"""Auto-generated consultant-level history narrative from structured answers."""

import re

from app.modules.clinical_history.models import HistoryAnswer, HistoryQuestionDefinition

SECTION_LABELS = {
    "hpi": "History of Present Illness",
    "relevant_negatives": "Relevant Negative Findings",
    "past_medical_history": "Past Medical History",
    "surgical_history": "Surgical History",
    "drug_history": "Drug History",
    "allergy_history": "Allergy History",
    "family_history": "Family History",
    "social_history": "Social History",
}

CHOICE_LABELS = {
    "acute_less_than_2_weeks": "less than 2 weeks (acute)",
    "persistent_2_to_4_weeks": "2–4 weeks (persistent)",
    "chronic_more_than_4_weeks": "more than 4 weeks (chronic)",
    "1-3": "1–3 times per day",
    "4-6": "4–6 times per day",
    "7+": "7 or more times per day",
}

HPI_SECTIONS = ("presenting", "alarm", "risk")
PRIORITY_CODES = ("q.diar.duration", "q.diar.frequency", "q.diar.blood", "q.diar.chronic_watery")


def _answers_by_section(session_id: int) -> dict[str, list[tuple[str, str, str, str]]]:
    """Return section -> [(question_code, prompt, display_answer, question_section), ...]"""
    answers = HistoryAnswer.query.filter_by(session_id=session_id, is_archived=False).all()
    qcodes = [a.question_code for a in answers]
    questions = {
        q.code: q
        for q in HistoryQuestionDefinition.query.filter(HistoryQuestionDefinition.code.in_(qcodes)).all()
    }
    grouped: dict[str, list] = {}
    for ans in answers:
        q = questions.get(ans.question_code)
        if not q:
            continue
        grouped.setdefault(q.section, []).append(
            (q.code, q.prompt_text, ans.answer_display or ans.answer_value, q.section)
        )
    return grouped


def _stem(prompt: str) -> str:
    return prompt.strip().rstrip("?").strip()


def _choice_label(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    return CHOICE_LABELS.get(cleaned, cleaned.replace("_", " "))


def _format_boolean(code: str, prompt: str, value: str, section: str) -> str | None:
    v = (value or "").lower()
    stem = _stem(prompt)
    if not stem:
        return None

    if v == "yes":
        if code == "q.diar.chronic_watery":
            return "Stools were described as chronic and watery without blood."
        if section == "alarm":
            return f"Alarm feature present: {stem.lower()}."
        if section == "exclusion":
            return f"{stem} was reported."
        return f"The patient reported {stem.lower()}."

    if v == "no":
        if section in HPI_SECTIONS:
            main = re.split(r"\s*\(", stem, maxsplit=1)[0].strip()
            return f"The patient denied {main.lower()}."
        return None

    return None


def _format_choice(code: str, prompt: str, value: str) -> str | None:
    label = _choice_label(value)
    if not label:
        return None
    if code == "q.diar.duration":
        return f"Symptoms have been present for {label}."
    if code == "q.diar.frequency":
        return f"Bowel frequency was {label}."
    stem = _stem(prompt)
    return f"{stem} was reported as {label}."


def _skip_contradictory_codes(answer_map: dict[str, str]) -> set[str]:
    skip: set[str] = set()
    if answer_map.get("q.diar.blood", "").lower() == "yes":
        if answer_map.get("q.diar.chronic_watery", "").lower() == "yes":
            skip.add("q.diar.chronic_watery")
    return skip


def _build_hpi(_session_id: int, complaint_name: str, grouped: dict) -> str:
    items: list[tuple[str, str, str, str]] = []
    for sec in HPI_SECTIONS:
        items.extend(grouped.get(sec, []))

    answer_map = {code: value for code, _prompt, value, _sec in items}
    skip = _skip_contradictory_codes(answer_map)

    sentences: list[str] = []
    seen: set[str] = set()

    def add_sentence(code: str, sentence: str | None) -> None:
        if sentence and code not in seen:
            sentences.append(sentence)
            seen.add(code)

    for code in PRIORITY_CODES:
        for item_code, prompt, value, section in items:
            if item_code != code or item_code in skip:
                continue
            if value.lower() in ("yes", "no"):
                add_sentence(item_code, _format_boolean(item_code, prompt, value, section))
            else:
                add_sentence(item_code, _format_choice(item_code, prompt, value))

    for code, prompt, value, section in items:
        if code in seen or code in skip:
            continue
        if value.lower() in ("yes", "no"):
            add_sentence(code, _format_boolean(code, prompt, value, section))
        elif value.strip():
            add_sentence(code, _format_choice(code, prompt, value))

    opener = f"The patient presents with {complaint_name.lower()}."
    if not sentences:
        return opener
    return f"{opener} {' '.join(sentences)}"


def _build_negatives(grouped: dict) -> str:
    exclusion = grouped.get("exclusion", [])
    negatives: list[str] = []
    for _code, prompt, value, _section in exclusion:
        if (value or "").lower() != "no":
            continue
        stem = _stem(prompt)
        if not stem:
            continue
        main = re.split(r"\s*\(", stem, maxsplit=1)[0].strip().lower()
        if main and main not in negatives:
            negatives.append(main)

    if not negatives:
        return "There were no significant alarm features on directed questioning."
    joined = "; ".join(negatives[:10])
    return (
        "On directed questioning to exclude alternative diagnoses, "
        f"the following were notably absent: {joined}."
    )


def _build_text_section(section_key: str, grouped: dict, fallback: str) -> str:
    mapping = {
        "past_medical_history": "pmh",
        "surgical_history": "surgical",
        "drug_history": "drugs",
        "allergy_history": "allergy",
        "family_history": "family",
        "social_history": "social",
    }
    sec = mapping.get(section_key, section_key)
    items = grouped.get(sec, [])
    texts = [disp for _c, _p, disp, _s in items if disp and disp.strip() and disp.lower() not in ("yes", "no")]
    if texts:
        return " ".join(texts)
    return fallback


def generate_all_sections(session_id: int, complaint_name: str) -> dict[str, str]:
    grouped = _answers_by_section(session_id)
    return {
        "hpi": _build_hpi(session_id, complaint_name, grouped),
        "relevant_negatives": _build_negatives(grouped),
        "past_medical_history": _build_text_section(
            "past_medical_history", grouped, "No significant past medical history reported."
        ),
        "surgical_history": _build_text_section(
            "surgical_history", grouped, "No previous relevant surgery reported."
        ),
        "drug_history": _build_text_section("drug_history", grouped, "No regular medications reported."),
        "allergy_history": _build_text_section("allergy_history", grouped, "No known drug allergies."),
        "family_history": _build_text_section(
            "family_history", grouped, "No relevant family history reported."
        ),
        "social_history": _build_text_section(
            "social_history", grouped, "Social history not elaborated."
        ),
    }
