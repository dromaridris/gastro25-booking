"""Clinical Documentation Intelligence orchestration — Gastro25."""

from __future__ import annotations

import json
from typing import Any

from gi_platform import history_service
from gi_platform.audit_service import log_event
from gi_platform.clinical_assessment import service as assessment_service
from gi_platform.documentation_ai.constants import (
    ACTION_APPROVE, ACTION_EDIT, ACTION_REGENERATE, ACTION_REJECT, ACTION_SIGN,
    AUDIT_PREFIX, DOC_STATUS_APPROVED, DOC_STATUS_DRAFT, DOC_STATUS_REJECTED, DOC_STATUS_SIGNED,
    SECTION_STATUS_DRAFT, SECTION_STATUS_MODIFIED,
)
from gi_platform.documentation_ai.context_builder import DocumentationContextBuilder
from gi_platform.documentation_ai.document_generator import DocumentGenerator
from gi_platform.documentation_ai.permissions import (
    require_documentation_sign, require_documentation_use, require_documentation_view,
)
from gi_platform.documentation_ai.section_builder import SectionBuilder
from gi_platform.documentation_ai.templates import TemplateRegistry, seed_templates_if_empty


class NotFoundError(LookupError):
    pass


class ValidationError(ValueError):
    pass


def list_templates(db, *, role) -> list[dict]:
    require_documentation_view(role=role)
    seed_templates_if_empty(db)
    return TemplateRegistry.list_active(db)


def generate_document(db, *, role, user_id, history_session_id: int, template_key: str) -> dict:
    require_documentation_use(role=role)
    seed_templates_if_empty(db)

    hist = history_service.get_session(db, history_session_id)
    if not hist:
        raise NotFoundError(f'No history session {history_session_id}')

    if not assessment_service.get_latest_run(db, role=role, history_session_id=history_session_id):
        raise ValidationError('Clinical assessment required before documentation generation.')

    template = TemplateRegistry.get_by_key(db, template_key)
    if not template:
        raise NotFoundError(f'No documentation template {template_key}')

    context = DocumentationContextBuilder().build(db, history_session_id=history_session_id, role=role)
    generator = DocumentGenerator()
    section_data = generator.generate_sections(template, context)
    ai_result = generator.run_ai_session(
        db, role=role, user_id=user_id, history_session_id=history_session_id,
        ward_patient_id=hist['ward_patient_id'], template=template,
        context=context, sections=section_data,
    )

    cur = db.execute(
        """
        INSERT INTO gi_clinical_document_draft (
            history_session_id, ward_patient_id, template_id, template_key, document_type,
            ai_session_uuid, provider_key, model_name, status,
            source_modules_json, knowledge_references_json, clinical_context_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_session_id, hist['ward_patient_id'], template['id'], template['template_key'],
            template['document_type'], ai_result['ai_session_uuid'], ai_result['provider_key'],
            ai_result['model_name'], DOC_STATUS_DRAFT,
            json.dumps(context.get('source_modules_used') or []),
            json.dumps(context.get('knowledge_references') or []),
            json.dumps(context), user_id,
        ),
    )
    doc_id = cur.lastrowid

    for item in section_data:
        db.execute(
            """
            INSERT INTO gi_document_section (
                document_id, section_key, section_name, sort_order,
                generated_content, source_data_references_json, missing_information_json,
                conflicting_information_json, is_required, is_complete, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id, item['section_key'], item['section_name'], item.get('sort_order', 0),
                item.get('generated_content'),
                json.dumps(item.get('source_data_references') or []),
                json.dumps(item.get('missing_information') or []),
                json.dumps(item.get('conflicting_information') or []),
                1 if item.get('is_required', True) else 0,
                1 if item.get('is_complete') else 0,
                SECTION_STATUS_DRAFT,
            ),
        )

    _record_version(db, doc_id=doc_id, version=1, user_id=user_id,
                    changed_sections=[s['section_key'] for s in section_data], reason='Initial generation')
    db.commit()

    log_event(
        db, action=f'{AUDIT_PREFIX}.generation_completed',
        entity_type='clinical_document_draft', entity_id=doc_id, user_id=user_id,
        details={'template_key': template_key, 'section_count': len(section_data)},
    )
    return get_document(db, role=role, document_id=doc_id)


def get_document(db, *, role, document_id: int) -> dict:
    require_documentation_view(role=role)
    row = db.execute('SELECT * FROM gi_clinical_document_draft WHERE id = ?', (document_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No document draft {document_id}')
    return document_to_dict(row)


def get_document_view(db, *, role, document_id: int) -> dict[str, Any]:
    doc = get_document(db, role=role, document_id=document_id)
    sections = list_sections(db, role=role, document_id=document_id)
    versions = db.execute(
        """
        SELECT * FROM gi_document_version_record
        WHERE document_id = ? ORDER BY version_number DESC
        """,
        (document_id,),
    ).fetchall()
    signed = db.execute(
        'SELECT * FROM gi_signed_clinical_document WHERE draft_id = ? LIMIT 1', (document_id,),
    ).fetchone()
    return {
        'document': doc,
        'sections': sections,
        'versions': [version_to_dict(v) for v in versions],
        'signed_document': signed_document_to_dict(signed) if signed else None,
    }


def list_sections(db, *, role, document_id: int) -> list[dict]:
    get_document(db, role=role, document_id=document_id)
    rows = db.execute(
        'SELECT * FROM gi_document_section WHERE document_id = ? ORDER BY sort_order, id',
        (document_id,),
    ).fetchall()
    return [section_to_dict(r) for r in rows]


def edit_section(db, *, role, user_id, section_id: int, content: str, notes=None) -> dict:
    require_documentation_use(role=role)
    section = _get_section_row(db, section_id)
    db.execute(
        """
        UPDATE gi_document_section
        SET physician_content = ?, approval_status = ?, is_complete = ?, version = version + 1
        WHERE id = ?
        """,
        (content, SECTION_STATUS_MODIFIED, 1 if content.strip() else 0, section_id),
    )
    db.execute(
        'UPDATE gi_clinical_document_draft SET version = version + 1 WHERE id = ?',
        (section['document_id'],),
    )
    _record_version(
        db, doc_id=section['document_id'], version=_doc_version(db, section['document_id']),
        user_id=user_id, changed_sections=[section['section_key']], reason=notes or 'Physician edit',
    )
    _record_action(
        db, document_id=section['document_id'], section_id=section_id,
        history_session_id=_doc_history_id(db, section['document_id']),
        user_id=user_id, action_type=ACTION_EDIT, notes=notes,
        modified_fields={'section_key': section['section_key'], 'content': content[:200]},
    )
    db.commit()
    return section_to_dict(db.execute('SELECT * FROM gi_document_section WHERE id = ?', (section_id,)).fetchone())


def regenerate_section(db, *, role, user_id, section_id: int) -> dict:
    require_documentation_use(role=role)
    section = _get_section_row(db, section_id)
    doc = db.execute('SELECT * FROM gi_clinical_document_draft WHERE id = ?', (section['document_id'],)).fetchone()
    context = json.loads(doc['clinical_context_json'] or '{}')
    result = SectionBuilder().build_section(section['section_key'], context)
    db.execute(
        """
        UPDATE gi_document_section SET
            generated_content = ?, source_data_references_json = ?,
            missing_information_json = ?, conflicting_information_json = ?,
            is_complete = ?, approval_status = ?, version = version + 1
        WHERE id = ?
        """,
        (
            result.get('generated_content'),
            json.dumps(result.get('source_data_references') or []),
            json.dumps(result.get('missing_information') or []),
            json.dumps(result.get('conflicting_information') or []),
            1 if result.get('is_complete') else 0,
            SECTION_STATUS_DRAFT, section_id,
        ),
    )
    db.execute('UPDATE gi_clinical_document_draft SET version = version + 1 WHERE id = ?', (section['document_id'],))
    db.commit()
    return section_to_dict(db.execute('SELECT * FROM gi_document_section WHERE id = ?', (section_id,)).fetchone())


def approve_document(db, *, role, user_id, document_id: int, notes=None) -> dict:
    require_documentation_use(role=role)
    doc = get_document(db, role=role, document_id=document_id)
    if doc['status'] == DOC_STATUS_SIGNED:
        raise ValidationError('Document is already signed.')

    incomplete = db.execute(
        """
        SELECT COUNT(*) AS c FROM gi_document_section
        WHERE document_id = ? AND is_required = 1 AND is_complete = 0
        """,
        (document_id,),
    ).fetchone()['c']
    if incomplete:
        raise ValidationError(f'{incomplete} required section(s) still incomplete.')

    db.execute(
        'UPDATE gi_clinical_document_draft SET status = ? WHERE id = ?',
        (DOC_STATUS_APPROVED, document_id),
    )
    _record_action(
        db, document_id=document_id, section_id=None,
        history_session_id=doc['history_session_id'], user_id=user_id,
        action_type=ACTION_APPROVE, notes=notes, modified_fields={},
    )
    db.commit()
    return get_document(db, role=role, document_id=document_id)


def reject_document(db, *, role, user_id, document_id: int, reason=None) -> dict:
    require_documentation_use(role=role)
    doc = get_document(db, role=role, document_id=document_id)
    db.execute(
        'UPDATE gi_clinical_document_draft SET status = ? WHERE id = ?',
        (DOC_STATUS_REJECTED, document_id),
    )
    _record_action(
        db, document_id=document_id, section_id=None,
        history_session_id=doc['history_session_id'], user_id=user_id,
        action_type=ACTION_REJECT, notes=reason, modified_fields={},
    )
    db.commit()
    return get_document(db, role=role, document_id=document_id)


def sign_document(db, *, role, user_id, document_id: int) -> dict:
    require_documentation_sign(role=role)
    doc = get_document(db, role=role, document_id=document_id)
    if doc['status'] != DOC_STATUS_APPROVED:
        raise ValidationError('Document must be approved before signing.')
    if db.execute(
        'SELECT id FROM gi_signed_clinical_document WHERE draft_id = ?', (document_id,),
    ).fetchone():
        raise ValidationError('Document is already signed.')

    sections = list_sections(db, role=role, document_id=document_id)
    signed_content = {
        'template_key': doc['template_key'],
        'document_type': doc['document_type'],
        'sections': {
            s['section_key']: {'name': s['section_name'], 'content': s['display_content']}
            for s in sections
        },
    }
    cur = db.execute(
        """
        INSERT INTO gi_signed_clinical_document (
            draft_id, history_session_id, ward_patient_id, template_key, document_type,
            signed_content_json, signed_by, signed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            document_id, doc['history_session_id'], doc['ward_patient_id'],
            doc['template_key'], doc['document_type'], json.dumps(signed_content), user_id,
        ),
    )
    db.execute(
        'UPDATE gi_clinical_document_draft SET status = ? WHERE id = ?',
        (DOC_STATUS_SIGNED, document_id),
    )
    _record_action(
        db, document_id=document_id, section_id=None,
        history_session_id=doc['history_session_id'], user_id=user_id,
        action_type=ACTION_SIGN, notes=None, modified_fields={'signed_document': True},
    )
    db.commit()
    row = db.execute('SELECT * FROM gi_signed_clinical_document WHERE id = ?', (cur.lastrowid,)).fetchone()
    return signed_document_to_dict(row)


def _get_section_row(db, section_id):
    row = db.execute('SELECT * FROM gi_document_section WHERE id = ?', (section_id,)).fetchone()
    if not row:
        raise NotFoundError(f'No section {section_id}')
    return row


def _doc_version(db, document_id) -> int:
    return db.execute(
        'SELECT version FROM gi_clinical_document_draft WHERE id = ?', (document_id,),
    ).fetchone()['version']


def _doc_history_id(db, document_id) -> int:
    return db.execute(
        'SELECT history_session_id FROM gi_clinical_document_draft WHERE id = ?', (document_id,),
    ).fetchone()['history_session_id']


def _record_version(db, *, doc_id, version, user_id, changed_sections, reason):
    sections = db.execute(
        'SELECT section_key, generated_content, physician_content FROM gi_document_section WHERE document_id = ?',
        (doc_id,),
    ).fetchall()
    snapshot = {
        'sections': {
            s['section_key']: (s['physician_content'] or s['generated_content'] or '')
            for s in sections
        },
    }
    db.execute(
        """
        INSERT INTO gi_document_version_record (
            document_id, version_number, changed_sections_json, editor_id, change_reason, snapshot_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (doc_id, version, json.dumps(changed_sections), user_id, reason, json.dumps(snapshot)),
    )


def _record_action(db, *, document_id, section_id, history_session_id, user_id,
                   action_type, notes, modified_fields):
    doc = db.execute(
        'SELECT ward_patient_id FROM gi_clinical_document_draft WHERE id = ?', (document_id,),
    ).fetchone()
    db.execute(
        """
        INSERT INTO gi_physician_document_action (
            document_id, section_id, history_session_id, ward_patient_id,
            action_type, action_notes, modified_fields_json, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id, section_id, history_session_id, doc['ward_patient_id'] if doc else None,
            action_type, notes, json.dumps(modified_fields or {}), user_id,
        ),
    )


def document_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'history_session_id': row['history_session_id'],
        'ward_patient_id': row['ward_patient_id'],
        'template_key': row['template_key'],
        'document_type': row['document_type'],
        'ai_session_uuid': row['ai_session_uuid'],
        'provider_key': row['provider_key'],
        'model_name': row['model_name'],
        'status': row['status'],
        'source_modules': json.loads(row['source_modules_json'] or '[]'),
        'knowledge_references': json.loads(row['knowledge_references_json'] or '[]'),
        'version': row['version'],
        'created_at': row['created_at'],
    }


def section_to_dict(row) -> dict:
    data = dict(row)
    display = data.get('physician_content') or data.get('generated_content') or ''
    return {
        'id': data['id'],
        'section_key': data['section_key'],
        'section_name': data['section_name'],
        'sort_order': data['sort_order'],
        'generated_content': data.get('generated_content'),
        'physician_content': data.get('physician_content'),
        'display_content': display,
        'source_data_references': json.loads(data.get('source_data_references_json') or '[]'),
        'missing_information': json.loads(data.get('missing_information_json') or '[]'),
        'conflicting_information': json.loads(data.get('conflicting_information_json') or '[]'),
        'is_required': bool(data.get('is_required')),
        'is_complete': bool(data.get('is_complete')),
        'approval_status': data.get('approval_status'),
        'version': data.get('version'),
    }


def version_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'version_number': row['version_number'],
        'changed_sections': json.loads(row['changed_sections_json'] or '[]'),
        'editor_id': row['editor_id'],
        'change_reason': row['change_reason'],
        'created_at': row['created_at'],
    }


def signed_document_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'draft_id': row['draft_id'],
        'history_session_id': row['history_session_id'],
        'template_key': row['template_key'],
        'document_type': row['document_type'],
        'signed_content': json.loads(row['signed_content_json'] or '{}'),
        'signed_by': row['signed_by'],
        'signed_at': row['signed_at'],
    }
