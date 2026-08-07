"""Rebuild Bates-aligned symptom chief complaints into clinical_knowledge/.

Clinical rule (Bates Ch.11 + teaching practice):
  Chief complaint = patient-reported symptom, NEVER a syndrome/diagnosis.
  - UGIB / LGIB / ascites / portal HTN / pancreatobiliary disease are differentials,
    reached AFTER history — not picker labels.
  - Blood in vomitus may be GI OR respiratory (hemoptysis) — always discriminate.
  - Abdominal distention covers gas, fluid, mass, organomegaly, pregnancy, etc.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "clinical_knowledge"
BATES = {
    "work": "Bates' Guide to Physical Examination and History Taking",
    "note": "Structure for history-taking only; not for disease extraction.",
}
BATES_EXAM = {
    "work": "Bates' Guide to Physical Examination and History Taking",
    "note": "Exam organization only; findings recorded against dictionary sign codes.",
}

BACKGROUND = [
    "Q000078", "Q000079", "Q000080", "Q000081", "Q000082", "Q000083",
    "Q000084", "Q000085", "Q000086", "Q000087", "Q000088", "Q000089", "Q000090",
]

NEW_QUESTIONS = [
    {
        "id": "Q000107",
        "prompt": "Was the blood coughed up from the chest, or brought up with vomiting from the stomach?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "blood_source_route",
        "priority_default": "emergency",
        "choices": [
            "Coughed up (from the chest / lungs)",
            "Vomited / retched up (from the stomach)",
            "Came up without clear cough or vomit",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "pulmonology", "emergency"],
    },
    {
        "id": "Q000108",
        "prompt": "What did the material look like when it came up?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "vomitus_appearance",
        "priority_default": "emergency",
        "choices": [
            "Bright red blood",
            "Dark / coffee-ground material",
            "Mixed blood with food or fluid",
            "Frothy / mixed with sputum (possibly from chest)",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "emergency"],
    },
    {
        "id": "Q000109",
        "prompt": "About how much bloody material came up (best estimate)?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "blood_volume_estimate",
        "priority_default": "emergency",
        "choices": [
            "Teaspoon or streaks",
            "A few spoonfuls",
            "About a cup",
            "More than a cup / continuous",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "emergency"],
    },
    {
        "id": "Q000110",
        "prompt": "Did prolonged retching or vomiting come before you saw blood?",
        "answer_type": "boolean",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "retching_before_blood",
        "priority_default": "high",
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology"],
    },
    {
        "id": "Q000111",
        "prompt": "Are you taking iron tablets, bismuth, charcoal, or foods/medicines that darken the stool?",
        "answer_type": "boolean",
        "bates_domain": "risk_factors",
        "dedupe_key": "black_stool_confounders",
        "priority_default": "routine",
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology"],
    },
    {
        "id": "Q000112",
        "prompt": "Is the stool sticky and tar-like, or only dark without being sticky?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "stool_tarry_vs_dark",
        "priority_default": "high",
        "choices": [
            "Sticky / tar-like (true melena character)",
            "Dark but not sticky",
            "Not sure / did not look closely",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology"],
    },
    {
        "id": "Q000113",
        "prompt": "Where is the blood relative to the stool?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "blood_stool_relation",
        "priority_default": "high",
        "choices": [
            "Mixed throughout the stool",
            "On the surface of the stool",
            "Only on toilet paper / dripping into the bowl",
            "Large volume separate from stool",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "surgery"],
    },
    {
        "id": "Q000114",
        "prompt": "What colour is the blood from the rectum?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "rectal_blood_color",
        "priority_default": "emergency",
        "choices": [
            "Bright red",
            "Dark red / maroon",
            "Mixed with black / tarry stool",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "emergency"],
    },
    {
        "id": "Q000115",
        "prompt": "How quickly has your abdomen become swollen or enlarged?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "distention_tempo",
        "priority_default": "high",
        "choices": [
            "Hours (sudden)",
            "Days",
            "Weeks",
            "Months or longer",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology"],
    },
    {
        "id": "Q000116",
        "prompt": "Does the swelling change during the day, after meals, or after passing stool or gas?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "distention_fluctuation",
        "priority_default": "routine",
        "choices": [
            "Worse after meals / gas",
            "Improves after stool or flatus",
            "Steady / does not fluctuate much",
            "Worse by evening / better in morning",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology"],
    },
    {
        "id": "Q000117",
        "prompt": "What do you think is making the belly enlarge (your impression)?",
        "answer_type": "choice",
        "bates_domain": "symptom_characteristics",
        "dedupe_key": "distention_patient_impression",
        "priority_default": "routine",
        "choices": [
            "Gas / bloating",
            "Fluid / water feeling",
            "A lump or mass",
            "Fat / weight gain",
            "Pregnancy (if applicable)",
            "Do not know",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology"],
    },
    {
        "id": "Q000118",
        "prompt": "Have you noticed swelling in the legs or ankles as well?",
        "answer_type": "boolean",
        "bates_domain": "associated_symptoms",
        "dedupe_key": "assoc_leg_edema",
        "priority_default": "high",
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "cardiology"],
    },
    {
        "id": "Q000119",
        "prompt": "Have you felt a lump or hard area in the abdomen yourself?",
        "answer_type": "boolean",
        "bates_domain": "associated_symptoms",
        "dedupe_key": "assoc_felt_mass",
        "priority_default": "high",
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "oncology"],
    },
    {
        "id": "Q000120",
        "prompt": "Have you had black stools or blood in the stool as well?",
        "answer_type": "choice",
        "bates_domain": "associated_symptoms",
        "dedupe_key": "assoc_stool_blood_any",
        "priority_default": "emergency",
        "choices": [
            "Black tarry stools",
            "Bright red blood",
            "Both",
            "Neither",
            "Not sure",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": ["gastroenterology", "emergency"],
    },
]


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path.relative_to(ROOT.parent))


def history_template(
    slug: str,
    name: str,
    synonyms: list[str],
    *,
    body_system: str,
    red_flags: list[str],
    hpi: list[str],
    associated: list[str],
    red_section: list[str],
    risk: list[str],
    associated_ccs: list[str],
    background: list[str] | None = None,
) -> dict:
    return {
        "id": f"HT_{slug}",
        "complaint_code": f"CC_{slug}",
        "name": name,
        "synonyms": synonyms,
        "body_system": body_system,
        "source": BATES,
        "red_flag_question_ids": red_flags,
        "sections": [
            {"key": "hpi_core", "title": "HPI — core characteristics", "question_ids": hpi},
            {"key": "associated", "title": "Associated symptoms", "question_ids": associated},
            {"key": "red_flags", "title": "Alarm / red flags", "question_ids": red_section},
            {"key": "risk_context", "title": "Risk factors & exposures", "question_ids": risk},
            {
                "key": "background",
                "title": "PMH / PSH / meds / allergies / FH / SH",
                "question_ids": background or BACKGROUND,
            },
        ],
        "associated_complaint_codes": associated_ccs,
        "schema_version": 1,
        "revision": 1,
        "status": "active",
    }


def exam_bleed_like(slug: str, name: str) -> dict:
    return {
        "id": f"ET_{slug}",
        "complaint_code": f"CC_{slug}",
        "name": name,
        "source": BATES_EXAM,
        "systems": [
            {
                "key": "general",
                "title": "General appearance & vitals",
                "finding_ids": [
                    "SG_tachycardia",
                    "SG_hypotension",
                    "SG_fever",
                    "SG_pallor",
                    "SG_dehydration",
                ],
                "checklist": [
                    "General distress / toxic appearance",
                    "Vital signs (HR, BP, RR, SpO2, temperature)",
                    "Hydration / mucous membranes",
                    "Pallor / colour",
                ],
            },
            {
                "key": "hemodynamic",
                "title": "Haemodynamic assessment",
                "finding_ids": ["SG_tachycardia", "SG_hypotension"],
                "checklist": [
                    "Postural pulse/BP change",
                    "Capillary refill",
                    "Level of consciousness",
                ],
            },
            {
                "key": "abdomen",
                "title": "Abdomen",
                "finding_ids": [
                    "SG_guarding",
                    "SG_rigidity",
                    "SG_ascites",
                    "SG_hepatomegaly",
                    "SG_splenomegaly",
                    "SG_caput_medusae",
                ],
                "checklist": [
                    "Tenderness / peritonism",
                    "Stigmata of chronic liver disease if relevant",
                ],
            },
            {
                "key": "rectal",
                "title": "Rectal examination",
                "finding_ids": [
                    "SG_abnormal_stool_colour",
                    "SG_rectal_mass",
                    "SG_perianal_findings",
                ],
                "checklist": [
                    "Stool colour/consistency on glove",
                    "Masses",
                    "Perianal source (haemorrhoids/fissure)",
                ],
            },
            {
                "key": "chest_if_needed",
                "title": "Chest (if blood-in-mouth source unclear)",
                "finding_ids": [],
                "checklist": [
                    "Respiratory distress / crackles / focal findings when hemoptysis possible",
                ],
            },
        ],
        "priority_findings": ["SG_hypotension", "SG_tachycardia", "SG_pallor"],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
    }


def exam_distention() -> dict:
    return {
        "id": "ET_abdominal_distention",
        "complaint_code": "CC_abdominal_distention",
        "name": "Abdominal distention — physical exam",
        "source": BATES_EXAM,
        "systems": [
            {
                "key": "general",
                "title": "General appearance & vitals",
                "finding_ids": [
                    "SG_tachycardia",
                    "SG_hypotension",
                    "SG_fever",
                    "SG_jaundice",
                    "SG_icteric_sclera",
                    "SG_pallor",
                ],
                "checklist": [
                    "General distress",
                    "Vital signs",
                    "Jaundice / pallor",
                ],
            },
            {
                "key": "abdomen_inspection",
                "title": "Abdomen — inspection",
                "finding_ids": [
                    "SG_ascites",
                    "SG_caput_medusae",
                    "SG_visible_peristalsis",
                    "SG_hernia",
                    "SG_abdominal_mass",
                ],
                "checklist": [
                    "Contour / symmetry of distention",
                    "Flank fullness",
                    "Scars / stomas",
                    "Visible peristalsis",
                    "Hernial orifices",
                ],
            },
            {
                "key": "abdomen_percussion_fluid",
                "title": "Abdomen — percussion (gas vs fluid vs mass)",
                "finding_ids": ["SG_ascites", "SG_hepatomegaly", "SG_abdominal_mass"],
                "checklist": [
                    "Tympany vs dullness",
                    "Shifting dullness / fluid wave if ascites suspected",
                    "Liver / spleen span",
                    "Dull mass vs resonant gas",
                ],
            },
            {
                "key": "abdomen_palpation",
                "title": "Abdomen — palpation",
                "finding_ids": [
                    "SG_guarding",
                    "SG_rigidity",
                    "SG_hepatomegaly",
                    "SG_splenomegaly",
                    "SG_abdominal_mass",
                    "SG_hernia",
                ],
                "checklist": [
                    "Tenderness / guarding",
                    "Organomegaly",
                    "Masses",
                    "Hernias",
                ],
            },
            {
                "key": "extremities_neuro",
                "title": "Extremities & neuro screen",
                "finding_ids": ["SG_peripheral_edema"],
                "checklist": [
                    "Pitting oedema",
                    "Asterixis / mental status if liver disease suspected",
                ],
            },
        ],
        "priority_findings": [
            "SG_ascites",
            "SG_abdominal_mass",
            "SG_visible_peristalsis",
            "SG_rigidity",
        ],
        "schema_version": 1,
        "revision": 1,
        "status": "active",
    }


def edu(complaint_code: str, structure_title: str, points: list[str], linked: list[str], coaching: dict, triggers: list) -> dict:
    return {
        "complaint_code": complaint_code,
        "schema_version": 1,
        "revision": 1,
        "description": "Teach-mode + passive coaching during history. Educational only.",
        "modules": [
            {
                "id": "EDU_structure",
                "title": structure_title,
                "trigger": {"always": True},
                "points": points,
                "linked_questions": linked,
            }
        ],
        "question_coaching": coaching,
        "answer_triggers": triggers,
    }


def patch_library() -> None:
    path = ROOT / "questions" / "library.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in data["questions"]}

    # Refine existing bleed Qs to be symptom-precise (not syndrome).
    if "Q000093" in by_id:
        by_id["Q000093"].update(
            {
                "prompt": "What colour was the blood you saw?",
                "bates_domain": "symptom_characteristics",
                "status": "active",
                "revision": max(1, int(by_id["Q000093"].get("revision") or 1)),
            }
        )
    for qid, prompt, domain in [
        ("Q000094", "About how much blood was there?", "symptom_characteristics"),
        ("Q000095", "How many times has this bleeding happened?", "symptom_characteristics"),
        (
            "Q000096",
            "Have you ever been told you have a stomach ulcer or swollen veins in the food pipe (varices)?",
            "risk_factors",
        ),
    ]:
        if qid in by_id:
            by_id[qid]["prompt"] = prompt
            by_id[qid]["bates_domain"] = domain
            by_id[qid]["status"] = "active"

    # Distention-related existing Q — keep British synonym in prompt, broaden meaning.
    if "Q000025" in by_id:
        by_id["Q000025"]["prompt"] = "Have you had bloating or abdominal distention (belly swelling)?"
        by_id["Q000025"]["dedupe_key"] = "assoc_bloating_distention"
    if "Q000046" in by_id:
        by_id["Q000046"]["prompt"] = "Have you noticed progressive abdominal distention (belly getting larger)?"

    for q in NEW_QUESTIONS:
        by_id[q["id"]] = q

    ordered = sorted(by_id.values(), key=lambda q: q["id"])
    dump(path, {"schema_version": 1, "revision": 2, "questions": ordered})

    last = ordered[-1]["id"]
    dump(
        ROOT / "questions" / "_index.json",
        {
            "schema_version": 1,
            "revision": 2,
            "library_file": "library.json",
            "question_count": len(ordered),
            "id_range": {"first": "Q000001", "last": last},
            "next_id": int(last[1:]) + 1,
        },
    )


def patch_abdominal_pain() -> None:
    path = ROOT / "templates" / "history" / "abdominal_pain.json"
    t = json.loads(path.read_text(encoding="utf-8"))
    hpi = t["sections"][0]["question_ids"]
    for qid in ["Q000102", "Q000103", "Q000104", "Q000106"]:
        if qid not in hpi:
            hpi.append(qid)
    assoc = t["sections"][1]["question_ids"]
    if "Q000105" not in assoc:
        assoc.append("Q000105")
    # Keep associated complaints as symptoms only
    t["associated_complaint_codes"] = [
        "CC_vomiting",
        "CC_diarrhea",
        "CC_constipation",
        "CC_jaundice",
        "CC_abdominal_distention",
        "CC_hematemesis",
        "CC_melena",
        "CC_hematochezia",
    ]
    t["revision"] = int(t.get("revision") or 1) + 1
    dump(path, t)


def write_symptom_packs() -> None:
    # --- Hematemesis / blood in vomitus ---
    dump(
        ROOT / "templates" / "history" / "hematemesis.json",
        history_template(
            "hematemesis",
            "Blood in vomitus (hematemesis) history",
            ["Vomiting blood", "Coffee-ground emesis", "Bloody vomit"],
            body_system="abdomen",
            red_flags=["Q000107", "Q000038", "Q000034", "Q000035", "Q000075"],
            hpi=[
                "Q000001", "Q000002", "Q000003", "Q000004", "Q000005",
                "Q000107", "Q000108", "Q000109", "Q000095", "Q000110",
                "Q000093", "Q000094",
            ],
            associated=[
                "Q000021", "Q000022", "Q000042", "Q000030", "Q000120",
                "Q000038", "Q000037", "Q000039", "Q000020", "Q000019",
            ],
            red_section=["Q000107", "Q000038", "Q000034", "Q000035", "Q000075", "Q000019"],
            risk=["Q000096", "Q000098", "Q000053"],
            associated_ccs=["CC_melena", "CC_hematochezia", "CC_abdominal_pain", "CC_vomiting", "CC_dyspnea"],
            background=BACKGROUND + ["Q000091"],
        ),
    )
    dump(ROOT / "templates" / "exam" / "hematemesis.json", exam_bleed_like("hematemesis", "Blood in vomitus — physical exam"))
    dump(
        ROOT / "rules" / "education" / "hematemesis.json",
        edu(
            "CC_hematemesis",
            "Blood in vomitus — history structure",
            [
                "This is a symptom pack: blood coming from the mouth with vomiting/retching. It is NOT synonymous with 'upper GI bleed'.",
                "First discriminate coughed blood (hemoptysis) from vomited blood (hematemesis) — respiratory sources can look like 'GI bleeding'.",
                "Then characterize colour, volume, and preceding retching. Coffee-ground or frank blood with melena raises concern for upper GI bleeding as a diagnosis to work up later.",
                "Haemodynamic symptoms (dizziness, syncope) and NSAID/anticoagulant/liver-disease context decide urgency.",
            ],
            ["Q000107", "Q000108", "Q000109", "Q000038"],
            {
                "Q000107": {
                    "why_ask": "Blood from the chest is not GI bleeding. Mislabeling as UGIB sends the work-up down the wrong path.",
                    "listen_for": ["Cough with frothy sputum", "true vomiting/retching"],
                    "think": "If coughed up → think airway/lungs. If vomited → think esophagus/stomach/duodenum.",
                },
                "Q000110": {
                    "why_ask": "Forceful retching before blood suggests Mallory–Weiss tear among other causes.",
                    "listen_for": ["Retching then bright red blood"],
                    "think": "Still a symptom history — diagnosis comes after clustering findings.",
                },
            },
            [
                {
                    "id": "AT_hemoptysis_pattern",
                    "question_id": "Q000107",
                    "title": "Unlocked: possible hemoptysis (not GI)",
                    "points": [
                        "Do not frame this as UGIB.",
                        "Examine the chest and pursue respiratory bleeding sources.",
                    ],
                    "answer_in": ["Coughed up (from the chest / lungs)"],
                }
            ],
        ),
    )

    # --- Melena ---
    dump(
        ROOT / "templates" / "history" / "melena.json",
        history_template(
            "melena",
            "Black tarry stools (melena) history",
            ["Black stools", "Tarry stools", "Melena"],
            body_system="abdomen",
            red_flags=["Q000033", "Q000038", "Q000035", "Q000075"],
            hpi=[
                "Q000001", "Q000002", "Q000003", "Q000004", "Q000005",
                "Q000112", "Q000094", "Q000095", "Q000047", "Q000048",
            ],
            associated=[
                "Q000033", "Q000035", "Q000021", "Q000022", "Q000042",
                "Q000038", "Q000019", "Q000020", "Q000017",
            ],
            red_section=["Q000033", "Q000038", "Q000035", "Q000075", "Q000019"],
            risk=["Q000111", "Q000096", "Q000098", "Q000053"],
            associated_ccs=["CC_hematemesis", "CC_hematochezia", "CC_abdominal_pain", "CC_vomiting"],
        ),
    )
    dump(ROOT / "templates" / "exam" / "melena.json", exam_bleed_like("melena", "Black tarry stools — physical exam"))
    dump(
        ROOT / "rules" / "education" / "melena.json",
        edu(
            "CC_melena",
            "Black stools — history structure",
            [
                "Melena is a stool appearance (black, tarry), not a diagnosis of UGIB.",
                "Confirm tarry character and exclude iron/bismuth/food confounders before escalating.",
                "Ask about blood in vomitus and haemodynamic symptoms — these may later support an upper GI bleeding diagnosis.",
                "Massive upper bleeding can also present with hematochezia — keep both symptoms on the board.",
            ],
            ["Q000112", "Q000111", "Q000033", "Q000038"],
            {
                "Q000111": {
                    "why_ask": "Iron and bismuth commonly mimic melena without bleeding.",
                    "listen_for": ["Iron tablets", "bismuth", "charcoal"],
                    "think": "Dark non-tarry stool on iron ≠ melena.",
                },
                "Q000112": {
                    "why_ask": "True melena is sticky/tar-like; mere dark colour is weaker evidence.",
                    "listen_for": ["Sticky", "tar"],
                    "think": "Tarry + occult blood context strengthens bleeding concern.",
                },
            },
            [
                {
                    "id": "AT_iron_confounder",
                    "question_id": "Q000111",
                    "title": "Unlocked: possible non-bleed dark stool",
                    "points": [
                        "Iron/bismuth can darken stool without GI bleeding.",
                        "Still examine for haemodynamic compromise if the story is unclear.",
                    ],
                    "answer_in": ["yes"],
                }
            ],
        ),
    )

    # --- Hematochezia ---
    dump(
        ROOT / "templates" / "history" / "hematochezia.json",
        history_template(
            "hematochezia",
            "Bright red / maroon blood per rectum (hematochezia) history",
            ["Rectal bleeding", "BRBPR", "Bloody stool", "Hematochezia"],
            body_system="abdomen",
            red_flags=["Q000038", "Q000033", "Q000034", "Q000075", "Q000019"],
            hpi=[
                "Q000001", "Q000002", "Q000003", "Q000004", "Q000005",
                "Q000114", "Q000113", "Q000094", "Q000095", "Q000047", "Q000048",
            ],
            associated=[
                "Q000023", "Q000024", "Q000042", "Q000021", "Q000033", "Q000034",
                "Q000038", "Q000019", "Q000017", "Q000050",
            ],
            red_section=["Q000038", "Q000033", "Q000034", "Q000075", "Q000019", "Q000045"],
            risk=["Q000096", "Q000098", "Q000053", "Q000052"],
            associated_ccs=["CC_melena", "CC_hematemesis", "CC_diarrhea", "CC_abdominal_pain", "CC_constipation"],
        ),
    )
    dump(
        ROOT / "templates" / "exam" / "hematochezia.json",
        exam_bleed_like("hematochezia", "Rectal bleeding — physical exam"),
    )
    dump(
        ROOT / "rules" / "education" / "hematochezia.json",
        edu(
            "CC_hematochezia",
            "Rectal bleeding — history structure",
            [
                "Hematochezia is a symptom (red/maroon blood per rectum), not automatically 'lower GI bleed'.",
                "Blood only on paper often points to anorectal sources; mixed or large-volume maroon blood may be colonic or brisk upper source.",
                "Always ask about haemodynamic instability and concurrent melena/hematemesis — massive upper bleeding can present this way.",
                "Do not label UGIB/LGIB in the complaint picker; those labels belong to later reasoning.",
            ],
            ["Q000114", "Q000113", "Q000038", "Q000034"],
            {
                "Q000113": {
                    "why_ask": "Surface/paper blood vs mixed-through stool changes the likely source.",
                    "listen_for": ["Toilet paper only", "mixed throughout", "large separate volume"],
                    "think": "Paper streaks → hemorrhoid/fissure more likely; large maroon volume → proximal or brisk bleed.",
                }
            },
            [
                {
                    "id": "AT_paper_only",
                    "question_id": "Q000113",
                    "title": "Unlocked: possible anorectal source",
                    "points": [
                        "Blood only on paper often reflects hemorrhoids or fissure — still examine.",
                        "Large volume or instability overrides a 'benign anorectal' assumption.",
                    ],
                    "answer_in": ["Only on toilet paper / dripping into the bowl"],
                }
            ],
        ),
    )

    # --- Abdominal distention ---
    dump(
        ROOT / "templates" / "history" / "abdominal_distention.json",
        history_template(
            "abdominal_distention",
            "Abdominal distention history",
            [
                "Abdominal swelling",
                "Bloated abdomen",
                "Distended belly",
                "Abdominal distension",
                "Ascites (patient may say fluid) — use as synonym only, not as diagnosis label",
            ],
            body_system="abdomen",
            red_flags=["Q000045", "Q000033", "Q000034", "Q000035", "Q000075", "Q000019"],
            hpi=[
                "Q000001", "Q000002", "Q000003", "Q000004", "Q000005",
                "Q000115", "Q000116", "Q000117", "Q000046", "Q000025",
            ],
            associated=[
                "Q000042", "Q000021", "Q000022", "Q000023", "Q000024",
                "Q000026", "Q000118", "Q000119", "Q000099", "Q000097",
                "Q000020", "Q000019", "Q000038",
            ],
            red_section=["Q000045", "Q000033", "Q000034", "Q000035", "Q000075", "Q000019", "Q000099"],
            risk=["Q000098", "Q000100", "Q000101", "Q000063", "Q000053"],
            associated_ccs=["CC_abdominal_pain", "CC_vomiting", "CC_constipation", "CC_jaundice", "CC_weight_loss"],
        ),
    )
    dump(ROOT / "templates" / "exam" / "abdominal_distention.json", exam_distention())
    dump(
        ROOT / "rules" / "education" / "abdominal_distention.json",
        edu(
            "CC_abdominal_distention",
            "Abdominal distention — history structure",
            [
                "Distention means the abdomen is enlarged — causes include gas, fluid (ascites), mass/tumour, organomegaly, constipation/obstruction, obesity, and pregnancy.",
                "Do not start with 'ascites' or 'portal hypertension' as the complaint. Those are exam/differential labels reached after the story and signs.",
                "Tempo + fluctuation (meals/gas vs steady) + associated jaundice/leg oedema/confusion/obstipation split the major pathways.",
                "Patient impression (gas vs fluid vs lump) is useful but never definitive — confirm on examination.",
            ],
            ["Q000115", "Q000116", "Q000117", "Q000045", "Q000118"],
            {
                "Q000117": {
                    "why_ask": "Patients often sense gas vs fluid vs lump; it guides exam focus without naming a disease.",
                    "listen_for": ["Gas", "water/fluid", "hard lump"],
                    "think": "Gas → tympany; fluid → shifting dullness; mass → focal dullness/palpable lesion.",
                },
                "Q000045": {
                    "why_ask": "Inability to pass stool or gas with distention raises obstruction concern.",
                    "listen_for": ["No flatus", "no stool", "vomiting"],
                    "think": "Obstipation + distention → surgical/obstruction pathway.",
                },
            },
            [
                {
                    "id": "AT_obstipation",
                    "question_id": "Q000045",
                    "title": "Unlocked: possible obstruction pattern",
                    "points": [
                        "Distention with obstipation needs urgent surgical assessment.",
                        "Do not assume ascites until obstruction and mass are considered.",
                    ],
                    "answer_in": ["yes"],
                }
            ],
        ),
    )


def rewrite_index_and_manifest() -> None:
    complaints = [
        ("CC_abdominal_pain", "Abdominal pain"),
        ("CC_abdominal_distention", "Abdominal distention / swelling"),
        ("CC_hematemesis", "Blood in vomitus (hematemesis)"),
        ("CC_melena", "Black tarry stools (melena)"),
        ("CC_hematochezia", "Rectal bleeding (hematochezia)"),
        ("CC_chest_pain", "Chest pain"),
        ("CC_constipation", "Constipation"),
        ("CC_diarrhea", "Diarrhea"),
        ("CC_dysphagia", "Dysphagia"),
        ("CC_dyspnea", "Dyspnea / shortness of breath"),
        ("CC_fever", "Fever"),
        ("CC_heartburn", "Heartburn / reflux"),
        ("CC_jaundice", "Jaundice"),
        ("CC_vomiting", "Vomiting / nausea"),
        ("CC_weight_loss", "Unintentional weight loss"),
    ]
    dump(
        ROOT / "packs" / "complaints" / "_index.json",
        {
            "schema_version": 1,
            "revision": 2,
            "complaints": [
                {
                    "complaint_code": code,
                    "history_template": f"templates/history/{code[3:]}.json",
                    "name": f"{name} history",
                }
                for code, name in complaints
            ],
            "design_note": (
                "Chief complaints are Bates-style patient symptoms only. "
                "Do not list UGIB, LGIB, ascites, portal hypertension, or pancreatobiliary disease as complaints — "
                "those belong to differential/reasoning after history."
            ),
        },
    )

    hist = sorted((ROOT / "templates" / "history").glob("*.json"))
    exam = sorted((ROOT / "templates" / "exam").glob("*.json"))
    edu_files = sorted((ROOT / "rules" / "education").glob("*.json"))
    lib = json.loads((ROOT / "questions" / "library.json").read_text(encoding="utf-8"))
    codes = [c for c, _ in complaints]
    dump(
        ROOT / "manifest.json",
        {
            "schema_version": 1,
            "revision": 4,
            "phase": "1-16",
            "dictionary_index": "dictionary/_index.json",
            "question_library": "questions/library.json",
            "evidence_registry": "evidence/registry.json",
            "history_templates": [f"templates/history/{p.name}" for p in hist],
            "exam_templates": [f"templates/exam/{p.name}" for p in exam],
            "rule_packs": {
                "history_branching": ["rules/history_branching/abdominal_pain.json"],
                "reasoning": ["rules/reasoning/abdominal_pain.json"],
                "investigation": ["rules/investigation/abdominal_pain.json"],
                "management": ["rules/management/abdominal_pain.json"],
                "interpretation": ["rules/interpretation/abdominal_pain.json"],
                "procedures": ["rules/procedures/abdominal_pain.json"],
                "scoring": ["rules/scoring/abdominal_pain.json"],
                "education": [f"rules/education/{p.name}" for p in edu_files],
                "research": ["rules/research/knowledge_gaps.json"],
            },
            "complaint_codes": codes,
            "question_count": len(lib.get("questions", [])),
            "template_count": len(hist),
            "validation": {"missing_question_refs": [], "ok": True},
            "runtime_package": "clinical_intelligence",
            "notes": [
                "Chief complaints are symptom-only (Bates Ch.11).",
                "Syndrome labels (UGIB, ascites, portal HTN, pancreatobiliary disease) are not complaint codes.",
                "Pancreatobiliary pain features live inside CC_abdominal_pain questions Q000102–Q000106.",
            ],
        },
    )


def patch_dictionary() -> None:
    path = ROOT / "dictionary" / "symptoms.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by_code = {e["code"]: e for e in data}
    # Prefer American Bates spelling as primary label; keep British as synonym.
    if "SX_abdominal_distension" in by_code:
        e = by_code["SX_abdominal_distension"]
        e["label"] = "Abdominal distention"
        e["synonyms"] = sorted(
            set(e.get("synonyms") or [])
            | {"Abdominal distension", "Bloating", "Swollen abdomen", "Abdominal swelling"}
        )
        e["revision"] = int(e.get("revision") or 1) + 1
    # Ensure symptom entries exist for the three bleed presentations (already present).
    for code, label, syns in [
        ("SX_hematemesis", "Hematemesis", ["Vomiting blood", "Blood in vomitus", "Coffee-ground emesis"]),
        ("SX_melena", "Melena", ["Black tarry stools", "Black stools"]),
        ("SX_hematochezia", "Hematochezia", ["Bright red blood per rectum", "Rectal bleeding", "BRBPR"]),
    ]:
        if code in by_code:
            e = by_code[code]
            e["synonyms"] = sorted(set(e.get("synonyms") or []) | set(syns))
            e["revision"] = int(e.get("revision") or 1) + 1
    dump(path, list(by_code.values()) if isinstance(data, list) else data)
    # preserve list order from original
    ordered = []
    seen = set()
    for e in data:
        code = e["code"]
        ordered.append(by_code[code])
        seen.add(code)
    for code, e in by_code.items():
        if code not in seen:
            ordered.append(e)
    dump(path, ordered)


def delete_syndrome_artifacts() -> None:
    doomed = [
        ROOT / "templates" / "history" / "exam_gi_bleeding.json",
        ROOT / "templates" / "history" / "exam_ascites_portal_htn.json",
        ROOT / "templates" / "history" / "exam_pancreatobiliary_pain.json",
        ROOT / "templates" / "exam" / "gi_bleeding.json",
        ROOT / "templates" / "exam" / "ascites_portal_htn.json",
        ROOT / "templates" / "exam" / "pancreatobiliary_pain.json",
        ROOT / "rules" / "education" / "gi_bleeding.json",
        ROOT / "rules" / "education" / "ascites_portal_htn.json",
        ROOT / "rules" / "education" / "pancreatobiliary_pain.json",
        ROOT / "templates" / "history" / "gi_bleeding.json",
        ROOT / "templates" / "history" / "ascites_portal_htn.json",
        ROOT / "templates" / "history" / "pancreatobiliary_pain.json",
    ]
    for p in doomed:
        if p.exists():
            p.unlink()
            print("deleted", p.relative_to(ROOT.parent))


def write_design_doc() -> None:
    dump_md = ROOT / "HISTORY_SYMPTOM_MODEL.md"
    dump_md.write_text(
        """# History symptom model (Bates-aligned)

## Rule

**Chief complaint = patient symptom.** Never put a syndrome or diagnosis in the complaint picker.

| Not a chief complaint | Symptom complaints that may lead there |
|----------------------|----------------------------------------|
| UGIB / upper GI bleed | `CC_hematemesis`, `CC_melena`, sometimes `CC_hematochezia` |
| LGIB / lower GI bleed | `CC_hematochezia`, sometimes `CC_melena` |
| Ascites / portal hypertension | `CC_abdominal_distention` (+ exam signs) |
| Pancreatobiliary disease | `CC_abdominal_pain` (character/location Qs) |

## Why (clinical)

- Bates Ch.11 lists GI **symptoms** (pain, heartburn, nausea/vomiting including blood, dysphagia, bowel change, diarrhea, constipation, jaundice, black/bloody stools) — not disease names.
- Blood in the mouth may be **hemoptysis** (chest) or **hematemesis** (GI). Calling the visit “UGIB” skips that fork.
- Abdominal distention means the belly is enlarged — gas, fluid, mass, organomegaly, obstipation, obesity, pregnancy. Ascites is one exam/differential pathway, not the complaint.

## Drop-in deploy

Replace the whole `clinical_knowledge/` tree (or set `CLINICAL_KNOWLEDGE_ROOT`), then clear CI knowledge cache / restart app.
""",
        encoding="utf-8",
    )
    print("wrote", dump_md.relative_to(ROOT.parent))


def validate() -> None:
    lib = {q["id"]: q for q in json.loads((ROOT / "questions" / "library.json").read_text(encoding="utf-8"))["questions"]}
    index = json.loads((ROOT / "packs" / "complaints" / "_index.json").read_text(encoding="utf-8"))
    missing = []
    for c in index["complaints"]:
        code = c["complaint_code"]
        slug = code[3:]
        ht = ROOT / "templates" / "history" / f"{slug}.json"
        if not ht.exists():
            missing.append(f"history missing: {slug}")
            continue
        t = json.loads(ht.read_text(encoding="utf-8"))
        for sec in t["sections"]:
            for qid in sec["question_ids"]:
                if qid not in lib:
                    missing.append(f"{slug}: missing {qid}")
        if t.get("complaint_code") != code:
            missing.append(f"{slug}: complaint_code mismatch")
    if missing:
        raise SystemExit("VALIDATION FAILED:\n" + "\n".join(missing))
    print(f"OK: {len(index['complaints'])} complaints, {len(lib)} questions")


def main() -> None:
    patch_library()
    write_symptom_packs()
    patch_abdominal_pain()
    delete_syndrome_artifacts()
    rewrite_index_and_manifest()
    patch_dictionary()
    write_design_doc()
    validate()


if __name__ == "__main__":
    main()
