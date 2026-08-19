"""Knowledge Library — vocabulary read service and seed aggregation.

Template-specific seed data lives in ``vocabulary_seeds/`` (one module per template).
"""

from app.extensions import db
from app.modules.clinical_reports.models import VocabularyTerm
from app.modules.clinical_reports.vocabulary_seeds import VOCABULARY_SEED


def seed_vocabulary_if_empty() -> int:
    """Insert seed terms when a vocabulary has no rows. Returns count inserted."""
    inserted = 0
    for vocab_key, terms in VOCABULARY_SEED.items():
        existing = VocabularyTerm.query.filter_by(vocabulary_key=vocab_key).first()
        if existing is not None:
            continue
        for code, label, sort_order in terms:
            db.session.add(
                VocabularyTerm(
                    vocabulary_key=vocab_key,
                    code=code,
                    display_label=label,
                    sort_order=sort_order,
                    active=True,
                )
            )
            inserted += 1
    if inserted:
        db.session.commit()
    return inserted


def get_vocabulary(vocabulary_key: str) -> list[VocabularyTerm]:
    return (
        VocabularyTerm.query.filter_by(vocabulary_key=vocabulary_key, active=True)
        .order_by(VocabularyTerm.sort_order.asc(), VocabularyTerm.display_label.asc())
        .all()
    )


def vocabulary_choices(vocabulary_key: str, include_blank: bool = True) -> list[tuple[str, str]]:
    terms = get_vocabulary(vocabulary_key)
    choices = [(t.code, t.display_label) for t in terms]
    if include_blank:
        return [("", "-- Select --")] + choices
    return choices


def vocabulary_code_label_map() -> dict[str, str]:
    """Map vocabulary codes to display labels (seed plus DB when in app context)."""
    labels: dict[str, str] = {}
    for terms in VOCABULARY_SEED.values():
        for code, display_label, _sort in terms:
            labels[code] = display_label
    try:
        from flask import has_app_context

        if has_app_context():
            for term in VocabularyTerm.query.filter_by(active=True).all():
                labels[term.code] = term.display_label
    except RuntimeError:
        pass
    return labels
