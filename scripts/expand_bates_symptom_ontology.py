"""Expand clinical_knowledge to a Bates-aligned practical symptom ontology.

Maps the user's long symptom inventory into:
  - CC packs (primary complaints with full history templates)
  - synonyms on templates
  - associated / red-flag shared questions
Never creates disease/syndrome complaint codes (UGIB, GERD, ascites, etc.).
"""

from __future__ import annotations

import json
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
CORE_HPI = [f"Q{i:06d}" for i in range(1, 17)]  # Q000001–Q000016


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path.relative_to(ROOT.parent))


def q(
    qid: str,
    prompt: str,
    answer_type: str = "boolean",
    *,
    dedupe_key: str,
    bates_domain: str = "associated_symptoms",
    priority: str = "routine",
    choices: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    obj = {
        "id": qid,
        "prompt": prompt,
        "answer_type": answer_type,
        "bates_domain": bates_domain,
        "dedupe_key": dedupe_key,
        "priority_default": priority,
        "schema_version": 1,
        "revision": 1,
        "status": "active",
        "specialty_tags": tags or ["general"],
    }
    if choices:
        obj["choices"] = choices
    return obj


NEW_QUESTIONS = [
    # --- GI nested detail ---
    q("Q000121", "Is odynophagia (pain on swallowing) your main swallowing problem, or mainly food sticking without pain?", "choice", dedupe_key="dysphagia_vs_odynophagia_primary", bates_domain="symptom_characteristics", priority="high", choices=["Mainly pain on swallowing", "Mainly food sticking / not going down", "Both", "Not sure"], tags=["gastroenterology"]),
    q("Q000122", "Do you feel a lump in the throat unrelated to swallowing (globus)?", dedupe_key="assoc_globus", tags=["gastroenterology", "ent"]),
    q("Q000123", "What does the vomitus look/smell like?", "choice", dedupe_key="vomitus_character", bates_domain="symptom_characteristics", priority="high", choices=["Food / clear fluid", "Yellow-green (bilious)", "Brown / feculent odor", "Bloody / coffee-ground", "Not sure"], tags=["gastroenterology"]),
    q("Q000124", "Have you had early satiety (feeling full after only a small amount of food)?", dedupe_key="assoc_early_satiety", priority="high", tags=["gastroenterology"]),
    q("Q000125", "Have you had postprandial fullness or upper abdominal fullness after meals?", dedupe_key="assoc_postprandial_fullness", tags=["gastroenterology"]),
    q("Q000126", "Have you had excessive belching?", dedupe_key="assoc_belching", tags=["gastroenterology"]),
    q("Q000127", "Have you had excessive gas / flatulence?", dedupe_key="assoc_flatulence", tags=["gastroenterology"]),
    q("Q000128", "Have you had hiccups that are new or persistent?", dedupe_key="assoc_hiccups", tags=["gastroenterology"]),
    q("Q000129", "Have you noticed a change in your usual bowel habit (frequency, form, or timing)?", dedupe_key="assoc_bowel_habit_change", priority="high", tags=["gastroenterology"]),
    q("Q000130", "Do you have tenesmus (constant urge to defecate with straining and little stool)?", dedupe_key="assoc_tenesmus", priority="high", tags=["gastroenterology"]),
    q("Q000131", "Is defecation painful?", dedupe_key="assoc_painful_defecation", tags=["gastroenterology"]),
    q("Q000132", "Do you strain hard to pass stool?", dedupe_key="assoc_straining_defecation", tags=["gastroenterology"]),
    q("Q000133", "Do you feel incomplete evacuation after a bowel movement?", dedupe_key="assoc_incomplete_evacuation", tags=["gastroenterology"]),
    q("Q000134", "Have you had accidental leakage of stool (fecal incontinence)?", dedupe_key="assoc_fecal_incontinence", priority="high", tags=["gastroenterology"]),
    q("Q000135", "Is there pus in the stool?", dedupe_key="stool_pus", priority="high", tags=["gastroenterology"]),
    q("Q000136", "Are stools greasy, floating, frothy, or unusually foul (steatorrhea-type)?", dedupe_key="stool_steatorrhea", priority="high", tags=["gastroenterology"]),
    q("Q000137", "Have you had anal pain?", dedupe_key="assoc_anal_pain", tags=["gastroenterology"]),
    q("Q000138", "Have you had anal itching?", dedupe_key="assoc_anal_itch", tags=["gastroenterology"]),
    q("Q000139", "Have you had rectal discharge?", dedupe_key="assoc_rectal_discharge", tags=["gastroenterology"]),
    q("Q000140", "Have you noticed something prolapsing from the anus, or a perianal swelling?", dedupe_key="assoc_perianal_swelling_prolapse", tags=["gastroenterology"]),
    q("Q000141", "Have you heard or felt loud bowel sounds / rumbling (borborygmi)?", dedupe_key="assoc_borborygmi", tags=["gastroenterology"]),
    q("Q000142", "Do certain foods reliably trigger your symptoms (food intolerance pattern)?", "text", dedupe_key="food_trigger_pattern", bates_domain="symptom_characteristics", tags=["gastroenterology"]),
    q("Q000143", "Have you had acid regurgitation (sour/bitter fluid coming up)?", dedupe_key="assoc_acid_regurgitation", tags=["gastroenterology"]),
    # --- Cardio / resp detail ---
    q("Q000144", "Do you get short of breath when lying flat (orthopnea)?", dedupe_key="assoc_orthopnea", priority="high", tags=["cardiology"]),
    q("Q000145", "Do you wake at night suddenly short of breath (PND)?", dedupe_key="assoc_pnd", priority="high", tags=["cardiology"]),
    q("Q000146", "Have you had coughing up blood (hemoptysis)?", dedupe_key="rf_hemoptysis", bates_domain="red_flags", priority="emergency", tags=["pulmonology", "emergency"]),
    q("Q000147", "How long have you been coughing, and is it mainly dry or productive?", "text", dedupe_key="cough_duration_type", bates_domain="symptom_characteristics", tags=["pulmonology"]),
    q("Q000148", "Do you produce sputum with cough? If yes, what colour/amount?", "text", dedupe_key="sputum_character", bates_domain="symptom_characteristics", tags=["pulmonology"]),
    q("Q000149", "Have you had wheezing?", dedupe_key="assoc_wheeze", tags=["pulmonology"]),
    q("Q000150", "Have you had chest tightness?", dedupe_key="assoc_chest_tightness", tags=["pulmonology", "cardiology"]),
    q("Q000151", "Is the chest pain sharp and worse with breathing (pleuritic)?", dedupe_key="chest_pain_pleuritic_yn", priority="high", tags=["pulmonology", "emergency"]),
    q("Q000152", "Have you had palpitations (awareness of heartbeat: racing, fluttering, pounding)?", dedupe_key="assoc_palpitations", priority="high", tags=["cardiology"]),
    q("Q000153", "Have you fainted or lost consciousness?", dedupe_key="rf_syncope_loc", bates_domain="red_flags", priority="emergency", tags=["cardiology", "neurology", "emergency"]),
    q("Q000154", "Have you had true spinning vertigo, or more lightheadedness?", "choice", dedupe_key="dizziness_type", bates_domain="symptom_characteristics", priority="high", choices=["Spinning vertigo", "Lightheaded / near-faint", "Unsteady / off-balance", "Not sure"], tags=["neurology", "cardiology"]),
    q("Q000155", "Have you had snoring or witnessed pauses in breathing during sleep?", dedupe_key="assoc_sleep_apnea_symptoms", tags=["pulmonology"]),
    q("Q000156", "Do your legs hurt with walking that improves with rest (claudication)?", dedupe_key="assoc_claudication", tags=["cardiology", "vascular"]),
    q("Q000157", "Are your feet or hands cold, pale, or blue (cyanosis)?", dedupe_key="assoc_cold_cyanosis_extremities", tags=["cardiology", "vascular"]),
    # --- GU (Bates abdomen chapter) ---
    q("Q000158", "Have you had burning or pain on urination (dysuria)?", dedupe_key="assoc_dysuria", priority="high", tags=["urology", "general"]),
    q("Q000159", "Have you had urinary frequency or urgency?", dedupe_key="assoc_urinary_freq_urgency", tags=["urology"]),
    q("Q000160", "Do you wake at night to urinate (nocturia)?", dedupe_key="assoc_nocturia", tags=["urology", "cardiology"]),
    q("Q000161", "Do you have hesitancy, weak stream, or incomplete bladder emptying?", dedupe_key="assoc_voiding_obstruction", tags=["urology"]),
    q("Q000162", "Have you had blood in the urine (hematuria)?", dedupe_key="rf_hematuria", bates_domain="red_flags", priority="high", tags=["urology"]),
    q("Q000163", "Have you had urinary incontinence?", dedupe_key="assoc_urinary_incontinence", tags=["urology"]),
    q("Q000164", "Have you had flank pain (side/back under the ribs)?", dedupe_key="assoc_flank_pain", priority="high", tags=["urology", "gastroenterology"]),
    q("Q000165", "Is urine cloudy or foul-smelling?", dedupe_key="urine_cloudy_foul", tags=["urology"]),
    # --- Constitutional / other ---
    q("Q000166", "Have you had fatigue or unusual loss of energy?", dedupe_key="assoc_fatigue", tags=["general"]),
    q("Q000167", "Have you had generalized weakness (not just fatigue)?", dedupe_key="assoc_weakness", tags=["general", "neurology"]),
    q("Q000168", "Have you had malaise (general unwell feeling)?", dedupe_key="assoc_malaise", tags=["general"]),
    q("Q000169", "Have you gained weight unintentionally?", dedupe_key="assoc_weight_gain", tags=["general"]),
    q("Q000170", "Have you had easy bruising or spontaneous gum/nose bleeding?", dedupe_key="assoc_easy_bleeding_bruising", priority="high", tags=["hematology", "hepatology"]),
    q("Q000171", "Have you had reduced oral intake or signs of dehydration (dry mouth, low urine)?", dedupe_key="assoc_reduced_intake_dehydration", priority="high", tags=["general"]),
    q("Q000172", "Have you had polyuria, polydipsia, or polyphagia?", dedupe_key="assoc_poly_symptoms", tags=["endocrine"]),
    q("Q000173", "Have you had heat or cold intolerance, or excessive sweating?", "text", dedupe_key="temp_intolerance_sweats", bates_domain="associated_symptoms", tags=["endocrine"]),
    q("Q000174", "Where is the headache located, and what is it like (pressure, throbbing, sudden)?", "text", dedupe_key="headache_character_location", bates_domain="symptom_characteristics", priority="high", tags=["neurology"]),
    q("Q000175", "Any headache warning features (sudden worst-ever, fever/neck stiffness, neuro deficit, trauma)?", "text", dedupe_key="rf_headache_alarms", bates_domain="red_flags", priority="emergency", tags=["neurology", "emergency"]),
    q("Q000176", "Have you had confusion, memory loss, or trouble speaking/understanding?", dedupe_key="rf_neuro_cognitive", bates_domain="red_flags", priority="emergency", tags=["neurology"]),
    q("Q000177", "Have you had numbness, tingling, tremor, or seizures?", "text", dedupe_key="assoc_neuro_sensory_seizure", bates_domain="associated_symptoms", tags=["neurology"]),
    q("Q000178", "Have you had back or neck pain related to this problem?", "text", dedupe_key="assoc_back_neck_pain", bates_domain="associated_symptoms", tags=["general"]),
    q("Q000179", "Have you had joint pain, swelling, or stiffness?", dedupe_key="assoc_joint_symptoms", tags=["rheumatology"]),
    q("Q000180", "Have you had a new skin rash, hair loss, or nail changes?", "text", dedupe_key="assoc_skin_hair_nails", bates_domain="associated_symptoms", tags=["dermatology"]),
    q("Q000181", "Have you had sore throat, hoarseness, nasal congestion, or nosebleeds?", "text", dedupe_key="assoc_ent_symptoms", bates_domain="associated_symptoms", tags=["ent"]),
    q("Q000182", "Have you had eye symptoms (pain, redness, vision change, photophobia)?", "text", dedupe_key="assoc_eye_symptoms", bates_domain="associated_symptoms", tags=["ophthalmology"]),
    q("Q000183", "Have you had anxiety, low mood, panic, insomnia, or poor concentration with this illness?", "text", dedupe_key="assoc_mood_sleep", bates_domain="associated_symptoms", tags=["psychiatry", "general"]),
    q("Q000184", "Have you noticed swollen lymph nodes?", dedupe_key="assoc_lymphadenopathy_symptom", tags=["general"]),
    q("Q000185", "Have you had mouth ulcers, dry mouth, burning mouth, or bad breath?", "text", dedupe_key="assoc_oral_symptoms", bates_domain="associated_symptoms", tags=["gastroenterology", "ent"]),
    q("Q000186", "Have you lost smell or taste?", dedupe_key="assoc_smell_taste_loss", tags=["ent", "neurology"]),
]


def ht(slug, name, synonyms, body_system, red_flags, hpi, associated, red_section, risk, associated_ccs, bg=None):
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
            {"key": "background", "title": "PMH / PSH / meds / allergies / FH / SH", "question_ids": bg or BACKGROUND},
        ],
        "associated_complaint_codes": associated_ccs,
        "schema_version": 1,
        "revision": 1,
        "status": "active",
    }


def exam_generic(slug, name, systems, priority):
    return {
        "id": f"ET_{slug}",
        "complaint_code": f"CC_{slug}",
        "name": name,
        "source": BATES_EXAM,
        "systems": systems,
        "priority_findings": priority,
        "schema_version": 1,
        "revision": 1,
        "status": "active",
    }


def edu(code, title, points, linked, coaching=None, triggers=None):
    return {
        "complaint_code": code,
        "schema_version": 1,
        "revision": 1,
        "description": "Teach-mode + passive coaching during history. Educational only.",
        "modules": [
            {
                "id": "EDU_structure",
                "title": title,
                "trigger": {"always": True},
                "points": points,
                "linked_questions": linked,
            }
        ],
        "question_coaching": coaching or {},
        "answer_triggers": triggers or [],
    }


GENERAL_EXAM = [
    {
        "key": "general",
        "title": "General appearance & vitals",
        "finding_ids": ["SG_tachycardia", "SG_hypotension", "SG_fever", "SG_pallor", "SG_dehydration"],
        "checklist": ["Distress", "Vital signs", "Hydration", "Pallor"],
    }
]


def merge_questions():
    path = ROOT / "questions" / "library.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    by_id = {x["id"]: x for x in data["questions"]}
    # Fix duplicate dedupe: keep Q000072, retarget Q000118
    if "Q000118" in by_id:
        by_id["Q000118"]["dedupe_key"] = "assoc_leg_edema_with_distention"
        by_id["Q000118"]["prompt"] = "With the abdominal swelling, have the legs or ankles swollen too?"
    for nq in NEW_QUESTIONS:
        by_id[nq["id"]] = nq
    ordered = sorted(by_id.values(), key=lambda x: x["id"])
    dump(path, {"schema_version": 1, "revision": 3, "questions": ordered})
    last = ordered[-1]["id"]
    dump(
        ROOT / "questions" / "_index.json",
        {
            "schema_version": 1,
            "revision": 3,
            "library_file": "library.json",
            "question_count": len(ordered),
            "id_range": {"first": "Q000001", "last": last},
            "next_id": int(last[1:]) + 1,
        },
    )
    return by_id


def enhance_existing():
    """Add synonyms + nested associated Qs to existing GI packs."""
    patches = {
        "heartburn.json": {
            "name": "Heartburn history",
            "synonyms": ["Pyrosis", "Acid regurgitation", "Sour taste in mouth", "Rising burning behind the breastbone"],
            "add_hpi": ["Q000143", "Q000059", "Q000060", "Q000061"],
            "add_assoc": ["Q000031", "Q000032", "Q000057", "Q000126", "Q000125", "Q000039", "Q000036"],
            "add_red": ["Q000019", "Q000033", "Q000034", "Q000058"],
        },
        "dysphagia.json": {
            "synonyms": ["Difficulty swallowing", "Food sticking", "Odynophagia (if pain is primary sensation with swallow)", "Swallowing problem"],
            "add_hpi": ["Q000121"],
            "add_assoc": ["Q000032", "Q000122", "Q000057", "Q000143", "Q000039", "Q000185", "Q000186"],
        },
        "vomiting.json": {
            "name": "Vomiting / nausea history",
            "synonyms": ["Nausea", "Emesis", "Throwing up", "Bilious vomiting", "Feculent vomiting", "Retching"],
            "add_hpi": ["Q000123"],
            "add_assoc": ["Q000124", "Q000125", "Q000171", "Q000045"],
        },
        "diarrhea.json": {
            "synonyms": ["Loose stools", "Watery stools", "Change in bowel habits toward looser stools", "Frequent stools"],
            "add_hpi": ["Q000129", "Q000130", "Q000049", "Q000135", "Q000136"],
            "add_assoc": ["Q000134", "Q000142", "Q000105"],
        },
        "constipation.json": {
            "synonyms": ["Infrequent stools", "Hard stools", "Straining", "Incomplete evacuation", "Change in bowel habits toward harder/less frequent stools"],
            "add_hpi": ["Q000129", "Q000132", "Q000133", "Q000131"],
            "add_assoc": ["Q000134", "Q000137", "Q000045", "Q000025"],
            "add_red": ["Q000045", "Q000035", "Q000019"],
        },
        "jaundice.json": {
            "synonyms": ["Yellow eyes/skin", "Icterus", "Dark urine with yellowing", "Pale stools with yellowing"],
            "add_assoc": ["Q000027", "Q000028", "Q000029", "Q000118", "Q000170"],
        },
        "abdominal_pain.json": {
            "synonyms": ["Belly pain", "Stomach pain", "Abdominal discomfort", "Epigastric pain", "Flank pain if abdominal/side", "Colicky abdominal pain"],
            "add_assoc": ["Q000124", "Q000125", "Q000129", "Q000142", "Q000164", "Q000141", "Q000178"],
        },
        "abdominal_distention.json": {
            "synonyms": [
                "Abdominal swelling",
                "Bloated abdomen",
                "Bloating",
                "Distended belly",
                "Abdominal distension",
                "Ascites (patient word for fluid) — synonym only",
                "Abdominal mass sensation",
            ],
            "add_assoc": ["Q000126", "Q000127", "Q000141", "Q000119", "Q000045"],
        },
        "hematemesis.json": {
            "synonyms": ["Vomiting blood", "Coffee-ground vomiting", "Coffee-ground emesis", "Bloody vomit", "Blood in vomitus"],
        },
        "melena.json": {
            "synonyms": ["Black stools", "Tarry stools", "Black sticky stools", "Melena"],
        },
        "hematochezia.json": {
            "synonyms": ["Rectal bleeding", "BRBPR", "Blood in stool", "Bright red blood per rectum", "Maroon stools", "Bloody stool"],
            "add_assoc": ["Q000137", "Q000138", "Q000139", "Q000140", "Q000130"],
        },
        "fever.json": {
            "synonyms": ["Pyrexia", "Feeling feverish", "Chills", "Night sweats", "Rigors"],
            "add_assoc": ["Q000018", "Q000166", "Q000168", "Q000184"],
        },
        "weight_loss.json": {
            "synonyms": ["Unintentional weight loss", "Losing weight without trying", "Reduced oral intake with weight loss"],
            "add_assoc": ["Q000124", "Q000020", "Q000171", "Q000166"],
        },
        "chest_pain.json": {
            "synonyms": ["Thoracic pain", "Pleuritic chest pain", "Chest discomfort", "Pressure in chest"],
            "add_assoc": ["Q000151", "Q000150", "Q000152", "Q000037", "Q000030"],
        },
        "dyspnea.json": {
            "synonyms": ["Shortness of breath", "Breathlessness", "Orthopnea", "Paroxysmal nocturnal dyspnea", "PND", "Difficulty breathing"],
            "add_hpi": ["Q000144", "Q000145", "Q000070"],
            "add_assoc": ["Q000147", "Q000149", "Q000072", "Q000146"],
        },
    }
    for fname, patch in patches.items():
        path = ROOT / "templates" / "history" / fname
        if not path.exists():
            continue
        t = json.loads(path.read_text(encoding="utf-8"))
        if "name" in patch:
            t["name"] = patch["name"]
        if "synonyms" in patch:
            t["synonyms"] = patch["synonyms"]
        sec = {s["key"]: s for s in t["sections"]}
        for key, add_key in [("hpi_core", "add_hpi"), ("associated", "add_assoc"), ("red_flags", "add_red"), ("risk_context", "add_risk")]:
            for qid in patch.get(add_key, []):
                if key in sec and qid not in sec[key]["question_ids"]:
                    sec[key]["question_ids"].append(qid)
        t["revision"] = int(t.get("revision") or 1) + 1
        dump(path, t)


def write_new_packs():
    packs = []

    def add(slug, name, synonyms, body, red, hpi, assoc, reds, risk, accs, edu_points, edu_linked, exam_systems=None, exam_priority=None):
        dump(ROOT / "templates" / "history" / f"{slug}.json", ht(slug, name, synonyms, body, red, hpi, assoc, reds, risk, accs))
        systems = exam_systems or GENERAL_EXAM
        priority = exam_priority or ["SG_tachycardia", "SG_hypotension"]
        dump(ROOT / "templates" / "exam" / f"{slug}.json", exam_generic(slug, f"{name.replace(' history', '')} — physical exam", systems, priority))
        dump(
            ROOT / "rules" / "education" / f"{slug}.json",
            edu(f"CC_{slug}", f"{name} — structure", edu_points, edu_linked),
        )
        packs.append((f"CC_{slug}", name.replace(" history", "")))

    add(
        "anorexia",
        "Loss of appetite / early satiety history",
        ["Anorexia", "Loss of appetite", "Early satiety", "Postprandial fullness", "Poor appetite", "Food fear"],
        "abdomen",
        ["Q000019", "Q000033", "Q000034", "Q000124"],
        CORE_HPI + ["Q000020", "Q000124", "Q000125", "Q000142"],
        ["Q000021", "Q000022", "Q000042", "Q000030", "Q000026", "Q000166", "Q000171"],
        ["Q000019", "Q000033", "Q000034", "Q000035", "Q000031"],
        ["Q000053"],
        ["CC_weight_loss", "CC_vomiting", "CC_abdominal_pain", "CC_jaundice"],
        [
            "Loss of appetite and early satiety are symptoms (Bates), not diagnoses like 'gastroparesis' or 'cancer'.",
            "Ask about food fear, pain with eating, vomiting, and weight change — these branch the pathways.",
            "Early satiety with progressive weight loss raises alarm but still belongs in symptom history first.",
        ],
        ["Q000020", "Q000124", "Q000019"],
    )

    add(
        "food_intolerance",
        "Food-triggered symptom history",
        ["Food intolerance", "Food-related symptoms", "Meal-triggered symptoms", "Lactose-type intolerance (patient language)"],
        "abdomen",
        ["Q000019", "Q000035", "Q000033"],
        CORE_HPI[:8] + ["Q000142", "Q000005", "Q000006", "Q000007"],
        ["Q000023", "Q000025", "Q000126", "Q000127", "Q000021", "Q000042", "Q000129"],
        ["Q000019", "Q000035", "Q000034", "Q000033"],
        ["Q000053"],
        ["CC_diarrhea", "CC_abdominal_pain", "CC_abdominal_distention", "CC_heartburn"],
        [
            "Food intolerance is a patient-reported pattern, not a disease label (e.g. not 'IBS' or 'allergy' as the complaint).",
            "Identify which foods, timing after ingestion, and which symptoms follow (pain, gas, diarrhea, rash).",
            "Alarm features (bleed, weight loss, nocturnal diarrhea) still apply.",
        ],
        ["Q000142", "Q000023", "Q000019"],
    )

    add(
        "anal_pain",
        "Anal / perianal symptom history",
        ["Anal pain", "Anal itching", "Perianal swelling", "Rectal discharge", "Painful defecation", "Rectal prolapse sensation"],
        "abdomen",
        ["Q000035", "Q000019", "Q000038"],
        CORE_HPI[:10] + ["Q000137", "Q000131", "Q000138", "Q000139", "Q000140"],
        ["Q000035", "Q000024", "Q000023", "Q000134", "Q000130"],
        ["Q000035", "Q000019", "Q000038", "Q000075"],
        [],
        ["CC_hematochezia", "CC_constipation", "CC_diarrhea"],
        [
            "Anal/perianal symptoms are local symptoms — not automatically 'hemorrhoids' as the complaint.",
            "Always ask about bleeding amount/colour and systemic alarm features.",
            "Prolapse/swelling and discharge change the exam focus.",
        ],
        ["Q000137", "Q000035", "Q000140"],
        GENERAL_EXAM + [{
            "key": "perianal",
            "title": "Perianal / rectal",
            "finding_ids": ["SG_perianal_findings", "SG_abnormal_stool_colour", "SG_rectal_mass"],
            "checklist": ["External inspection", "Digital rectal exam when indicated", "Stool colour"],
        }],
        ["SG_perianal_findings", "SG_hypotension"],
    )

    add(
        "fecal_incontinence",
        "Fecal incontinence history",
        ["Stool leakage", "Accidental bowel leakage", "Soiling", "Loss of bowel control"],
        "abdomen",
        ["Q000035", "Q000019", "Q000176"],
        CORE_HPI[:8] + ["Q000134", "Q000047", "Q000048", "Q000050", "Q000129"],
        ["Q000023", "Q000024", "Q000163", "Q000137", "Q000166"],
        ["Q000035", "Q000019", "Q000176"],
        [],
        ["CC_diarrhea", "CC_constipation", "CC_anal_pain"],
        [
            "Fecal incontinence is the symptom; do not start with 'neurogenic bowel' or 'sphincter injury' as the complaint.",
            "Clarify urgency-related vs passive leakage, stool consistency, and coexisting urinary incontinence.",
        ],
        ["Q000134", "Q000050", "Q000048"],
    )

    add(
        "pruritus",
        "Itching (pruritus) history",
        ["Itching", "Generalized itch", "Pruritus", "Itchy skin"],
        "skin",
        ["Q000026", "Q000019", "Q000170"],
        CORE_HPI[:8] + ["Q000029"],
        ["Q000026", "Q000027", "Q000028", "Q000180", "Q000166"],
        ["Q000026", "Q000019", "Q000170"],
        ["Q000063"],
        ["CC_jaundice", "CC_fatigue"],
        [
            "Pruritus is a symptom. Cholestasis is a pathway you may reach after jaundice/dark urine/pale stool clustering — not the complaint label.",
            "Ask about distribution, night predominance, and biliary/hepatic companion symptoms.",
        ],
        ["Q000029", "Q000026", "Q000027"],
    )

    add(
        "weight_gain",
        "Weight gain history",
        ["Unintentional weight gain", "Gaining weight", "Fluid-related weight gain (patient language)"],
        "general",
        ["Q000037", "Q000072", "Q000046"],
        CORE_HPI[:8] + ["Q000169", "Q000097"],
        ["Q000072", "Q000046", "Q000037", "Q000144", "Q000173"],
        ["Q000037", "Q000144", "Q000145"],
        [],
        ["CC_edema", "CC_abdominal_distention", "CC_dyspnea"],
        [
            "Weight gain is a symptom/sign pattern (tissue vs fluid). Heart failure, ascites, and endocrine disease are differentials — not complaint codes.",
            "Ask about edema, orthopnea, and abdominal swelling to separate fluid overload pathways.",
        ],
        ["Q000169", "Q000072", "Q000046"],
    )

    add(
        "fatigue",
        "Fatigue / low energy history",
        ["Fatigue", "Low energy", "Tiredness", "Malaise", "Weakness (patient language — clarify true motor weakness)"],
        "general",
        ["Q000019", "Q000037", "Q000038", "Q000176"],
        CORE_HPI[:8] + ["Q000166", "Q000167", "Q000168"],
        ["Q000017", "Q000018", "Q000019", "Q000026", "Q000037", "Q000183"],
        ["Q000019", "Q000038", "Q000176", "Q000033", "Q000034"],
        [],
        ["CC_weight_loss", "CC_fever", "CC_jaundice", "CC_dyspnea"],
        [
            "Fatigue ≠ neurologic weakness (Bates). Clarify energy vs true power loss.",
            "Do not label the visit 'anemia' or 'depression' as the chief complaint — those are later considerations.",
        ],
        ["Q000166", "Q000167", "Q000019"],
    )

    add(
        "cough",
        "Cough history",
        ["Cough", "Sputum production", "Chronic cough", "Dry cough"],
        "respiratory",
        ["Q000146", "Q000037", "Q000036"],
        CORE_HPI[:10] + ["Q000039", "Q000147", "Q000148", "Q000149"],
        ["Q000037", "Q000036", "Q000017", "Q000155", "Q000030"],
        ["Q000146", "Q000037", "Q000069"],
        [],
        ["CC_hemoptysis", "CC_dyspnea", "CC_chest_pain", "CC_heartburn"],
        [
            "Cough is the symptom. Asthma/COPD/GERD/TB are differentials — not complaint codes.",
            "Always ask about hemoptysis separately; blood coughed up is not GI bleeding.",
        ],
        ["Q000039", "Q000146", "Q000148"],
    )

    add(
        "hemoptysis",
        "Coughing blood (hemoptysis) history",
        ["Hemoptysis", "Coughing blood", "Blood in sputum", "Bloody spit from chest"],
        "respiratory",
        ["Q000107", "Q000037", "Q000038"],
        CORE_HPI[:8] + ["Q000107", "Q000146", "Q000148", "Q000109", "Q000095"],
        ["Q000147", "Q000037", "Q000036", "Q000017", "Q000033"],
        ["Q000107", "Q000038", "Q000037", "Q000069"],
        [],
        ["CC_cough", "CC_dyspnea", "CC_chest_pain", "CC_hematemesis"],
        [
            "Hemoptysis is blood from the chest with cough — not UGIB and not hematemesis.",
            "First question: coughed vs vomited (same fork as Bates respiratory vs GI).",
            "Volume and cardiorespiratory instability decide urgency.",
        ],
        ["Q000107", "Q000146", "Q000109"],
    )

    add(
        "palpitations",
        "Palpitations history",
        ["Palpitations", "Racing heart", "Fluttering heart", "Pounding heartbeat", "Skipped beats"],
        "cardiovascular",
        ["Q000153", "Q000036", "Q000037"],
        CORE_HPI[:10] + ["Q000152"],
        ["Q000036", "Q000037", "Q000038", "Q000173"],
        ["Q000153", "Q000069", "Q000037"],
        [],
        ["CC_chest_pain", "CC_syncope", "CC_dyspnea"],
        [
            "Palpitations are awareness of heartbeat (Bates) — not 'AF' or 'panic attack' as the complaint.",
            "Ask about syncope, chest pain, and exertion relation.",
        ],
        ["Q000152", "Q000153", "Q000036"],
    )

    add(
        "edema",
        "Leg / body swelling (edema) history",
        ["Leg swelling", "Ankle swelling", "Edema", "Peripheral swelling", "Puffy legs"],
        "cardiovascular",
        ["Q000037", "Q000144", "Q000046"],
        CORE_HPI[:8] + ["Q000072", "Q000118"],
        ["Q000037", "Q000144", "Q000145", "Q000046", "Q000026", "Q000169"],
        ["Q000037", "Q000144", "Q000145"],
        [],
        ["CC_dyspnea", "CC_abdominal_distention", "CC_weight_gain"],
        [
            "Edema is swelling — causes include heart, liver, kidney, venous disease. Do not start with 'heart failure' or 'ascites' as the complaint.",
            "Ask about orthopnea/PND and abdominal swelling to cluster pathways.",
        ],
        ["Q000072", "Q000144", "Q000046"],
    )

    add(
        "syncope",
        "Fainting / loss of consciousness history",
        ["Syncope", "Fainting", "Blackout", "Loss of consciousness", "Collapse"],
        "cardiovascular",
        ["Q000153", "Q000036", "Q000033", "Q000034"],
        CORE_HPI[:10] + ["Q000153", "Q000038"],
        ["Q000036", "Q000037", "Q000152", "Q000154", "Q000033", "Q000034"],
        ["Q000153", "Q000069", "Q000033", "Q000034", "Q000035"],
        [],
        ["CC_dizziness", "CC_chest_pain", "CC_palpitations", "CC_hematemesis"],
        [
            "Syncope/LOC is the symptom. Do not label 'seizure' or 'cardiogenic syncope' as the chief complaint.",
            "In a GI setting, always screen bleeding and volume loss as possible precipitants.",
        ],
        ["Q000153", "Q000033", "Q000036"],
    )

    add(
        "dizziness",
        "Dizziness / vertigo / lightheadedness history",
        ["Dizziness", "Lightheadedness", "Vertigo", "Unsteadiness", "Near-fainting"],
        "neurologic",
        ["Q000153", "Q000175", "Q000176"],
        CORE_HPI[:8] + ["Q000154", "Q000038"],
        ["Q000036", "Q000037", "Q000174", "Q000033", "Q000034", "Q000152"],
        ["Q000153", "Q000175", "Q000176"],
        [],
        ["CC_syncope", "CC_headache", "CC_hematemesis"],
        [
            "Separate spinning vertigo from lightheaded near-syncope (Bates cardiac vs vestibular pathways).",
            "Do not use 'labyrinthitis' or 'hypotension' as the complaint code.",
        ],
        ["Q000154", "Q000153", "Q000038"],
    )

    add(
        "headache",
        "Headache history",
        ["Headache", "Cephalgia", "Head pain", "Migraine-type headache (patient language)"],
        "neurologic",
        ["Q000175", "Q000176", "Q000017"],
        CORE_HPI + ["Q000040", "Q000174", "Q000175"],
        ["Q000021", "Q000017", "Q000018", "Q000037", "Q000182", "Q000022"],
        ["Q000175", "Q000176", "Q000069"],
        [],
        ["CC_fever", "CC_dizziness", "CC_vomiting"],
        [
            "Headache is the symptom. Migraine/SAH/meningitis are differentials — never the complaint picker label.",
            "Screen Bates headache warning signs early.",
        ],
        ["Q000040", "Q000175"],
    )

    add(
        "flank_pain",
        "Flank pain history",
        ["Flank pain", "Side pain", "Loin pain", "Pain under the ribs at the side", "Ureteric colic-type pain (patient description)"],
        "abdomen",
        ["Q000162", "Q000017", "Q000038"],
        CORE_HPI + ["Q000164", "Q000042"],
        ["Q000158", "Q000159", "Q000162", "Q000165", "Q000021", "Q000022", "Q000017"],
        ["Q000162", "Q000017", "Q000038", "Q000045"],
        [],
        ["CC_abdominal_pain", "CC_dysuria", "CC_hematuria"],
        [
            "Flank pain is a location symptom (Bates urinary/renal). Pyelo/stone/AAA are differentials — not CCs.",
            "Ask dysuria, hematuria, fever, and radiation to groin.",
        ],
        ["Q000164", "Q000162", "Q000158"],
    )

    add(
        "dysuria",
        "Painful / difficult urination history",
        ["Dysuria", "Burning urination", "Urinary frequency", "Urinary urgency", "Hesitancy", "Weak stream", "Incomplete bladder emptying", "Urinary retention sensation"],
        "urinary",
        ["Q000162", "Q000017", "Q000164"],
        CORE_HPI[:8] + ["Q000158", "Q000159", "Q000160", "Q000161"],
        ["Q000162", "Q000165", "Q000163", "Q000164", "Q000017"],
        ["Q000162", "Q000017", "Q000164"],
        [],
        ["CC_hematuria", "CC_flank_pain", "CC_fever"],
        [
            "Dysuria/voiding symptoms are symptoms — not 'UTI' as the chief complaint.",
            "Clarify storage vs voiding symptoms; screen hematuria and fever.",
        ],
        ["Q000158", "Q000159", "Q000162"],
    )

    add(
        "hematuria",
        "Blood in urine (hematuria) history",
        ["Hematuria", "Blood in urine", "Red urine", "Pink urine"],
        "urinary",
        ["Q000162", "Q000038", "Q000017"],
        CORE_HPI[:8] + ["Q000162", "Q000165"],
        ["Q000158", "Q000159", "Q000164", "Q000034", "Q000035", "Q000019"],
        ["Q000038", "Q000017", "Q000019"],
        [],
        ["CC_dysuria", "CC_flank_pain", "CC_abdominal_pain"],
        [
            "Hematuria is blood in urine — analogous to melena/hematochezia principle: symptom first, disease later.",
            "Do not label the visit 'bladder cancer' or 'UTI' as the complaint.",
            "Distinguish true hematuria from other causes of red urine when possible.",
        ],
        ["Q000162", "Q000158", "Q000164"],
    )

    add(
        "back_pain",
        "Back pain history",
        ["Back pain", "Low back pain", "Thoracolumbar pain", "Neck pain with back"],
        "musculoskeletal",
        ["Q000037", "Q000167", "Q000176"],
        CORE_HPI + ["Q000178"],
        ["Q000042", "Q000164", "Q000036", "Q000167", "Q000177"],
        ["Q000037", "Q000176", "Q000069"],
        [],
        ["CC_abdominal_pain", "CC_flank_pain", "CC_chest_pain"],
        [
            "Back/neck pain are symptoms. In GI clinic, still ask about abdominal/flank radiation and red flags.",
            "Do not use 'disc disease' or 'musculoskeletal strain' as the complaint code.",
        ],
        ["Q000178", "Q000042", "Q000164"],
    )

    return packs


def rewrite_index(new_packs):
    # Stable curated order: GI-first, then constitutional, then cross-system
    order = [
        ("CC_abdominal_pain", "Abdominal pain"),
        ("CC_abdominal_distention", "Abdominal distention / swelling"),
        ("CC_heartburn", "Heartburn"),
        ("CC_dysphagia", "Dysphagia"),
        ("CC_vomiting", "Vomiting / nausea"),
        ("CC_hematemesis", "Blood in vomitus (hematemesis)"),
        ("CC_melena", "Black tarry stools (melena)"),
        ("CC_hematochezia", "Rectal bleeding (hematochezia)"),
        ("CC_diarrhea", "Diarrhea"),
        ("CC_constipation", "Constipation"),
        ("CC_anorexia", "Loss of appetite / early satiety"),
        ("CC_food_intolerance", "Food-triggered symptoms"),
        ("CC_anal_pain", "Anal / perianal symptoms"),
        ("CC_fecal_incontinence", "Fecal incontinence"),
        ("CC_jaundice", "Jaundice"),
        ("CC_pruritus", "Itching (pruritus)"),
        ("CC_flank_pain", "Flank pain"),
        ("CC_dysuria", "Painful / difficult urination"),
        ("CC_hematuria", "Blood in urine (hematuria)"),
        ("CC_weight_loss", "Unintentional weight loss"),
        ("CC_weight_gain", "Weight gain"),
        ("CC_fever", "Fever"),
        ("CC_fatigue", "Fatigue / low energy"),
        ("CC_chest_pain", "Chest pain"),
        ("CC_dyspnea", "Dyspnea / shortness of breath"),
        ("CC_cough", "Cough"),
        ("CC_hemoptysis", "Coughing blood (hemoptysis)"),
        ("CC_palpitations", "Palpitations"),
        ("CC_edema", "Leg / body swelling (edema)"),
        ("CC_syncope", "Fainting / loss of consciousness"),
        ("CC_dizziness", "Dizziness / vertigo / lightheadedness"),
        ("CC_headache", "Headache"),
        ("CC_back_pain", "Back pain"),
    ]
    dump(
        ROOT / "packs" / "complaints" / "_index.json",
        {
            "schema_version": 1,
            "revision": 3,
            "complaints": [
                {
                    "complaint_code": code,
                    "history_template": f"templates/history/{code[3:]}.json",
                    "name": f"{name} history",
                }
                for code, name in order
            ],
            "design_note": (
                "Chief complaints are Bates-style patient symptoms only. "
                "Near-duplicates belong in synonyms[] or associated/red-flag questions. "
                "Never list diagnoses/syndromes (UGIB, LGIB, GERD, ascites, portal hypertension, "
                "cholecystitis, pancreatitis, UTI, heart failure, IBS, etc.) as complaint codes."
            ),
        },
    )
    return [c for c, _ in order]


def rewrite_manifest(codes):
    hist = sorted((ROOT / "templates" / "history").glob("*.json"))
    # exclude any misplaced exam_* leftovers if present
    hist = [p for p in hist if not p.name.startswith("exam_")]
    exam = sorted((ROOT / "templates" / "exam").glob("*.json"))
    edu_files = sorted((ROOT / "rules" / "education").glob("*.json"))
    lib = json.loads((ROOT / "questions" / "library.json").read_text(encoding="utf-8"))
    dump(
        ROOT / "manifest.json",
        {
            "schema_version": 1,
            "revision": 5,
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
                "Symptom-only chief complaints (Bates).",
                "User symptom inventory mapped to CC packs + synonyms + associated/red-flag questions.",
            ],
        },
    )


def delete_syndrome_leftovers():
    for rel in [
        "templates/history/exam_gi_bleeding.json",
        "templates/history/exam_ascites_portal_htn.json",
        "templates/history/exam_pancreatobiliary_pain.json",
        "templates/exam/gi_bleeding.json",
        "templates/exam/ascites_portal_htn.json",
        "templates/exam/pancreatobiliary_pain.json",
        "rules/education/gi_bleeding.json",
        "rules/education/ascites_portal_htn.json",
        "rules/education/pancreatobiliary_pain.json",
    ]:
        p = ROOT / rel
        if p.exists():
            p.unlink()
            print("deleted", rel)


def write_docs():
    (ROOT / "HISTORY_SYMPTOM_MODEL.md").write_text(
        """# History symptom model (Bates-aligned)

## Rule (applies to EVERY system)

**Chief complaint = patient symptom.** Never put a syndrome or diagnosis in the complaint picker.

The bleeding examples below illustrate the *logic* — the same logic applies to abdomen, chest, urine, neuro, etc.

| Not a chief complaint | Symptom complaints / where it lives |
|----------------------|-------------------------------------|
| UGIB / upper GI bleed | `CC_hematemesis`, `CC_melena`, sometimes `CC_hematochezia` |
| LGIB / lower GI bleed | `CC_hematochezia` (± melena) |
| GERD / reflux disease | `CC_heartburn` (+ regurgitation as synonym/associated) |
| Ascites / portal hypertension | `CC_abdominal_distention` (+ exam) |
| Cholecystitis / pancreatitis | `CC_abdominal_pain` (character/location questions) |
| Peptic ulcer disease | pain/bleed **symptoms** first (`CC_abdominal_pain`, `CC_hematemesis`, …) |
| Bowel obstruction | `CC_vomiting` / `CC_abdominal_distention` / `CC_abdominal_pain` + obstipation red flags |
| UTI / pyelonephritis | `CC_dysuria`, `CC_flank_pain`, `CC_hematuria`, `CC_fever` |
| Bladder cancer | never a CC — may follow `CC_hematuria` work-up |
| Heart failure | `CC_dyspnea`, `CC_edema`, `CC_orthopnea` questions — not `CC_heart_failure` |
| Asthma / COPD | `CC_cough`, `CC_dyspnea`, `CC_wheeze` questions |
| Stroke / seizure | neuro **symptoms** (`CC_syncope`, `CC_dizziness`, deficit red flags) — not disease CCs |
| IBS / IBD as labels | bowel **symptoms** (`CC_diarrhea`, `CC_constipation`, incontinence, blood) |
| Depression / anemia as visit label | `CC_fatigue`, `CC_weight_loss`, mood associated Qs |

## How the user's long inventory was mapped

1. **CC packs** — primary complaints that deserve their own Bates-style template (see `packs/complaints/_index.json`).
2. **synonyms[]** — near-duplicates of a CC (e.g. coffee-ground vomiting → hematemesis; rectal bleeding → hematochezia; ascites word → abdominal_distention).
3. **Associated / red-flag questions** — important but usually not a standalone visit reason (tenesmus, steatorrhea, mucus/pus, early satiety, orthopnea, PND, claudication, etc.).
4. **Deferred as own CC** — rare isolated ENT/eye/derm/psych items stay as associated text questions for now (`Q000180`–`Q000183`, `Q000181`, `Q000182`) rather than dozens of thin packs. Promote later if clinics need them.

## Bates sources

- Ch.4 constitutional: fatigue, fever/chills/night sweats, weight change, pain
- Ch.8–9 thorax/CV: chest pain, dyspnea/orthopnea/PND, cough, wheeze, palpitations, edema, syncope
- Ch.11 abdomen: GI + urinary concerning symptoms (pain, heartburn, nausea/vomiting/blood, anorexia/early satiety, dysphagia/odynophagia, bowel change, diarrhea, constipation, jaundice, dysuria, hematuria, flank pain, …)

## Drop-in deploy

Replace the whole `clinical_knowledge/` folder (or set `CLINICAL_KNOWLEDGE_ROOT`), then clear CI knowledge cache / restart the app.
""",
        encoding="utf-8",
    )
    print("wrote clinical_knowledge/HISTORY_SYMPTOM_MODEL.md")


def validate(codes):
    lib = {q["id"]: q for q in json.loads((ROOT / "questions" / "library.json").read_text(encoding="utf-8"))["questions"]}
    bad = []
    for code in codes:
        slug = code[3:]
        ht_path = ROOT / "templates" / "history" / f"{slug}.json"
        if not ht_path.exists():
            bad.append(f"missing history {slug}")
            continue
        t = json.loads(ht_path.read_text(encoding="utf-8"))
        if t.get("complaint_code") != code:
            bad.append(f"code mismatch {slug}")
        for sec in t["sections"]:
            for qid in sec["question_ids"]:
                if qid not in lib:
                    bad.append(f"{slug} missing {qid}")
        if not (ROOT / "templates" / "exam" / f"{slug}.json").exists():
            bad.append(f"missing exam {slug}")
        if not (ROOT / "rules" / "education" / f"{slug}.json").exists():
            bad.append(f"missing education {slug}")
    if bad:
        raise SystemExit("VALIDATION FAILED:\n" + "\n".join(bad))
    print(f"OK: {len(codes)} complaints, {len(lib)} questions")


def main():
    merge_questions()
    enhance_existing()
    write_new_packs()
    delete_syndrome_leftovers()
    codes = rewrite_index([])
    rewrite_manifest(codes)
    write_docs()
    # refresh heartburn education title away from GERD-as-disease framing lightly
    hb = ROOT / "rules" / "education" / "heartburn.json"
    if hb.exists():
        e = json.loads(hb.read_text(encoding="utf-8"))
        e["complaint_code"] = "CC_heartburn"
        if e.get("modules"):
            e["modules"][0]["points"] = [
                "Heartburn is a symptom (rising retrosternal burning). GERD is a diagnosis you may reach later — not the complaint code.",
                "Ask about regurgitation, dysphagia, odynophagia, vomiting, bleeding, weight loss (Bates alarm features).",
                "Exertional 'indigestion' still needs a cardiac screen.",
            ]
        e["revision"] = int(e.get("revision") or 1) + 1
        dump(hb, e)
    validate(codes)


if __name__ == "__main__":
    main()
