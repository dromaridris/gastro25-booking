"""Clinical Reasoning Engine — specialty-agnostic; consumes Knowledge Graph only."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from clinical_knowledge_platform import STRENGTH_SCORE
from clinical_knowledge_platform import repository as repo
from clinical_knowledge_platform.reasoning import ebs as ebs_mod


def _score_for_rel(rel: dict) -> float:
    strength = (rel.get("strength") or "neutral").lower()
    base = STRENGTH_SCORE.get(strength, 0.0)
    # Type modifiers when strength missing nuance
    rt = rel.get("rel_type")
    if rt in ("excludes", "refutes") and base >= 0:
        return STRENGTH_SCORE["strongly_against"]
    if rt == "confirms" and base <= 0:
        return STRENGTH_SCORE["very_strong"]
    if rt == "suggests" and strength == "neutral":
        return STRENGTH_SCORE["weak"]
    return base


def _label_from_score(score: float, *, excluded: bool = False, confirmed: bool = False) -> str:
    if excluded:
        return "excluded"
    if confirmed or score >= 2.8:
        return "established" if confirmed else "very_strong"
    if score >= 2.0:
        return "strong"
    if score >= 1.0:
        return "moderate"
    if score >= 0.3:
        return "weak"
    if score > -0.3:
        return "neutral"
    if score > -1.5:
        return "against"
    return "strongly_against"


class ClinicalReasoningEngine:
    """Deterministic CRE. All medical content comes from `graph` (KG snapshot)."""

    def __init__(self, graph: dict):
        self.entities: dict[str, dict] = graph.get("entities") or {}
        self.relationships: list[dict] = graph.get("relationships") or []
        self.release_id = graph.get("release_id")
        self._by_source: dict[str, list[dict]] = {}
        self._by_target: dict[str, list[dict]] = {}
        self._by_type: dict[str, list[dict]] = {}
        for r in self.relationships:
            self._by_source.setdefault(r["source_code"], []).append(r)
            self._by_target.setdefault(r["target_code"], []).append(r)
            self._by_type.setdefault(r["rel_type"], []).append(r)

    # ----- graph helpers -----

    def entity(self, code: str) -> dict | None:
        return self.entities.get(code)

    def rels(self, *, rel_type: str | None = None, source: str | None = None, target: str | None = None) -> list[dict]:
        if source is not None:
            pool = self._by_source.get(source, [])
        elif target is not None:
            pool = self._by_target.get(target, [])
        elif rel_type is not None:
            pool = self._by_type.get(rel_type, [])
        else:
            pool = self.relationships
        out = pool
        if rel_type is not None:
            out = [r for r in out if r["rel_type"] == rel_type]
        if source is not None:
            out = [r for r in out if r["source_code"] == source]
        if target is not None:
            out = [r for r in out if r["target_code"] == target]
        return out

    def resolve_symptom(self, text: str) -> dict | None:
        t = (text or "").strip().lower()
        if not t:
            return None
        # Exact code
        if t in self.entities and self.entities[t]["entity_type"] == "symptom":
            return self.entities[t]
        for e in self.entities.values():
            if e["entity_type"] != "symptom":
                continue
            if e["label"].lower() == t or e["code"].lower() == t:
                return e
            for syn in e.get("synonyms") or []:
                if str(syn).lower() == t:
                    return e
        # Substring synonym / label match
        for e in self.entities.values():
            if e["entity_type"] != "symptom":
                continue
            label = e["label"].lower()
            if label in t or t in label:
                return e
            for syn in e.get("synonyms") or []:
                s = str(syn).lower()
                if s in t or t in s:
                    return e
        return None

    # ----- 1. Symptom intake -----

    def symptom_intake(self, ebs: dict, complaints: list[str]) -> dict:
        problems = []
        for raw in complaints:
            sx = self.resolve_symptom(raw)
            if not sx:
                ebs_mod.add_explanation(
                    ebs,
                    f"Could not map presenting text '{raw}' to a Symptom entity in the knowledge release.",
                    category="intake",
                )
                continue
            problems.append({"code": sx["code"], "label": sx["label"], "raw": raw})
            ebs_mod.append_finding(ebs, code=sx["code"], kind="symptom", polarity="present", source="intake")
        ebs["presenting_problems"] = problems
        ebs_mod.add_explanation(
            ebs,
            f"Symptom intake normalized {len(problems)} presenting problem(s).",
            category="intake",
            refs=[p["code"] for p in problems],
        )
        self.generate_hypotheses(ebs)
        self.plan_questions(ebs)
        self.detect_red_flags(ebs)
        self.rank_differential(ebs)
        self.evaluate_stopping(ebs)
        return ebs_mod.touch(ebs)

    # ----- 2. Hypothesis generation -----

    def generate_hypotheses(self, ebs: dict) -> dict:
        scores: dict[str, float] = {}
        traces: dict[str, list] = {}
        for p in ebs.get("presenting_problems") or []:
            for r in self.rels(source=p["code"], rel_type="suggests"):
                dx = r["target_code"]
                if self.entity(dx) and self.entity(dx)["entity_type"] == "disease":
                    sc = _score_for_rel(r)
                    scores[dx] = scores.get(dx, 0.0) + sc
                    traces.setdefault(dx, []).append(
                        {"rel": r["rel_type"], "from": p["code"], "strength": r.get("strength"), "delta": sc}
                    )
        # Seed from already-present findings that suggest diseases
        for f in ebs.get("findings_ledger") or []:
            if f.get("polarity") != "present":
                continue
            for r in self.rels(source=f["code"]):
                if r["rel_type"] not in ("suggests", "supports", "strongly_supports", "causes"):
                    continue
                dx = r["target_code"]
                ent = self.entity(dx)
                if not ent or ent["entity_type"] != "disease":
                    continue
                sc = _score_for_rel(r)
                scores[dx] = scores.get(dx, 0.0) + sc
                traces.setdefault(dx, []).append(
                    {"rel": r["rel_type"], "from": f["code"], "strength": r.get("strength"), "delta": sc}
                )

        hy: dict[str, dict] = {}
        for dx, sc in scores.items():
            ent = self.entity(dx)
            hy[dx] = {
                "code": dx,
                "label": ent["label"] if ent else dx,
                "score": round(sc, 3),
                "confidence": _label_from_score(sc),
                "status": "active",
                "support": [t for t in traces.get(dx, []) if t["delta"] > 0],
                "against": [t for t in traces.get(dx, []) if t["delta"] < 0],
                "must_not_miss": bool((ent or {}).get("body", {}).get("must_not_miss")),
            }
        ebs["hypotheses"] = hy
        ebs_mod.add_explanation(
            ebs,
            f"Hypothesis generation produced {len(hy)} candidate disease(s) from knowledge graph suggests/supports only.",
            category="hypothesis",
            refs=list(hy.keys()),
        )
        return ebs

    # ----- 3. Dynamic update from a finding -----

    def apply_finding(
        self,
        ebs: dict,
        *,
        code: str,
        polarity: str,
        kind: str = "finding",
        value: str | None = None,
        source: str = "history",
        meta: dict | None = None,
    ) -> dict:
        ebs_mod.append_finding(ebs, code=code, kind=kind, polarity=polarity, value=value, source=source, meta=meta)
        if polarity == "present":
            self._apply_epistemic(ebs, code, positive=True)
        elif polarity == "absent":
            self._apply_epistemic(ebs, code, positive=False)
        # unknown / not_assessed: no epistemic fire
        self.detect_red_flags(ebs)
        self.plan_questions(ebs)
        self.guide_examination(ebs)
        self.recommend_investigations(ebs)
        self.recommend_management(ebs)
        self.rank_differential(ebs)
        self.evaluate_stopping(ebs)
        self._refresh_missing(ebs)
        return ebs_mod.touch(ebs)

    def _apply_epistemic(self, ebs: dict, evidence_code: str, *, positive: bool) -> None:
        hy = ebs.setdefault("hypotheses", {})
        for r in self.rels(source=evidence_code):
            rt = r["rel_type"]
            if rt not in (
                "supports",
                "strongly_supports",
                "argues_against",
                "strongly_argues_against",
                "excludes",
                "confirms",
                "refutes",
                "suggests",
            ):
                continue
            dx = r["target_code"]
            ent = self.entity(dx)
            if not ent or ent["entity_type"] != "disease":
                continue
            if dx not in hy:
                hy[dx] = {
                    "code": dx,
                    "label": ent["label"],
                    "score": 0.0,
                    "confidence": "neutral",
                    "status": "active",
                    "support": [],
                    "against": [],
                    "must_not_miss": False,
                }
            delta = _score_for_rel(r)
            if not positive:
                # Confirmed absent: invert supportive edges if knowledge didn't declare separate absent edges
                if rt in ("supports", "strongly_supports", "suggests", "confirms"):
                    delta = -abs(delta) * 0.5
                elif rt in ("argues_against", "strongly_argues_against", "excludes", "refutes"):
                    delta = abs(delta) * 0.5
            hy[dx]["score"] = round(float(hy[dx].get("score") or 0) + delta, 3)
            trace = {"rel": rt, "from": evidence_code, "strength": r.get("strength"), "delta": delta, "positive": positive}
            if delta >= 0:
                hy[dx].setdefault("support", []).append(trace)
            else:
                hy[dx].setdefault("against", []).append(trace)
            if positive and rt == "excludes":
                hy[dx]["status"] = "excluded"
                hy[dx]["confidence"] = "excluded"
            elif positive and rt == "refutes":
                hy[dx]["status"] = "excluded"
                hy[dx]["confidence"] = "excluded"
            elif positive and rt == "confirms":
                hy[dx]["status"] = "confirmed"
                hy[dx]["confidence"] = "established"
            else:
                if hy[dx].get("status") not in ("excluded", "confirmed"):
                    hy[dx]["confidence"] = _label_from_score(hy[dx]["score"])
            ebs_mod.add_explanation(
                ebs,
                f"Evidence {evidence_code} ({'present' if positive else 'absent'}) via {rt} → {dx} (Δ {delta:+.2f}).",
                category="update",
                refs=[evidence_code, dx, rt],
            )

    # ----- 4. Question planning (sections) -----

    def plan_questions(self, ebs: dict) -> dict:
        problems = ebs.get("presenting_problems") or []
        if not problems:
            ebs["section_agenda"] = []
            ebs["active_section"] = None
            ebs["suggested_next_action"] = {"kind": "intake", "detail": "Capture presenting problem(s)"}
            return ebs

        # Build agenda from priority_section_for on presenting symptoms
        agenda_map: dict[str, dict] = {}
        for p in problems:
            for r in self.rels(source=p["code"], rel_type="priority_section_for"):
                sec = r["target_code"]
                order = (r.get("context") or {}).get("order", 99)
                if sec not in agenda_map or order < agenda_map[sec]["order"]:
                    ent = self.entity(sec)
                    agenda_map[sec] = {
                        "code": sec,
                        "label": ent["label"] if ent else sec,
                        "order": order,
                        "from_symptom": p["code"],
                    }
        agenda = sorted(agenda_map.values(), key=lambda x: x["order"])
        ebs["section_agenda"] = agenda

        answered = {
            f["code"]
            for f in ebs.get("findings_ledger") or []
            if f.get("kind") in ("history_question", "question") and f.get("polarity") in ("present", "absent", "unknown")
        }

        active = None
        next_qs: list[dict] = []
        for sec in agenda:
            qs = []
            for r in self.rels(source=sec["code"], rel_type="contains_question"):
                qcode = r["target_code"]
                if qcode in answered:
                    continue
                qent = self.entity(qcode)
                if not qent:
                    continue
                # Priority: questions that discriminate among top hypotheses
                priority = 0
                for dr in self.rels(source=qcode, rel_type="discriminates"):
                    if dr["target_code"] in (ebs.get("hypotheses") or {}):
                        priority += 2
                for er in self.rels(source=qcode):
                    if er["rel_type"] in ("supports", "strongly_supports", "argues_against") and er["target_code"] in (
                        ebs.get("hypotheses") or {}
                    ):
                        priority += 1
                qs.append(
                    {
                        "code": qcode,
                        "label": qent["label"],
                        "prompt": (qent.get("body") or {}).get("prompt") or qent["label"],
                        "priority": priority,
                    }
                )
            qs.sort(key=lambda q: (-q["priority"], q["label"]))
            if qs:
                active = sec
                next_qs = qs[:5]
                break

        ebs["active_section"] = active
        if active:
            ebs["section_objective"] = f"Explore {active['label']} to discriminate active hypotheses."
            ebs["suggested_next_action"] = {
                "kind": "ask",
                "section": active["code"],
                "questions": next_qs,
                "detail": f"Next section: {active['label']}",
            }
            ebs_mod.add_explanation(
                ebs,
                f"Question planning selected section {active['code']} with {len(next_qs)} pending question(s).",
                category="planning",
                refs=[active["code"]] + [q["code"] for q in next_qs],
            )
        else:
            ebs["section_objective"] = "History sections complete or no further KG-linked questions."
            ebs["suggested_next_action"] = {
                "kind": "history_complete",
                "detail": "No remaining questions in section agenda — consider examination or investigations.",
                "questions": [],
            }
        return ebs

    # ----- 5. Red flags / pathways -----

    def detect_red_flags(self, ebs: dict) -> dict:
        flags = []
        pathways = set(ebs.get("active_pathways") or [])
        present = {f["code"] for f in ebs.get("findings_ledger") or [] if f.get("polarity") == "present"}
        for code in present:
            for r in self.rels(source=code, rel_type="activates"):
                pw = r["target_code"]
                pent = self.entity(pw)
                if pent and pent["entity_type"] == "pathway":
                    pathways.add(pw)
                    flags.append(
                        {
                            "code": pw,
                            "label": pent["label"],
                            "trigger": code,
                            "urgency": (pent.get("body") or {}).get("urgency", "urgent"),
                        }
                    )
                    ebs_mod.add_explanation(
                        ebs,
                        f"Red flag: {code} activates pathway {pw}.",
                        category="red_flag",
                        refs=[code, pw],
                    )
        # Deduplicate flags by pathway
        uniq = {}
        for f in flags:
            uniq[f["code"]] = f
        ebs["red_flags"] = list(uniq.values())
        ebs["active_pathways"] = sorted(pathways)
        if pathways:
            ebs["suggested_next_action"] = {
                "kind": "pathway",
                "detail": "Emergency/urgent pathway active — prioritize resuscitation and pathway actions.",
                "pathways": sorted(pathways),
                "questions": (ebs.get("suggested_next_action") or {}).get("questions") or [],
            }
        return ebs

    # ----- 6. Examination guidance -----

    def guide_examination(self, ebs: dict) -> dict:
        priorities = []
        seen = set()
        # Signs that support/against top hypotheses
        top = [h["code"] for h in (ebs.get("differential") or [])[:5]] or list((ebs.get("hypotheses") or {}).keys())[:5]
        for dx in top:
            for r in self.rels(target=dx):
                if r["rel_type"] not in ("supports", "strongly_supports", "argues_against", "excludes"):
                    continue
                src = r["source_code"]
                ent = self.entity(src)
                if not ent or ent["entity_type"] != "sign":
                    continue
                if src in seen:
                    continue
                seen.add(src)
                priorities.append(
                    {
                        "code": src,
                        "label": ent["label"],
                        "for_disease": dx,
                        "rel": r["rel_type"],
                        "expected": "positive" if r["rel_type"] in ("supports", "strongly_supports") else "informative_negative",
                    }
                )
        ebs["exam_priorities"] = priorities[:12]
        return ebs

    # ----- 7. Investigation recommendations -----

    def recommend_investigations(self, ebs: dict) -> dict:
        recs = []
        seen = set()
        done = {
            f["code"]
            for f in ebs.get("findings_ledger") or []
            if f.get("kind") == "investigation_result" and f.get("polarity") == "present"
        }
        # Also treat ordered investigations stored as findings kind investigation_order
        ordered = {
            f["code"]
            for f in ebs.get("findings_ledger") or []
            if f.get("kind") in ("investigation_order", "investigation") and f.get("polarity") == "present"
        }
        top = [h["code"] for h in (ebs.get("differential") or [])[:5]] or list((ebs.get("hypotheses") or {}).keys())[:5]
        for dx in top:
            for r in self.rels(source=dx, rel_type="investigated_by"):
                ix = r["target_code"]
                if ix in seen:
                    continue
                ent = self.entity(ix)
                if not ent or ent["entity_type"] != "investigation":
                    continue
                seen.add(ix)
                duplicate = ix in done or ix in ordered
                recs.append(
                    {
                        "code": ix,
                        "label": ent["label"],
                        "for_disease": dx,
                        "duplicate": duplicate,
                        "reason": f"investigated_by link from {dx}",
                    }
                )
        # Pathway-required investigations
        for pw in ebs.get("active_pathways") or []:
            for r in self.rels(source=pw, rel_type="requires"):
                tgt = r["target_code"]
                ent = self.entity(tgt)
                if ent and ent["entity_type"] == "investigation" and tgt not in seen:
                    seen.add(tgt)
                    recs.append(
                        {
                            "code": tgt,
                            "label": ent["label"],
                            "for_disease": pw,
                            "duplicate": tgt in done or tgt in ordered,
                            "reason": f"required by pathway {pw}",
                        }
                    )
        ebs["investigation_recommendations"] = recs
        return ebs

    # ----- 8. Management / follow-up -----

    def recommend_management(self, ebs: dict) -> dict:
        actions = []
        follow = []
        seen = set()
        sources = [h["code"] for h in (ebs.get("differential") or [])[:3]]
        sources += list(ebs.get("active_pathways") or [])
        for src in sources:
            for r in self.rels(source=src, rel_type="managed_by"):
                code = r["target_code"]
                if code in seen:
                    continue
                ent = self.entity(code)
                if not ent:
                    continue
                seen.add(code)
                item = {"code": code, "label": ent["label"], "from": src, "type": ent["entity_type"]}
                if ent["entity_type"] == "follow_up_scheme":
                    follow.append(item)
                elif ent["entity_type"] in ("management_action", "education", "pathway"):
                    actions.append(item)
                else:
                    actions.append(item)
        ebs["management_recommendations"] = actions
        ebs["follow_up_recommendations"] = follow
        return ebs

    # ----- 9. Differential ranking -----

    def rank_differential(self, ebs: dict) -> dict:
        hy = ebs.get("hypotheses") or {}
        rows = []
        for dx, h in hy.items():
            if h.get("status") == "excluded":
                conf = "excluded"
            elif h.get("status") == "confirmed":
                conf = "established"
            else:
                conf = _label_from_score(float(h.get("score") or 0))
                h["confidence"] = conf
            rows.append(
                {
                    "code": dx,
                    "label": h.get("label") or dx,
                    "score": h.get("score") or 0,
                    "confidence": conf,
                    "status": h.get("status") or "active",
                    "support": h.get("support") or [],
                    "against": h.get("against") or [],
                }
            )
        # Sort: confirmed first, then by score desc, excluded last
        def key(r):
            if r["status"] == "excluded":
                return (-1, r["score"])
            if r["status"] == "confirmed":
                return (100, r["score"])
            return (50, r["score"])

        rows.sort(key=key, reverse=True)
        ebs["differential"] = rows
        ebs["working_diagnoses"] = [r for r in rows if r["status"] in ("confirmed", "active") and r["confidence"] in ("established", "very_strong", "strong")][:3]
        return ebs

    # ----- 10. Stopping criteria -----

    def evaluate_stopping(self, ebs: dict) -> dict:
        reasons = []
        status = "continue"
        if ebs.get("active_pathways"):
            status = "escalate"
            reasons.append("Active emergency/urgent pathway(s) from knowledge graph.")
        confirmed = [h for h in (ebs.get("hypotheses") or {}).values() if h.get("status") == "confirmed"]
        strong = [
            h
            for h in (ebs.get("differential") or [])
            if h.get("confidence") in ("established", "very_strong", "strong") and h.get("status") != "excluded"
        ]
        next_qs = ((ebs.get("suggested_next_action") or {}).get("questions")) or []
        if confirmed and not ebs.get("active_pathways"):
            status = "enough_for_plan"
            reasons.append("At least one disease confirmed by knowledge confirms/refutes edges.")
        elif strong and not next_qs and not ebs.get("active_pathways"):
            status = "enough_for_plan"
            reasons.append("Strong leading hypothesis and no remaining section questions.")
        elif not next_qs and (ebs.get("investigation_recommendations") or []):
            status = "need_investigations"
            reasons.append("History agenda exhausted; investigations recommended by graph.")
        else:
            reasons.append("Continue gathering information.")
        ebs["stopping"] = {"status": status, "reasons": reasons}
        if status != "continue" and (ebs.get("suggested_next_action") or {}).get("kind") == "ask":
            # Keep questions if escalate with questions still useful; else update
            if status == "need_investigations":
                ebs["suggested_next_action"] = {
                    "kind": "investigate",
                    "detail": reasons[0],
                    "recommendations": ebs.get("investigation_recommendations") or [],
                }
            elif status == "enough_for_plan":
                ebs["suggested_next_action"] = {
                    "kind": "plan",
                    "detail": reasons[0],
                    "management": ebs.get("management_recommendations") or [],
                }
            elif status == "escalate":
                ebs["suggested_next_action"]["detail"] = reasons[0]
        ebs_mod.add_explanation(ebs, f"Stopping criteria → {status}: {'; '.join(reasons)}", category="stopping")
        return ebs

    def _refresh_missing(self, ebs: dict) -> None:
        missing = []
        # Unanswered high-priority questions in active section
        sna = ebs.get("suggested_next_action") or {}
        for q in sna.get("questions") or []:
            missing.append({"code": q["code"], "label": q.get("prompt") or q.get("label"), "kind": "history_question"})
        # Exam priorities not yet assessed
        assessed = {f["code"] for f in ebs.get("findings_ledger") or [] if f.get("source") == "exam"}
        for p in ebs.get("exam_priorities") or []:
            if p["code"] not in assessed:
                missing.append({"code": p["code"], "label": p["label"], "kind": "sign"})
        ebs["missing_critical"] = missing[:20]

    def build_narrative_draft(self, ebs: dict) -> str:
        parts = []
        probs = ebs.get("presenting_problems") or []
        if probs:
            labels = ", ".join(p["label"] for p in probs)
            parts.append(f"The patient presented with {labels}.")
        findings = [f for f in ebs.get("findings_ledger") or [] if f.get("polarity") == "present" and f.get("kind") == "history_question"]
        if findings:
            bits = []
            for f in findings[:12]:
                ent = self.entity(f["code"])
                bits.append(ent["label"] if ent else f["code"])
            parts.append("Positive history items included: " + "; ".join(bits) + ".")
        neg = [f for f in ebs.get("findings_ledger") or [] if f.get("polarity") == "absent" and f.get("kind") == "history_question"]
        if neg:
            bits = []
            for f in neg[:8]:
                ent = self.entity(f["code"])
                bits.append(ent["label"] if ent else f["code"])
            parts.append("Negated items included: " + "; ".join(bits) + ".")
        diff = ebs.get("differential") or []
        if diff:
            top = ", ".join(f"{d['label']} ({d['confidence']})" for d in diff[:5] if d.get("status") != "excluded")
            if top:
                parts.append("Current differential (knowledge-ranked): " + top + ".")
        if ebs.get("red_flags"):
            parts.append(
                "Active pathway alerts: "
                + ", ".join(f["label"] for f in ebs["red_flags"])
                + "."
            )
        draft = " ".join(parts)
        ebs["narrative_draft"] = draft
        return draft


def load_engine(db: sqlite3.Connection, release_id: int | None = None) -> ClinicalReasoningEngine:
    if release_id is None:
        pub = repo.latest_published_release(db)
        release_id = pub["id"] if pub else None
    graph = repo.graph_for_release(db, release_id)
    return ClinicalReasoningEngine(graph)


def save_session(db: sqlite3.Connection, session_id: int, ebs: dict) -> None:
    db.execute(
        "UPDATE cre_session SET ebs_json=?, updated_at=datetime('now') WHERE id=?",
        (json.dumps(ebs, ensure_ascii=False), session_id),
    )


def create_session(db: sqlite3.Connection, *, release_id: int, patient_label: str = "") -> tuple[int, dict]:
    ebs = ebs_mod.new_ebs(release_id=release_id, release_code=(repo.get_release(db, release_id) or {}).get("code"))
    cur = db.execute(
        "INSERT INTO cre_session (release_id, patient_label, ebs_json) VALUES (?,?,?)",
        (release_id, patient_label, json.dumps(ebs, ensure_ascii=False)),
    )
    return int(cur.lastrowid), ebs


def load_session(db: sqlite3.Connection, session_id: int) -> tuple[dict, dict] | None:
    row = db.execute("SELECT * FROM cre_session WHERE id=?", (session_id,)).fetchone()
    if not row:
        return None
    ebs = json.loads(row["ebs_json"] or "{}")
    return dict(row), ebs
