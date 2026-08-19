"""Initial disease registries and research variable definitions — Sprint 5A-RES / 6B."""

import json

from app.extensions import db
from app.modules.research.constants import (
    LEGACY_VALUE_TYPE_MAP,
    MODULE_CLINICAL_HISTORY,
    MODULE_LABORATORY,
    MODULE_PATIENTS,
    ORIGIN_CLINICAL_REFERENCE,
    SOURCE_TYPE_TO_MODULE,
)
from app.modules.research.models import DiseaseRegistryDefinition, ResearchVariableDefinition

REGISTRIES = [
    ("reg.ugib", "Upper GI Bleeding Registry", "Prospective and retrospective UGI bleed outcomes.", "kl.research.reg.ugib", 10),
    ("reg.ibd", "IBD Registry", "Inflammatory bowel disease structured follow-up.", "kl.research.reg.ibd", 20),
    ("reg.ercp", "ERCP Registry", "ERCP procedure and outcome variables.", "kl.research.reg.ercp", 30),
    ("reg.cld", "Chronic Liver Disease Registry", "Chronic liver disease presentation and outcomes.", "kl.research.reg.cld", 40),
]

# (code, registry_code, name, source_type, source_key, value_type, sort_order, description)
VARIABLES = [
    ("rv.patient.sex", "reg.ugib", "Patient sex", "patient_field", "sex", "text", 10, None),
    ("rv.patient.mrn", "reg.ugib", "MRN", "patient_field", "mrn", "text", 20, None),
    ("rv.ugib.melena", "reg.ugib", "Melena", "history_answer", "q.ugib.melena", "boolean", 30, None),
    ("rv.ugib.liver_disease", "reg.ugib", "Known liver disease", "history_answer", "q.ugib.liver_disease", "boolean", 40, None),
    ("rv.ugib.diagnosis", "reg.ugib", "Confirmed diagnosis", "history_confirmed_diagnosis", "hist.upper_gi_bleeding", "text", 50, None),
    ("rv.ugib.hb", "reg.ugib", "Haemoglobin", "lab_result", "lab.cbc_hb", "number", 60, None),

    ("rv.patient.sex_ibd", "reg.ibd", "Patient sex", "patient_field", "sex", "text", 10, None),
    ("rv.ibd.blood_stool", "reg.ibd", "Blood in stool", "history_answer", "q.diar.blood", "boolean", 20, None),
    ("rv.ibd.nocturnal", "reg.ibd", "Nocturnal symptoms", "history_answer", "q.diar.nocturnal", "boolean", 30, None),
    ("rv.ibd.diagnosis", "reg.ibd", "Confirmed diagnosis", "history_confirmed_diagnosis", "hist.diarrhea", "text", 40, None),
    ("rv.ibd.calprotectin", "reg.ibd", "Faecal calprotectin", "lab_result", "lab.calprotectin", "number", 50, None),

    ("rv.patient.sex_cld", "reg.cld", "Patient sex", "patient_field", "sex", "text", 10, None),
    ("rv.cld.alcohol", "reg.cld", "Heavy alcohol use", "history_answer", "q.cld.alcohol", "boolean", 20, None),
    ("rv.cld.ascites", "reg.cld", "Ascites", "history_answer", "q.cld.ascites", "boolean", 30, None),
    ("rv.cld.diagnosis", "reg.cld", "Confirmed diagnosis", "history_confirmed_diagnosis", "hist.chronic_liver_disease", "text", 40, None),
    ("rv.cld.inr", "reg.cld", "INR", "lab_result", "lab.inr", "number", 50, None),

    ("rv.patient.sex_ercp", "reg.ercp", "Patient sex", "patient_field", "sex", "text", 10, None),
    ("rv.patient.mrn_ercp", "reg.ercp", "MRN", "patient_field", "mrn", "text", 20, None),
]

REGISTRY_CONTEXT = {
    "reg.ugib": {"complaint_code": "hist.upper_gi_bleeding"},
    "reg.ibd": {"complaint_code": "hist.diarrhea"},
    "reg.cld": {"complaint_code": "hist.chronic_liver_disease"},
    "reg.ercp": {},
}


def _attachment_for(source_type: str, registry_code: str) -> dict:
    ctx = REGISTRY_CONTEXT.get(registry_code, {})
    module = SOURCE_TYPE_TO_MODULE.get(source_type, MODULE_PATIENTS)
    attachment = {"module": module}
    if source_type == "history_answer" and ctx.get("complaint_code"):
        attachment["complaint_code"] = ctx["complaint_code"]
    if source_type == "history_confirmed_diagnosis" and ctx.get("complaint_code"):
        attachment["complaint_code"] = ctx["complaint_code"]
    return attachment


def seed_research_catalogue_if_empty() -> int:
    if DiseaseRegistryDefinition.query.first() is not None:
        return 0

    count = 0
    for code, name, description, kl_key, sort_order in REGISTRIES:
        db.session.add(DiseaseRegistryDefinition(
            code=code,
            name=name,
            description=description,
            knowledge_topic_key=kl_key,
            sort_order=sort_order,
            department_id=1,
        ))
        count += 1

    for code, registry_code, name, source_type, source_key, value_type, sort_order, description in VARIABLES:
        data_type = LEGACY_VALUE_TYPE_MAP.get(value_type, value_type)
        db.session.add(ResearchVariableDefinition(
            code=code,
            stable_id=code,
            registry_code=registry_code,
            name=name,
            description=description,
            source_module=SOURCE_TYPE_TO_MODULE.get(source_type),
            source_type=source_type,
            source_key=source_key,
            data_type=data_type,
            value_type=value_type,
            value_origin=ORIGIN_CLINICAL_REFERENCE,
            attachment_config_json=json.dumps(_attachment_for(source_type, registry_code)),
            version=1,
            sort_order=sort_order,
            department_id=1,
        ))
        count += 1

    db.session.commit()
    return count
