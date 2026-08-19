"""Clinical Documentation Intelligence orchestration services."""

from __future__ import annotations

from typing import Any

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_history_ai.constants import SESSION_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistorySession
from app.modules.documentation_ai.constants import (
    ACTION_APPROVE,
    ACTION_EDIT,
    ACTION_REGENERATE,
    ACTION_REJECT,
    ACTION_SIGN,
    AUDIT_PREFIX,
    DOC_STATUS_APPROVED,
    DOC_STATUS_DRAFT,
    DOC_STATUS_REJECTED,
    DOC_STATUS_SIGNED,
    SECTION_STATUS_APPROVED,
    SECTION_STATUS_DRAFT,
    SECTION_STATUS_MODIFIED,
    SECTION_STATUS_REJECTED,
)
from app.modules.documentation_ai.context_builder import DocumentationContextBuilder
from app.modules.documentation_ai.document_generator import DocumentGenerator
from app.modules.documentation_ai.models import (
    ClinicalDocumentDraft,
    DocumentSection,
    DocumentVersionRecord,
    PhysicianDocumentAction,
    SignedClinicalDocument,
)
from app.modules.documentation_ai.permissions import (
    require_documentation_sign,
    require_documentation_use,
    require_documentation_view,
)
from app.modules.documentation_ai.section_builder import SectionBuilder
from app.modules.documentation_ai.templates import TemplateRegistry, seed_templates_if_empty
from app.modules.encounters.models import ClinicalEncounter


def ensure_templates_seeded() -> int:
    return seed_templates_if_empty()


def list_templates(acting_user) -> list[dict]:
    require_documentation_view(acting_user)
    ensure_templates_seeded()
    return [
        {
            "id": t.id,
            "template_key": t.template_key,
            "document_type": t.document_type,
            "name": t.name,
            "sections": t.sections,
            "version": t.version,
        }
        for t in TemplateRegistry.list_active()
    ]


def generate_document(acting_user, encounter_id: int, *, template_key: str) -> ClinicalDocumentDraft:
    require_documentation_use(acting_user)
    ensure_templates_seeded()

    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    history_session = GuidedHistorySession.query.filter_by(
        encounter_id=encounter_id, is_archived=False
    ).first()
    if history_session is None or history_session.status != SESSION_STATUS_APPROVED:
        raise ValidationError("Approved structured history is required before documentation generation.")

    template = TemplateRegistry.get_by_key(template_key)
    if template is None:
        raise NotFoundError(f"No documentation template with key {template_key}")

    context = DocumentationContextBuilder().build(acting_user, encounter_id)
    generator = DocumentGenerator()
    section_data = generator.generate_sections(template, context)
    ai_result = generator.run_ai_session(
        acting_user,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        template=template,
        context=context,
        sections=section_data,
    )

    draft = ClinicalDocumentDraft(
        patient_id=encounter.patient_id,
        encounter_id=encounter.id,
        template_id=template.id,
        template_key=template.template_key,
        document_type=template.document_type,
        ai_session_uuid=ai_result["ai_session_uuid"],
        provider_key=ai_result["provider_key"],
        model_name=ai_result["model_name"],
        status=DOC_STATUS_DRAFT,
        source_modules=context.get("source_modules_used") or [],
        knowledge_references=context.get("knowledge_references") or [],
        clinical_context=context,
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(draft)
    db.session.flush()

    for item in section_data:
        section = DocumentSection(
            document_id=draft.id,
            section_key=item["section_key"],
            section_name=item["section_name"],
            sort_order=item.get("sort_order", 0),
            generated_content=item.get("generated_content"),
            source_data_references=item.get("source_data_references") or [],
            missing_information=item.get("missing_information") or [],
            conflicting_information=item.get("conflicting_information") or [],
            is_required=item.get("is_required", True),
            is_complete=item.get("is_complete", False),
            approval_status=SECTION_STATUS_DRAFT,
            department_id=encounter.department_id,
            created_by_id=acting_user.id,
        )
        db.session.add(section)

    _record_version(acting_user, draft, changed_sections=[s["section_key"] for s in section_data], reason="Initial generation")
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.generation_completed",
        user=acting_user,
        target_type="ClinicalDocumentDraft",
        target_id=draft.id,
        details={
            "encounter_id": encounter.id,
            "template_key": template.template_key,
            "ai_session_uuid": draft.ai_session_uuid,
            "source_modules": draft.source_modules,
            "knowledge_references": draft.knowledge_references,
        },
    )
    return draft


def get_document(acting_user, document_id: int) -> ClinicalDocumentDraft:
    require_documentation_view(acting_user)
    doc = ClinicalDocumentDraft.query.get(document_id)
    if doc is None or doc.is_archived:
        raise NotFoundError(f"No document draft with id {document_id}")
    return doc


def get_document_view(acting_user, document_id: int) -> dict[str, Any]:
    doc = get_document(acting_user, document_id)
    sections = (
        DocumentSection.query.filter_by(document_id=doc.id, is_archived=False)
        .order_by(DocumentSection.sort_order)
        .all()
    )
    versions = (
        DocumentVersionRecord.query.filter_by(document_id=doc.id, is_archived=False)
        .order_by(DocumentVersionRecord.version_number.desc())
        .all()
    )
    signed = SignedClinicalDocument.query.filter_by(draft_id=doc.id, is_archived=False).first()
    return {
        "document": document_to_dict(doc),
        "sections": [section_to_dict(s) for s in sections],
        "versions": [version_to_dict(v) for v in versions],
        "signed_document": signed_document_to_dict(signed) if signed else None,
    }


def get_latest_for_encounter(acting_user, encounter_id: int, *, document_type: str | None = None) -> ClinicalDocumentDraft | None:
    require_documentation_view(acting_user)
    query = ClinicalDocumentDraft.query.filter_by(encounter_id=encounter_id, is_archived=False)
    if document_type:
        query = query.filter_by(document_type=document_type)
    return query.order_by(ClinicalDocumentDraft.created_at.desc()).first()


def edit_section(
    acting_user, section_id: int, *, content: str, notes: str | None = None
) -> DocumentSection:
    require_documentation_use(acting_user)
    section = _get_section(acting_user, section_id)
    section.physician_content = content
    section.approval_status = SECTION_STATUS_MODIFIED
    section.is_complete = bool(content.strip())
    section.version += 1
    section.document.version += 1

    _record_version(
        acting_user,
        section.document,
        changed_sections=[section.section_key],
        reason=notes or "Physician edit",
    )
    _record_action(
        acting_user,
        section.document,
        section,
        ACTION_EDIT,
        notes,
        {"section_key": section.section_key, "content": content[:200]},
    )
    db.session.commit()
    return section


def regenerate_section(acting_user, section_id: int) -> DocumentSection:
    require_documentation_use(acting_user)
    section = _get_section(acting_user, section_id)
    context = section.document.clinical_context
    result = SectionBuilder().build_section(section.section_key, context)
    section.generated_content = result.get("generated_content")
    section.source_data_references = result.get("source_data_references") or []
    section.missing_information = result.get("missing_information") or []
    section.conflicting_information = result.get("conflicting_information") or []
    section.is_complete = result.get("is_complete", False)
    section.approval_status = SECTION_STATUS_DRAFT
    section.version += 1
    section.document.version += 1

    _record_version(acting_user, section.document, changed_sections=[section.section_key], reason="Section regenerated")
    _record_action(acting_user, section.document, section, ACTION_REGENERATE, None, {"section_key": section.section_key})
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.section_regenerated",
        user=acting_user,
        target_type="DocumentSection",
        target_id=section.id,
        details={"section_key": section.section_key},
    )
    return section


def approve_document(acting_user, document_id: int, *, notes: str | None = None) -> ClinicalDocumentDraft:
    require_documentation_use(acting_user)
    doc = get_document(acting_user, document_id)
    if doc.status == DOC_STATUS_SIGNED:
        raise ValidationError("Document is already signed.")

    incomplete = DocumentSection.query.filter_by(
        document_id=doc.id, is_required=True, is_complete=False, is_archived=False
    ).count()
    if incomplete:
        raise ValidationError(f"{incomplete} required section(s) still incomplete.")

    doc.status = DOC_STATUS_APPROVED
    _record_action(acting_user, doc, None, ACTION_APPROVE, notes, {})
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.document_approved",
        user=acting_user,
        target_type="ClinicalDocumentDraft",
        target_id=doc.id,
        details={"encounter_id": doc.encounter_id},
    )
    return doc


def reject_document(acting_user, document_id: int, *, reason: str | None = None) -> ClinicalDocumentDraft:
    require_documentation_use(acting_user)
    doc = get_document(acting_user, document_id)
    doc.status = DOC_STATUS_REJECTED
    _record_action(acting_user, doc, None, ACTION_REJECT, reason, {})
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.document_rejected",
        user=acting_user,
        target_type="ClinicalDocumentDraft",
        target_id=doc.id,
        details={"reason": reason},
    )
    return doc


def add_manual_section(
    acting_user, document_id: int, *, section_key: str, section_name: str, content: str
) -> DocumentSection:
    require_documentation_use(acting_user)
    doc = get_document(acting_user, document_id)
    section = DocumentSection(
        document_id=doc.id,
        section_key=section_key,
        section_name=section_name,
        sort_order=999,
        generated_content="",
        physician_content=content,
        is_required=False,
        is_complete=True,
        approval_status=SECTION_STATUS_MODIFIED,
        department_id=doc.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(section)
    _record_action(acting_user, doc, section, "manual", None, {"section_key": section_key})
    db.session.commit()
    return section


def sign_document(acting_user, document_id: int) -> SignedClinicalDocument:
    require_documentation_sign(acting_user)
    doc = get_document(acting_user, document_id)
    if doc.status != DOC_STATUS_APPROVED:
        raise ValidationError("Document must be approved before signing.")
    if SignedClinicalDocument.query.filter_by(draft_id=doc.id, is_archived=False).first():
        raise ValidationError("Document is already signed.")

    sections = DocumentSection.query.filter_by(document_id=doc.id, is_archived=False).order_by(DocumentSection.sort_order).all()
    signed_content = {
        "template_key": doc.template_key,
        "document_type": doc.document_type,
        "sections": {
            s.section_key: {
                "name": s.section_name,
                "content": s.display_content,
            }
            for s in sections
        },
    }

    signed = SignedClinicalDocument(
        draft_id=doc.id,
        patient_id=doc.patient_id,
        encounter_id=doc.encounter_id,
        template_key=doc.template_key,
        document_type=doc.document_type,
        signed_content=signed_content,
        signed_by_id=acting_user.id,
        signed_at=utcnow(),
        department_id=doc.department_id,
        created_by_id=acting_user.id,
    )
    doc.status = DOC_STATUS_SIGNED
    db.session.add(signed)
    _record_action(acting_user, doc, None, ACTION_SIGN, None, {"signed_document": True})
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.document_signed",
        user=acting_user,
        target_type="SignedClinicalDocument",
        target_id=signed.id,
        details={"draft_id": doc.id, "encounter_id": doc.encounter_id},
    )
    return signed


def _get_section(acting_user, section_id: int) -> DocumentSection:
    require_documentation_view(acting_user)
    section = DocumentSection.query.get(section_id)
    if section is None or section.is_archived:
        raise NotFoundError(f"No document section with id {section_id}")
    return section


def _record_version(acting_user, doc: ClinicalDocumentDraft, *, changed_sections: list[str], reason: str) -> None:
    sections = DocumentSection.query.filter_by(document_id=doc.id, is_archived=False).all()
    snapshot = {
        "sections": {s.section_key: s.display_content for s in sections},
        "status": doc.status,
    }
    record = DocumentVersionRecord(
        document_id=doc.id,
        version_number=doc.version,
        changed_sections=changed_sections,
        editor_id=acting_user.id,
        change_reason=reason,
        snapshot=snapshot,
        department_id=doc.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(record)


def _record_action(
    acting_user,
    doc: ClinicalDocumentDraft,
    section: DocumentSection | None,
    action_type: str,
    notes: str | None,
    modified_fields: dict,
) -> None:
    action = PhysicianDocumentAction(
        document_id=doc.id,
        section_id=section.id if section else None,
        encounter_id=doc.encounter_id,
        patient_id=doc.patient_id,
        action_type=action_type,
        action_notes=notes,
        modified_fields=modified_fields,
        department_id=doc.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(action)


def document_to_dict(doc: ClinicalDocumentDraft) -> dict[str, Any]:
    return {
        "id": doc.id,
        "patient_id": doc.patient_id,
        "encounter_id": doc.encounter_id,
        "template_key": doc.template_key,
        "document_type": doc.document_type,
        "ai_session_uuid": doc.ai_session_uuid,
        "provider_key": doc.provider_key,
        "model_name": doc.model_name,
        "status": doc.status,
        "source_modules": doc.source_modules,
        "knowledge_references": doc.knowledge_references,
        "version": doc.version,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


def section_to_dict(section: DocumentSection) -> dict[str, Any]:
    return {
        "id": section.id,
        "section_key": section.section_key,
        "section_name": section.section_name,
        "sort_order": section.sort_order,
        "generated_content": section.generated_content,
        "physician_content": section.physician_content,
        "display_content": section.display_content,
        "source_data_references": section.source_data_references,
        "missing_information": section.missing_information,
        "conflicting_information": section.conflicting_information,
        "is_required": section.is_required,
        "is_complete": section.is_complete,
        "approval_status": section.approval_status,
        "version": section.version,
    }


def version_to_dict(record: DocumentVersionRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "version_number": record.version_number,
        "changed_sections": record.changed_sections,
        "editor_id": record.editor_id,
        "change_reason": record.change_reason,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def signed_document_to_dict(signed: SignedClinicalDocument) -> dict[str, Any]:
    return {
        "id": signed.id,
        "draft_id": signed.draft_id,
        "patient_id": signed.patient_id,
        "encounter_id": signed.encounter_id,
        "template_key": signed.template_key,
        "document_type": signed.document_type,
        "signed_content": signed.signed_content,
        "signed_by_id": signed.signed_by_id,
        "signed_at": signed.signed_at.isoformat() if signed.signed_at else None,
    }
