"""Encounter Belief State (EBS) — specialty-agnostic continuous assessment object."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_ebs(*, release_id: int | None = None, release_code: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "release_id": release_id,
        "release_code": release_code,
        "updated_at": _now(),
        "presenting_problems": [],
        "active_section": None,
        "section_agenda": [],
        "section_objective": None,
        "hypotheses": {},  # disease_code -> hypothesis dict
        "red_flags": [],
        "active_pathways": [],
        "missing_critical": [],
        "suggested_next_action": {"kind": "intake", "detail": "Capture presenting problem(s)"},
        "findings_ledger": [],
        "exam_priorities": [],
        "investigation_recommendations": [],
        "management_recommendations": [],
        "follow_up_recommendations": [],
        "differential": [],
        "working_diagnoses": [],
        "stopping": {"status": "continue", "reasons": []},
        "narrative_draft": "",
        "summary_edits": {},
        "plan_edits": {},
        "explainability": [],
        "channel": "history",
    }


def clone_ebs(ebs: dict) -> dict:
    return copy.deepcopy(ebs)


def touch(ebs: dict) -> dict:
    ebs["updated_at"] = _now()
    return ebs


def append_finding(
    ebs: dict,
    *,
    code: str,
    kind: str,
    polarity: str,
    value: str | None = None,
    source: str = "history",
    meta: dict | None = None,
) -> dict:
    """polarity: present | absent | unknown | not_assessed | indeterminate"""
    entry = {
        "code": code,
        "kind": kind,
        "polarity": polarity,
        "value": value,
        "source": source,
        "meta": meta or {},
        "at": _now(),
    }
    # Replace prior entry for same code+source if present
    ledger = [f for f in ebs.get("findings_ledger") or [] if not (f.get("code") == code and f.get("source") == source)]
    ledger.append(entry)
    ebs["findings_ledger"] = ledger
    return touch(ebs)


def finding_present(ebs: dict, code: str) -> bool:
    for f in ebs.get("findings_ledger") or []:
        if f.get("code") == code and f.get("polarity") == "present":
            return True
    return False


def add_explanation(ebs: dict, text: str, *, category: str = "general", refs: list | None = None) -> None:
    ebs.setdefault("explainability", []).append(
        {"at": _now(), "category": category, "text": text, "refs": refs or []}
    )
