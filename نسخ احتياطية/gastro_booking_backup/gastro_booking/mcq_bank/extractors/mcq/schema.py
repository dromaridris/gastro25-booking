"""
MCQ payload contract. Every read/write of an MCQ ContentItem's payload_json
must go through build_payload()/read_payload() - never touch the dict
directly elsewhere in the codebase. That discipline is what makes a future
move to a dedicated `mcq_items` table a pure migration.
"""

REQUIRED_KEYS = {"question_text", "options", "correct_answer", "explanation_text", "references"}


def build_payload(question_text, options, correct_answer, explanation_text, references):
    """options: list of {"letter": "A", "text": "..."}"""
    return {
        "question_text": question_text,
        "options": options,
        "correct_answer": correct_answer,
        "explanation_text": explanation_text,
        "references": references,
    }


def read_payload(payload: dict):
    missing = REQUIRED_KEYS - payload.keys()
    if missing:
        raise ValueError(f"MCQ payload missing keys: {missing}")
    return payload


def student_view(payload: dict, reveal_answer: bool):
    """Strips anything the student shouldn't see pre-answer. Post-answer,
    reveals correct_answer + explanation but never internal fields like
    confidence_flag / raw_extracted_text - those never enter this function
    at all, they live one level up in content_items and are stripped by
    the route/serializer before this is even called."""
    options = [{"letter": o["letter"], "text": o["text"]} for o in payload["options"]]
    out = {"question_text": payload["question_text"], "options": options}
    if reveal_answer:
        out["correct_answer"] = payload["correct_answer"]
        out["explanation_text"] = payload["explanation_text"]
        out["references"] = payload["references"]
    return out
