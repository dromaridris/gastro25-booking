"""Intelligent chief complaint search — autocomplete, prefix, fuzzy, synonym matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.modules.clinical_intake.models import (
    ChiefComplaintEntry,
    ChiefComplaintTerm,
    TERM_TYPE_ABBREVIATION,
    TERM_TYPE_ALIAS,
    TERM_TYPE_SYNONYM,
    normalize_text,
)


@dataclass
class ComplaintSearchResult:
    complaint_id: int
    code: str
    display_name: str
    normalized_name: str
    category_name: str | None
    specialty_code: str | None
    matched_term: str | None = None
    match_type: str = "display"
    score: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "complaint_id": self.complaint_id,
            "code": self.code,
            "display_name": self.display_name,
            "normalized_name": self.normalized_name,
            "category_name": self.category_name,
            "specialty_code": self.specialty_code,
            "matched_term": self.matched_term,
            "match_type": self.match_type,
            "score": round(self.score, 2),
            "metadata": self.metadata,
        }


class ComplaintSearchEngine:
    """Specialty-agnostic complaint search over the configured library."""

    def __init__(self, *, specialty_code: str | None = None) -> None:
        self.specialty_code = specialty_code

    def search(self, query: str, *, limit: int = 10) -> list[ComplaintSearchResult]:
        normalized_query = normalize_text(query)
        if not normalized_query:
            return []

        candidates: dict[int, ComplaintSearchResult] = {}
        entries = self._load_entries()
        terms = self._load_terms()

        for entry in entries:
            self._score_entry(entry, normalized_query, candidates)
        for term in terms:
            self._score_term(term, normalized_query, candidates)

        ranked = sorted(candidates.values(), key=lambda item: (-item.score, item.display_name))
        return ranked[:limit]

    def resolve(self, query: str) -> ComplaintSearchResult | None:
        results = self.search(query, limit=1)
        if not results:
            return None
        top = results[0]
        if top.score < 55:
            return None
        return top

    def _load_entries(self) -> list[ChiefComplaintEntry]:
        query = ChiefComplaintEntry.query.filter_by(is_active=True, is_archived=False)
        if self.specialty_code:
            query = query.filter(
                (ChiefComplaintEntry.specialty_code == self.specialty_code)
                | (ChiefComplaintEntry.specialty_code.is_(None))
            )
        return query.order_by(ChiefComplaintEntry.sort_order, ChiefComplaintEntry.display_name).all()

    def _load_terms(self) -> list[ChiefComplaintTerm]:
        query = ChiefComplaintTerm.query.filter_by(is_archived=False)
        if self.specialty_code:
            query = query.join(ChiefComplaintEntry).filter(
                (ChiefComplaintEntry.specialty_code == self.specialty_code)
                | (ChiefComplaintEntry.specialty_code.is_(None))
            )
        return query.all()

    def _score_entry(
        self,
        entry: ChiefComplaintEntry,
        normalized_query: str,
        candidates: dict[int, ComplaintSearchResult],
    ) -> None:
        category_name = entry.category.name if entry.category else None
        base = ComplaintSearchResult(
            complaint_id=entry.id,
            code=entry.code,
            display_name=entry.display_name,
            normalized_name=entry.normalized_name,
            category_name=category_name,
            specialty_code=entry.specialty_code,
        )

        checks = [
            (entry.normalized_name, "normalized_exact", 100.0),
            (entry.display_name, "display_exact", 98.0),
            (entry.normalized_name, "normalized_prefix", 90.0, True),
            (entry.display_name, "display_prefix", 85.0, True),
            (entry.normalized_name, "normalized_partial", 75.0, False, True),
            (entry.display_name, "display_partial", 72.0, False, True),
        ]
        for check in checks:
            text, match_type, score = check[0], check[1], check[2]
            normalized_text = normalize_text(text)
            prefix = len(check) > 3 and check[3]
            partial = len(check) > 4 and check[4]
            if normalized_text == normalized_query:
                self._upsert(candidates, base, match_type, score, text)
            elif prefix and normalized_text.startswith(normalized_query):
                self._upsert(candidates, base, match_type, score, text)
            elif partial and normalized_query in normalized_text:
                self._upsert(candidates, base, match_type, score, text)
            else:
                fuzzy = self._fuzzy_score(normalized_query, normalized_text)
                if fuzzy >= 0.72:
                    self._upsert(candidates, base, "fuzzy_display", 55 + fuzzy * 10, text)

    def _score_term(
        self,
        term: ChiefComplaintTerm,
        normalized_query: str,
        candidates: dict[int, ComplaintSearchResult],
    ) -> None:
        entry = term.complaint
        if entry is None or not entry.is_active or entry.is_archived:
            return

        category_name = entry.category.name if entry.category else None
        base = ComplaintSearchResult(
            complaint_id=entry.id,
            code=entry.code,
            display_name=entry.display_name,
            normalized_name=entry.normalized_name,
            category_name=category_name,
            specialty_code=entry.specialty_code,
        )
        term_text = term.normalized_term
        type_bonus = {
            TERM_TYPE_SYNONYM: 80.0,
            TERM_TYPE_ALIAS: 78.0,
            TERM_TYPE_ABBREVIATION: 76.0,
        }.get(term.term_type, 75.0)

        if term_text == normalized_query:
            self._upsert(candidates, base, term.term_type, type_bonus + 5, term.term_text)
        elif term_text.startswith(normalized_query):
            self._upsert(candidates, base, f"{term.term_type}_prefix", type_bonus, term.term_text)
        elif normalized_query in term_text:
            self._upsert(candidates, base, f"{term.term_type}_partial", type_bonus - 5, term.term_text)
        else:
            fuzzy = self._fuzzy_score(normalized_query, term_text)
            if fuzzy >= 0.75:
                self._upsert(candidates, base, f"{term.term_type}_fuzzy", 50 + fuzzy * 10, term.term_text)

    def _upsert(
        self,
        candidates: dict[int, ComplaintSearchResult],
        base: ComplaintSearchResult,
        match_type: str,
        score: float,
        matched_term: str,
    ) -> None:
        existing = candidates.get(base.complaint_id)
        if existing is None or score > existing.score:
            candidates[base.complaint_id] = ComplaintSearchResult(
                complaint_id=base.complaint_id,
                code=base.code,
                display_name=base.display_name,
                normalized_name=base.normalized_name,
                category_name=base.category_name,
                specialty_code=base.specialty_code,
                matched_term=matched_term,
                match_type=match_type,
                score=score,
            )

    @staticmethod
    def _fuzzy_score(left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()
