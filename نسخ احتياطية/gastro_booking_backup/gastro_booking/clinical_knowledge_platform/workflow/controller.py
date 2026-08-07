"""Encounter Controller — sole coordinator between workflow channels and CRE/EBS."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from clinical_knowledge_platform import repository as repo
from clinical_knowledge_platform.reasoning import ebs as ebs_mod
from clinical_knowledge_platform.reasoning.engine import (
    ClinicalReasoningEngine,
    create_session,
    load_engine,
    load_session,
    save_session,
)


class EncounterController:
    """All channels mutate state only through this controller."""

    def __init__(self, db: sqlite3.Connection, session_id: int):
        loaded = load_session(db, session_id)
        if not loaded:
            raise ValueError(f"Unknown encounter session {session_id}")
        self.db = db
        self.session_id = session_id
        self.row, self.ebs = loaded
        self.engine = load_engine(db, self.row["release_id"])

    @staticmethod
    def start(db: sqlite3.Connection, *, patient_label: str = "", release_id: int | None = None) -> "EncounterController":
        if release_id is None:
            pub = repo.latest_published_release(db)
            if not pub:
                raise ValueError("No published knowledge release — seed demo KB first")
            release_id = int(pub["id"])
        sid, _ebs = create_session(db, release_id=release_id, patient_label=patient_label)
        db.commit()
        return EncounterController(db, sid)

    def persist(self) -> None:
        save_session(self.db, self.session_id, self.ebs)
        self.db.commit()

    def set_channel(self, channel: str) -> dict:
        if channel not in ("history", "examination", "investigations", "summary", "plan"):
            raise ValueError("Invalid channel")
        self.ebs["channel"] = channel
        self.persist()
        return self.snapshot()

    def intake(self, complaints: list[str]) -> dict:
        self.engine.symptom_intake(self.ebs, complaints)
        self.engine.build_narrative_draft(self.ebs)
        self.persist()
        return self.snapshot()

    def answer_question(self, question_code: str, polarity: str, value: str | None = None) -> dict:
        """polarity: present|absent|unknown"""
        if polarity not in ("present", "absent", "unknown"):
            raise ValueError("Invalid polarity")
        self.engine.apply_finding(
            self.ebs,
            code=question_code,
            polarity=polarity,
            kind="history_question",
            value=value,
            source="history",
        )
        self.engine.build_narrative_draft(self.ebs)
        self.persist()
        return self.snapshot()

    def record_exam(self, sign_code: str, polarity: str, value: str | None = None) -> dict:
        if polarity not in ("present", "absent", "not_assessed", "unknown"):
            raise ValueError("Invalid polarity")
        self.engine.apply_finding(
            self.ebs,
            code=sign_code,
            polarity=polarity if polarity != "not_assessed" else "not_assessed",
            kind="sign",
            value=value,
            source="exam",
        )
        self.engine.build_narrative_draft(self.ebs)
        self.persist()
        return self.snapshot()

    def order_investigation(self, ix_code: str) -> dict:
        self.engine.apply_finding(
            self.ebs,
            code=ix_code,
            polarity="present",
            kind="investigation_order",
            source="investigations",
            meta={"ordered": True},
        )
        # Re-run recommendations to mark duplicates
        self.engine.recommend_investigations(self.ebs)
        self.persist()
        return self.snapshot()

    def record_result(self, finding_code: str, polarity: str = "present", value: str | None = None) -> dict:
        self.engine.apply_finding(
            self.ebs,
            code=finding_code,
            polarity=polarity,
            kind="investigation_result",
            value=value,
            source="investigations",
        )
        self.engine.build_narrative_draft(self.ebs)
        self.persist()
        return self.snapshot()

    def save_summary_edits(self, edits: dict) -> dict:
        self.ebs["summary_edits"] = {**(self.ebs.get("summary_edits") or {}), **edits}
        if edits.get("narrative_draft") is not None:
            self.ebs["narrative_draft"] = edits["narrative_draft"]
        self.persist()
        return self.snapshot()

    def save_plan_edits(self, edits: dict) -> dict:
        self.ebs["plan_edits"] = {**(self.ebs.get("plan_edits") or {}), **edits}
        self.persist()
        return self.snapshot()

    def regen_narrative(self) -> dict:
        self.engine.build_narrative_draft(self.ebs)
        self.persist()
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "patient_label": self.row.get("patient_label"),
            "release_id": self.row.get("release_id"),
            "ebs": self.ebs,
            "explainability": (self.ebs.get("explainability") or [])[-30:],
        }
