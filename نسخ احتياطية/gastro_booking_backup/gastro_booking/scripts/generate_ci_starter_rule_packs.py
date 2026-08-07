"""Generate starter CI reasoning + investigation packs and update manifest."""
from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "clinical_knowledge"
reasoning_dir = root / "rules" / "reasoning"
ix_dir = root / "rules" / "investigation"
reasoning_dir.mkdir(parents=True, exist_ok=True)
ix_dir.mkdir(parents=True, exist_ok=True)

packs = {
    "hematemesis": {
        "complaint_code": "CC_hematemesis",
        "min_history": 6,
        "patterns": [
            {
                "id": "PAT_hem_variceal_risk",
                "label": "Variceal / portal hypertension risk bleed",
                "diagnosis_code": "DX_variceal_bleed_suspect",
                "diagnosis_label": "Variceal bleeding (suspect)",
                "weight_sum_required": 1.8,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000033", "op": "truthy", "weight": 0.8, "finding": "Hematemesis confirmed"},
                    {"kind": "answer", "question_id": "Q000109", "op": "in", "value": ["About a cup", "More than a cup / continuous"], "weight": 1.0, "finding": "Large-volume hematemesis"},
                    {"kind": "answer", "question_id": "Q000038", "op": "truthy", "weight": 0.7, "finding": "Syncope/dizziness"},
                    {"kind": "exam", "sign_code": "SG_hypotension", "op": "present", "weight": 1.0, "finding": "Hypotension"},
                    {"kind": "exam", "sign_code": "SG_tachycardia", "op": "present", "weight": 0.6, "finding": "Tachycardia"},
                ],
                "suggested_questions": ["Q000034", "Q000038", "Q000096"],
                "suggested_exam": ["SG_hypotension", "SG_tachycardia", "SG_pallor"],
                "suggested_investigations": ["IX_cbc", "IX_coagulation_panel", "IX_upper_endoscopy", "IX_liver_panel"],
            },
            {
                "id": "PAT_hem_ulcer_pud",
                "label": "Peptic ulcer / non-variceal UGIB pattern",
                "diagnosis_code": "DX_pud_ugib_suspect",
                "diagnosis_label": "Peptic ulcer UGIB (suspect)",
                "weight_sum_required": 1.6,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000108", "op": "in", "value": ["Bright red blood", "Dark / coffee-ground material"], "weight": 1.0, "finding": "Bloody or coffee-ground emesis"},
                    {"kind": "answer", "question_id": "Q000034", "op": "truthy", "weight": 0.9, "finding": "Melena"},
                    {"kind": "answer", "question_id": "Q000042", "op": "eq", "value": "Epigastric", "weight": 0.6, "finding": "Epigastric pain"},
                ],
                "suggested_questions": ["Q000034", "Q000053", "Q000038"],
                "suggested_exam": ["SG_pallor", "SG_tachycardia"],
                "suggested_investigations": ["IX_cbc", "IX_coagulation_panel", "IX_upper_endoscopy"],
            },
            {
                "id": "PAT_hem_mallory_weiss",
                "label": "Mallory-Weiss / retching-first pattern",
                "diagnosis_code": "DX_mallory_weiss_suspect",
                "diagnosis_label": "Mallory-Weiss tear (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000110", "op": "truthy", "weight": 1.4, "finding": "Retching before blood"},
                    {"kind": "answer", "question_id": "Q000108", "op": "eq", "value": "Bright red blood", "weight": 0.6, "finding": "Bright red hematemesis"},
                ],
                "suggested_questions": ["Q000109", "Q000038"],
                "suggested_exam": ["SG_tachycardia"],
                "suggested_investigations": ["IX_cbc", "IX_upper_endoscopy"],
            },
        ],
        "missing": [
            {"id": "need_volume", "if_unanswered": ["Q000109"], "message": "Estimate volume of hematemesis", "next_questions": ["Q000109"]},
            {"id": "need_hemodynamics", "if_exam_missing_any": ["SG_hypotension", "SG_tachycardia"], "message": "Document vitals / shock signs", "next_exam": ["SG_hypotension", "SG_tachycardia", "SG_pallor"]},
        ],
        "ix_bundles": [
            {"id": "IXB_hem_baseline", "label": "Hematemesis baseline / resuscitation labs", "urgency": "emergency",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_cbc", "IX_coagulation_panel", "IX_basic_metabolic_panel", "IX_liver_panel"],
             "referral_hint": "Urgent endoscopy pathway if unstable or large-volume bleed"},
            {"id": "IXB_hem_endo", "label": "Urgent upper endoscopy", "urgency": "emergency",
             "when": {"any": [{"pattern_id": "PAT_hem_variceal_risk"}, {"pattern_id": "PAT_hem_ulcer_pud"}, {"question_id": "Q000038", "op": "truthy"}]},
             "investigations": ["IX_upper_endoscopy"],
             "referral_hint": "Activate GI bleed pathway"},
        ],
    },
    "melena": {
        "complaint_code": "CC_melena",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_mel_ugib",
                "label": "True melena / upper GI source",
                "diagnosis_code": "DX_ugib_melena_suspect",
                "diagnosis_label": "Upper GI bleed with melena (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000112", "op": "in", "value": ["Sticky / tar-like (true melena character)"], "weight": 1.3, "finding": "Tarry sticky stool"},
                    {"kind": "answer", "question_id": "Q000033", "op": "truthy", "weight": 0.9, "finding": "Hematemesis"},
                    {"kind": "answer", "question_id": "Q000038", "op": "truthy", "weight": 0.7, "finding": "Presyncope"},
                    {"kind": "exam", "sign_code": "SG_pallor", "op": "present", "weight": 0.6, "finding": "Pallor"},
                ],
                "suggested_questions": ["Q000033", "Q000038", "Q000053"],
                "suggested_exam": ["SG_hypotension", "SG_tachycardia", "SG_pallor"],
                "suggested_investigations": ["IX_cbc", "IX_coagulation_panel", "IX_upper_endoscopy"],
            },
            {
                "id": "PAT_mel_hemodynamic",
                "label": "Melena with hemodynamic concern",
                "diagnosis_code": "DX_significant_gi_bleed_suspect",
                "diagnosis_label": "Significant GI bleed (suspect)",
                "weight_sum_required": 1.4,
                "criteria": [
                    {"kind": "exam", "sign_code": "SG_hypotension", "op": "present", "weight": 1.2, "finding": "Hypotension"},
                    {"kind": "exam", "sign_code": "SG_tachycardia", "op": "present", "weight": 0.8, "finding": "Tachycardia"},
                    {"kind": "answer", "question_id": "Q000038", "op": "truthy", "weight": 0.7, "finding": "Dizziness/fainting"},
                ],
                "suggested_questions": ["Q000033", "Q000035"],
                "suggested_exam": ["SG_hypotension", "SG_tachycardia"],
                "suggested_investigations": ["IX_cbc", "IX_coagulation_panel", "IX_upper_endoscopy"],
            },
        ],
        "missing": [
            {"id": "need_melena_character", "if_unanswered": ["Q000112"], "message": "Clarify true melena vs dark stool", "next_questions": ["Q000112"]},
        ],
        "ix_bundles": [
            {"id": "IXB_mel_baseline", "label": "Melena baseline", "urgency": "urgent",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_cbc", "IX_coagulation_panel", "IX_basic_metabolic_panel"]},
            {"id": "IXB_mel_endo", "label": "Upper endoscopy for melena", "urgency": "urgent",
             "when": {"any": [{"pattern_id": "PAT_mel_ugib"}, {"pattern_id": "PAT_mel_hemodynamic"}]},
             "investigations": ["IX_upper_endoscopy"],
             "referral_hint": "Urgent GI review"},
        ],
    },
    "hematochezia": {
        "complaint_code": "CC_hematochezia",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_hc_massive_lgib",
                "label": "Massive LGIB / brisk bleed",
                "diagnosis_code": "DX_massive_lgib_suspect",
                "diagnosis_label": "Massive lower GI bleed (suspect)",
                "weight_sum_required": 1.6,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000035", "op": "truthy", "weight": 1.0, "finding": "Hematochezia"},
                    {"kind": "answer", "question_id": "Q000038", "op": "truthy", "weight": 0.9, "finding": "Presyncope"},
                    {"kind": "exam", "sign_code": "SG_hypotension", "op": "present", "weight": 1.1, "finding": "Hypotension"},
                    {"kind": "exam", "sign_code": "SG_tachycardia", "op": "present", "weight": 0.6, "finding": "Tachycardia"},
                ],
                "suggested_questions": ["Q000033", "Q000034", "Q000114"],
                "suggested_exam": ["SG_hypotension", "SG_tachycardia", "SG_pallor"],
                "suggested_investigations": ["IX_cbc", "IX_coagulation_panel", "IX_ct_abdomen"],
            },
            {
                "id": "PAT_hc_brisk_ugib",
                "label": "Brisk UGIB presenting as hematochezia",
                "diagnosis_code": "DX_brisk_ugib_as_hematochezia_suspect",
                "diagnosis_label": "Brisk UGIB with hematochezia (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000033", "op": "truthy", "weight": 1.2, "finding": "Hematemesis"},
                    {"kind": "answer", "question_id": "Q000035", "op": "truthy", "weight": 0.8, "finding": "Hematochezia"},
                    {"kind": "answer", "question_id": "Q000038", "op": "truthy", "weight": 0.6, "finding": "Hemodynamic symptoms"},
                ],
                "suggested_questions": ["Q000034", "Q000038"],
                "suggested_exam": ["SG_hypotension", "SG_pallor"],
                "suggested_investigations": ["IX_cbc", "IX_upper_endoscopy", "IX_coagulation_panel"],
            },
            {
                "id": "PAT_hc_anorectal",
                "label": "Likely anorectal source (stable)",
                "diagnosis_code": "DX_anorectal_bleed_suspect",
                "diagnosis_label": "Anorectal bleeding (suspect)",
                "weight_sum_required": 1.2,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000114", "op": "truthy", "weight": 0.8, "finding": "Rectal blood characterised"},
                    {"kind": "answer", "question_id": "Q000035", "op": "truthy", "weight": 0.7, "finding": "Hematochezia"},
                ],
                "suggested_questions": ["Q000034", "Q000019"],
                "suggested_exam": ["SG_pallor"],
                "suggested_investigations": ["IX_cbc", "IX_colonoscopy"],
            },
        ],
        "missing": [
            {"id": "need_blood_colour", "if_unanswered": ["Q000114"], "message": "Clarify blood colour / pattern", "next_questions": ["Q000114"]},
        ],
        "ix_bundles": [
            {"id": "IXB_hc_baseline", "label": "Hematochezia baseline", "urgency": "urgent",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_cbc", "IX_coagulation_panel"]},
            {"id": "IXB_hc_massive", "label": "Massive bleed workup", "urgency": "emergency",
             "when": {"any": [{"pattern_id": "PAT_hc_massive_lgib"}, {"pattern_id": "PAT_hc_brisk_ugib"}]},
             "investigations": ["IX_cbc", "IX_coagulation_panel", "IX_upper_endoscopy"],
             "referral_hint": "Resuscitation + urgent endoscopy as needed"},
        ],
    },
    "jaundice": {
        "complaint_code": "CC_jaundice",
        "min_history": 6,
        "patterns": [
            {
                "id": "PAT_jaundice_obstructive",
                "label": "Obstructive / cholestatic pattern",
                "diagnosis_code": "DX_obstructive_jaundice_suspect",
                "diagnosis_label": "Obstructive jaundice (suspect)",
                "weight_sum_required": 1.6,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000026", "op": "truthy", "weight": 0.8, "finding": "Jaundice"},
                    {"kind": "answer", "question_id": "Q000064", "op": "truthy", "weight": 1.2, "finding": "Pale stools + dark urine"},
                    {"kind": "answer", "question_id": "Q000042", "op": "eq", "value": "RUQ", "weight": 0.7, "finding": "RUQ pain"},
                    {"kind": "exam", "sign_code": "SG_jaundice", "op": "present", "weight": 0.6, "finding": "Clinical jaundice"},
                ],
                "suggested_questions": ["Q000017", "Q000074"],
                "suggested_exam": ["SG_jaundice", "SG_murphy_sign", "SG_abdominal_mass"],
                "suggested_investigations": ["IX_liver_panel", "IX_abdominal_ultrasound", "IX_cbc"],
            },
            {
                "id": "PAT_jaundice_hepatitic",
                "label": "Hepatocellular / acute hepatitis pattern",
                "diagnosis_code": "DX_hepatitis_jaundice_suspect",
                "diagnosis_label": "Hepatocellular jaundice (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000017", "op": "truthy", "weight": 0.7, "finding": "Fever"},
                    {"kind": "answer", "question_id": "Q000021", "op": "truthy", "weight": 0.4, "finding": "Nausea"},
                    {"kind": "answer", "question_id": "Q000074", "op": "truthy", "weight": 1.0, "finding": "Altered mental status"},
                    {"kind": "exam", "sign_code": "SG_jaundice", "op": "present", "weight": 0.6, "finding": "Jaundice"},
                ],
                "suggested_questions": ["Q000064", "Q000096"],
                "suggested_exam": ["SG_jaundice", "SG_ascites"],
                "suggested_investigations": ["IX_liver_panel", "IX_coagulation_panel", "IX_cbc"],
            },
            {
                "id": "PAT_jaundice_cholangitis",
                "label": "Ascending cholangitis concern",
                "diagnosis_code": "DX_cholangitis_suspect",
                "diagnosis_label": "Cholangitis (suspect)",
                "weight_sum_required": 1.8,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000026", "op": "truthy", "weight": 0.7, "finding": "Jaundice"},
                    {"kind": "answer", "question_id": "Q000017", "op": "truthy", "weight": 0.9, "finding": "Fever"},
                    {"kind": "answer", "question_id": "Q000042", "op": "eq", "value": "RUQ", "weight": 0.8, "finding": "RUQ pain"},
                    {"kind": "exam", "sign_code": "SG_murphy_sign", "op": "present", "weight": 0.7, "finding": "Murphy / RUQ tenderness"},
                ],
                "suggested_questions": ["Q000064", "Q000074"],
                "suggested_exam": ["SG_jaundice", "SG_murphy_sign"],
                "suggested_investigations": ["IX_liver_panel", "IX_cbc", "IX_abdominal_ultrasound"],
            },
        ],
        "missing": [
            {"id": "need_stool_urine", "if_unanswered": ["Q000064"], "message": "Ask about pale stools / dark urine", "next_questions": ["Q000064"]},
        ],
        "ix_bundles": [
            {"id": "IXB_jaundice_baseline", "label": "Jaundice baseline labs + US", "urgency": "urgent",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_liver_panel", "IX_cbc", "IX_coagulation_panel", "IX_abdominal_ultrasound"]},
            {"id": "IXB_jaundice_cholangitis", "label": "Cholangitis pathway", "urgency": "emergency",
             "when": {"any": [{"pattern_id": "PAT_jaundice_cholangitis"}]},
             "investigations": ["IX_cbc", "IX_liver_panel", "IX_abdominal_ultrasound"],
             "referral_hint": "Urgent biliary decompression consideration"},
        ],
    },
    "diarrhea": {
        "complaint_code": "CC_diarrhea",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_diarrhea_infectious",
                "label": "Acute infectious / inflammatory diarrhea",
                "diagnosis_code": "DX_infectious_diarrhea_suspect",
                "diagnosis_label": "Infectious diarrhea (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000023", "op": "truthy", "weight": 0.8, "finding": "Diarrhea"},
                    {"kind": "answer", "question_id": "Q000017", "op": "truthy", "weight": 0.8, "finding": "Fever"},
                    {"kind": "answer", "question_id": "Q000003", "op": "eq", "value": "Sudden", "weight": 0.5, "finding": "Sudden onset"},
                    {"kind": "exam", "sign_code": "SG_dehydration", "op": "present", "weight": 0.7, "finding": "Dehydration"},
                ],
                "suggested_questions": ["Q000035", "Q000051", "Q000075"],
                "suggested_exam": ["SG_dehydration", "SG_rebound_tenderness"],
                "suggested_investigations": ["IX_cbc", "IX_basic_metabolic_panel"],
            },
            {
                "id": "PAT_diarrhea_ibd_alarm",
                "label": "Chronic / IBD-alarm pattern",
                "diagnosis_code": "DX_ibd_diarrhea_suspect",
                "diagnosis_label": "IBD / inflammatory diarrhea (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000051", "op": "truthy", "weight": 1.0, "finding": "Nocturnal diarrhea"},
                    {"kind": "answer", "question_id": "Q000035", "op": "truthy", "weight": 0.9, "finding": "Bloody stool"},
                    {"kind": "answer", "question_id": "Q000019", "op": "truthy", "weight": 0.6, "finding": "Weight loss"},
                ],
                "suggested_questions": ["Q000034", "Q000017"],
                "suggested_exam": ["SG_abnormal_stool_colour", "SG_pallor"],
                "suggested_investigations": ["IX_cbc", "IX_colonoscopy"],
            },
            {
                "id": "PAT_diarrhea_dehydration",
                "label": "Dehydration / volume depletion",
                "diagnosis_code": "DX_diarrheal_dehydration_suspect",
                "diagnosis_label": "Dehydration from diarrhea (suspect)",
                "weight_sum_required": 1.2,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000075", "op": "truthy", "weight": 1.1, "finding": "Dehydration symptoms"},
                    {"kind": "exam", "sign_code": "SG_dehydration", "op": "present", "weight": 1.0, "finding": "Dehydration signs"},
                    {"kind": "exam", "sign_code": "SG_hypotension", "op": "present", "weight": 0.7, "finding": "Hypotension"},
                ],
                "suggested_questions": ["Q000038"],
                "suggested_exam": ["SG_dehydration", "SG_hypotension"],
                "suggested_investigations": ["IX_basic_metabolic_panel", "IX_cbc"],
            },
        ],
        "missing": [
            {"id": "need_bloody", "if_unanswered_any": ["Q000035", "Q000034"], "message": "Ask about blood in stool", "next_questions": ["Q000035", "Q000034"]},
        ],
        "ix_bundles": [
            {"id": "IXB_diarrhea_baseline", "label": "Diarrhea baseline", "urgency": "routine",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_cbc", "IX_basic_metabolic_panel"]},
            {"id": "IXB_diarrhea_inflammatory", "label": "Inflammatory / bloody diarrhea", "urgency": "urgent",
             "when": {"any": [{"pattern_id": "PAT_diarrhea_ibd_alarm"}, {"question_id": "Q000035", "op": "truthy"}]},
             "investigations": ["IX_cbc"]},
        ],
    },
    "vomiting": {
        "complaint_code": "CC_vomiting",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_vom_obstruction",
                "label": "Obstruction / ileus pattern",
                "diagnosis_code": "DX_obstruction_vomiting_suspect",
                "diagnosis_label": "Bowel obstruction (suspect)",
                "weight_sum_required": 1.6,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000022", "op": "truthy", "weight": 0.7, "finding": "Vomiting"},
                    {"kind": "answer", "question_id": "Q000045", "op": "truthy", "weight": 1.2, "finding": "Inability to pass stool/gas"},
                    {"kind": "answer", "question_id": "Q000025", "op": "truthy", "weight": 0.6, "finding": "Distention"},
                    {"kind": "exam", "sign_code": "SG_visible_peristalsis", "op": "present", "weight": 0.7, "finding": "Visible peristalsis"},
                ],
                "suggested_questions": ["Q000033", "Q000073"],
                "suggested_exam": ["SG_rigidity", "SG_rebound_tenderness", "SG_visible_peristalsis"],
                "suggested_investigations": ["IX_ct_abdomen", "IX_cbc", "IX_basic_metabolic_panel"],
            },
            {
                "id": "PAT_vom_bleed",
                "label": "Vomiting with GI bleed alarms",
                "diagnosis_code": "DX_vomiting_with_bleed_suspect",
                "diagnosis_label": "Vomiting with GI bleeding (suspect)",
                "weight_sum_required": 1.3,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000033", "op": "truthy", "weight": 1.4, "finding": "Hematemesis"},
                    {"kind": "answer", "question_id": "Q000034", "op": "truthy", "weight": 1.0, "finding": "Melena"},
                ],
                "suggested_questions": ["Q000038", "Q000077"],
                "suggested_exam": ["SG_hypotension", "SG_pallor"],
                "suggested_investigations": ["IX_cbc", "IX_upper_endoscopy", "IX_coagulation_panel"],
            },
            {
                "id": "PAT_vom_dehydration",
                "label": "Dehydration from protracted vomiting",
                "diagnosis_code": "DX_vomiting_dehydration_suspect",
                "diagnosis_label": "Dehydration from vomiting (suspect)",
                "weight_sum_required": 1.2,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000075", "op": "truthy", "weight": 1.1, "finding": "Dehydration symptoms"},
                    {"kind": "exam", "sign_code": "SG_hypotension", "op": "present", "weight": 0.8, "finding": "Hypotension"},
                ],
                "suggested_questions": ["Q000074"],
                "suggested_exam": ["SG_hypotension"],
                "suggested_investigations": ["IX_basic_metabolic_panel", "IX_cbc"],
            },
        ],
        "missing": [
            {"id": "need_bleed_screen", "if_unanswered_any": ["Q000033", "Q000077"], "message": "Screen for hematemesis", "next_questions": ["Q000033", "Q000077"]},
        ],
        "ix_bundles": [
            {"id": "IXB_vom_baseline", "label": "Vomiting baseline", "urgency": "routine",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_cbc", "IX_basic_metabolic_panel"]},
            {"id": "IXB_vom_obstruction", "label": "Obstruction imaging", "urgency": "emergency",
             "when": {"any": [{"pattern_id": "PAT_vom_obstruction"}, {"question_id": "Q000045", "op": "truthy"}]},
             "investigations": ["IX_ct_abdomen"],
             "referral_hint": "Surgical review if obstruction suspected"},
        ],
    },
    "abdominal_distention": {
        "complaint_code": "CC_abdominal_distention",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_dist_ascites",
                "label": "Ascites / portal hypertension pattern",
                "diagnosis_code": "DX_ascites_suspect",
                "diagnosis_label": "Ascites (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000025", "op": "truthy", "weight": 0.7, "finding": "Distention"},
                    {"kind": "exam", "sign_code": "SG_ascites", "op": "present", "weight": 1.3, "finding": "Ascites signs"},
                    {"kind": "answer", "question_id": "Q000026", "op": "truthy", "weight": 0.5, "finding": "Jaundice"},
                ],
                "suggested_questions": ["Q000026", "Q000034", "Q000115"],
                "suggested_exam": ["SG_ascites", "SG_jaundice"],
                "suggested_investigations": ["IX_liver_panel", "IX_abdominal_ultrasound", "IX_coagulation_panel"],
            },
            {
                "id": "PAT_dist_obstruction",
                "label": "Acute distention / obstruction",
                "diagnosis_code": "DX_distention_obstruction_suspect",
                "diagnosis_label": "Obstruction with distention (suspect)",
                "weight_sum_required": 1.6,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000045", "op": "truthy", "weight": 1.2, "finding": "Obstipation"},
                    {"kind": "answer", "question_id": "Q000022", "op": "truthy", "weight": 0.6, "finding": "Vomiting"},
                    {"kind": "exam", "sign_code": "SG_visible_peristalsis", "op": "present", "weight": 0.7, "finding": "Visible peristalsis"},
                ],
                "suggested_questions": ["Q000073", "Q000033", "Q000115"],
                "suggested_exam": ["SG_rigidity", "SG_rebound_tenderness"],
                "suggested_investigations": ["IX_ct_abdomen", "IX_cbc", "IX_basic_metabolic_panel"],
            },
            {
                "id": "PAT_dist_mass",
                "label": "Mass / organomegaly concern",
                "diagnosis_code": "DX_abdominal_mass_suspect",
                "diagnosis_label": "Abdominal mass (suspect)",
                "weight_sum_required": 1.2,
                "criteria": [
                    {"kind": "exam", "sign_code": "SG_abdominal_mass", "op": "present", "weight": 1.4, "finding": "Palpable mass"},
                    {"kind": "answer", "question_id": "Q000019", "op": "truthy", "weight": 0.5, "finding": "Weight loss"},
                ],
                "suggested_questions": ["Q000019", "Q000026"],
                "suggested_exam": ["SG_abdominal_mass", "SG_ascites"],
                "suggested_investigations": ["IX_ct_abdomen", "IX_cbc", "IX_liver_panel"],
            },
        ],
        "missing": [
            {"id": "need_tempo", "if_unanswered": ["Q000115"], "message": "Ask how quickly abdomen enlarged", "next_questions": ["Q000115"]},
        ],
        "ix_bundles": [
            {"id": "IXB_dist_baseline", "label": "Distention baseline", "urgency": "urgent",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_cbc", "IX_liver_panel", "IX_basic_metabolic_panel"]},
            {"id": "IXB_dist_ascites", "label": "Ascites workup", "urgency": "urgent",
             "when": {"any": [{"pattern_id": "PAT_dist_ascites"}, {"sign_code": "SG_ascites", "op": "present"}]},
             "investigations": ["IX_abdominal_ultrasound", "IX_liver_panel", "IX_coagulation_panel"]},
            {"id": "IXB_dist_obstruction", "label": "Obstruction imaging", "urgency": "emergency",
             "when": {"any": [{"pattern_id": "PAT_dist_obstruction"}]},
             "investigations": ["IX_ct_abdomen"],
             "referral_hint": "Urgent surgical review"},
        ],
    },
    "heartburn": {
        "complaint_code": "CC_heartburn",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_hb_gerd",
                "label": "Typical GERD / reflux pattern",
                "diagnosis_code": "DX_gerd_suspect",
                "diagnosis_label": "GERD (suspect)",
                "weight_sum_required": 1.0,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000043", "op": "in", "value": ["Worse after meals", "Worse when lying flat"], "weight": 0.9, "finding": "Postprandial / positional"},
                ],
                "suggested_questions": ["Q000031", "Q000033", "Q000019"],
                "suggested_exam": [],
                "suggested_investigations": ["IX_upper_endoscopy"],
            },
            {
                "id": "PAT_hb_alarm",
                "label": "Heartburn with alarm features",
                "diagnosis_code": "DX_gerd_alarm_suspect",
                "diagnosis_label": "Reflux with alarms (suspect)",
                "weight_sum_required": 1.3,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000031", "op": "truthy", "weight": 1.0, "finding": "Dysphagia"},
                    {"kind": "answer", "question_id": "Q000019", "op": "truthy", "weight": 0.8, "finding": "Weight loss"},
                    {"kind": "answer", "question_id": "Q000033", "op": "truthy", "weight": 1.0, "finding": "Hematemesis"},
                ],
                "suggested_questions": ["Q000034", "Q000077"],
                "suggested_exam": ["SG_pallor"],
                "suggested_investigations": ["IX_upper_endoscopy", "IX_cbc"],
            },
        ],
        "missing": [
            {"id": "need_alarms", "if_unanswered_any": ["Q000031", "Q000019", "Q000033"], "message": "Screen dysphagia / weight loss / bleed", "next_questions": ["Q000031", "Q000019", "Q000033"]},
        ],
        "ix_bundles": [
            {"id": "IXB_hb_alarm_endo", "label": "Alarm-feature endoscopy", "urgency": "urgent",
             "when": {"any": [{"pattern_id": "PAT_hb_alarm"}, {"question_id": "Q000031", "op": "truthy"}]},
             "investigations": ["IX_upper_endoscopy", "IX_cbc"]},
            {"id": "IXB_hb_routine", "label": "Typical reflux — endoscopy if indicated", "urgency": "routine",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_upper_endoscopy"]},
        ],
    },
    "constipation": {
        "complaint_code": "CC_constipation",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_const_obstruction",
                "label": "Obstipation / obstruction alarm",
                "diagnosis_code": "DX_constipation_obstruction_suspect",
                "diagnosis_label": "Possible obstruction (suspect)",
                "weight_sum_required": 1.5,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000045", "op": "truthy", "weight": 1.3, "finding": "Inability to pass stool/gas"},
                    {"kind": "answer", "question_id": "Q000022", "op": "truthy", "weight": 0.6, "finding": "Vomiting"},
                    {"kind": "answer", "question_id": "Q000073", "op": "truthy", "weight": 0.7, "finding": "Severe pain"},
                ],
                "suggested_questions": ["Q000025", "Q000035"],
                "suggested_exam": ["SG_rigidity", "SG_rebound_tenderness"],
                "suggested_investigations": ["IX_ct_abdomen", "IX_cbc"],
            },
            {
                "id": "PAT_const_alarm_colon",
                "label": "Constipation with colorectal alarms",
                "diagnosis_code": "DX_constipation_alarm_suspect",
                "diagnosis_label": "Constipation with alarms (suspect)",
                "weight_sum_required": 1.3,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000019", "op": "truthy", "weight": 0.9, "finding": "Weight loss"},
                    {"kind": "answer", "question_id": "Q000035", "op": "truthy", "weight": 0.9, "finding": "Rectal bleeding"},
                ],
                "suggested_questions": ["Q000045"],
                "suggested_exam": ["SG_abdominal_mass"],
                "suggested_investigations": ["IX_cbc", "IX_colonoscopy"],
            },
        ],
        "missing": [
            {"id": "need_obstipation", "if_unanswered": ["Q000045"], "message": "Ask about gas/stool passage", "next_questions": ["Q000045"]},
        ],
        "ix_bundles": [
            {"id": "IXB_const_baseline", "label": "Constipation baseline", "urgency": "routine",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_cbc", "IX_basic_metabolic_panel"]},
            {"id": "IXB_const_obstruction", "label": "Obstruction imaging", "urgency": "emergency",
             "when": {"any": [{"pattern_id": "PAT_const_obstruction"}]},
             "investigations": ["IX_ct_abdomen"]},
        ],
    },
    "dysphagia": {
        "complaint_code": "CC_dysphagia",
        "min_history": 5,
        "patterns": [
            {
                "id": "PAT_dys_impaction",
                "label": "Food impaction / obstructive dysphagia",
                "diagnosis_code": "DX_food_impaction_suspect",
                "diagnosis_label": "Food impaction / obstructive dysphagia (suspect)",
                "weight_sum_required": 1.2,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000031", "op": "truthy", "weight": 0.8, "finding": "Dysphagia"},
                    {"kind": "answer", "question_id": "Q000058", "op": "truthy", "weight": 1.0, "finding": "Food impaction"},
                ],
                "suggested_questions": ["Q000019", "Q000033"],
                "suggested_exam": [],
                "suggested_investigations": ["IX_upper_endoscopy"],
            },
            {
                "id": "PAT_dys_alarm",
                "label": "Dysphagia with red flags",
                "diagnosis_code": "DX_dysphagia_alarm_suspect",
                "diagnosis_label": "Dysphagia with alarms (suspect)",
                "weight_sum_required": 1.3,
                "criteria": [
                    {"kind": "answer", "question_id": "Q000019", "op": "truthy", "weight": 1.0, "finding": "Weight loss"},
                    {"kind": "answer", "question_id": "Q000033", "op": "truthy", "weight": 0.8, "finding": "Hematemesis"},
                ],
                "suggested_questions": ["Q000058"],
                "suggested_exam": ["SG_pallor"],
                "suggested_investigations": ["IX_upper_endoscopy", "IX_cbc"],
            },
        ],
        "missing": [
            {"id": "need_impaction", "if_unanswered": ["Q000058"], "message": "Ask about food impaction", "next_questions": ["Q000058"]},
        ],
        "ix_bundles": [
            {"id": "IXB_dys_endo", "label": "Dysphagia endoscopy", "urgency": "urgent",
             "when": {"always_if_complaint": True},
             "investigations": ["IX_upper_endoscopy"],
             "referral_hint": "Urgent endoscopy if progressive dysphagia or alarms"},
        ],
    },
}


def main() -> None:
    written = []
    for slug, spec in packs.items():
        reasoning = {
            "complaint_code": spec["complaint_code"],
            "schema_version": 1,
            "revision": 1,
            "min_history_answers_for_dx": spec["min_history"],
            "min_confidence_to_list_dx": 0.45,
            "description": f"Starter reasoning pack for {spec['complaint_code']} (practical, not Sleisenger-complete).",
            "patterns": spec["patterns"],
            "missing_info_rules": spec["missing"],
        }
        investigation = {
            "complaint_code": spec["complaint_code"],
            "schema_version": 1,
            "revision": 1,
            "description": f"Starter investigation framework for {spec['complaint_code']}. Names/urgency/indications only.",
            "bundles": spec["ix_bundles"],
        }
        (reasoning_dir / f"{slug}.json").write_text(
            json.dumps(reasoning, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (ix_dir / f"{slug}.json").write_text(
            json.dumps(investigation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        written.append(slug)

    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["revision"] = int(manifest.get("revision") or 5) + 1
    rp = manifest.setdefault("rule_packs", {})
    reason = ["rules/reasoning/abdominal_pain.json"] + [
        f"rules/reasoning/{s}.json" for s in sorted(written)
    ]
    ix = ["rules/investigation/abdominal_pain.json"] + [
        f"rules/investigation/{s}.json" for s in sorted(written)
    ]
    seen: set[str] = set()
    rp["reasoning"] = [x for x in reason if not (x in seen or seen.add(x))]
    seen = set()
    rp["investigation"] = [x for x in ix if not (x in seen or seen.add(x))]
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", len(written), "packs:", ", ".join(written))
    print("manifest revision", manifest["revision"])
    print("reasoning", len(rp["reasoning"]), "investigation", len(rp["investigation"]))


if __name__ == "__main__":
    main()
