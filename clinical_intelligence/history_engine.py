"""History Engine — Phase 4 runtime.

Complaint → load template → resolve Q IDs → ask in order → save answers.
Respects optional branching/stop rules from clinical_knowledge/rules/history_branching/.
Dedupes shared question IDs within a template walk.
"""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.conditions import eval_group


PRIORITY_RANK = {"emergency": 0, "high": 1, "routine": 2, "low": 3}


def _answer_map(answers: list[dict] | dict[str, Any]) -> dict[str, Any]:
    if isinstance(answers, dict):
        return {k: (v.get("answer_text") if isinstance(v, dict) else v) for k, v in answers.items()}
    return {a["question_id"]: a.get("answer_text") for a in answers if not a.get("skipped")}


def _as_code_list(complaint_code: str | list[str]) -> list[str]:
    if isinstance(complaint_code, str):
        return [complaint_code]
    # de-duplicate while preserving the order the clinician selected them in
    seen: set[str] = set()
    out = []
    for c in complaint_code:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def build_question_queue(complaint_code: str | list[str]) -> list[dict]:
    """Flatten template sections into ordered unique questions (first occurrence wins).

    Accepts either a single complaint code or a list of complaint codes. When a
    patient has more than one active complaint, questions shared across their
    templates (same dedupe_key, e.g. "Have you had nausea?") are asked only
    once — the item is tagged with every complaint that requested it via
    ``source_complaints`` so the UI can show where it came from.
    """
    codes = _as_code_list(complaint_code)
    library = kl.load_question_library()
    seen_ids: set[str] = set()
    seen_dedupe: dict[str, int] = {}
    queue: list[dict] = []
    for code in codes:
        template = kl.load_history_template(code)
        if not template:
            raise ValueError(f"No history template for {code}")
        red_flags = set(template.get("red_flag_question_ids") or [])
        for section in template.get("sections", []):
            for qid in section.get("question_ids", []):
                dedupe = None
                q = library.get(qid)
                if q:
                    dedupe = q.get("dedupe_key")
                if qid in seen_ids or (dedupe and dedupe in seen_dedupe):
                    # already asked (possibly via a different complaint) —
                    # just record that this complaint also needed it.
                    idx = None
                    if qid in seen_ids:
                        idx = next((i for i, it in enumerate(queue) if it["id"] == qid), None)
                    elif dedupe in seen_dedupe:
                        idx = seen_dedupe[dedupe]
                    if idx is not None and code not in queue[idx]["source_complaints"]:
                        queue[idx]["source_complaints"].append(code)
                    continue
                if not q:
                    continue
                seen_ids.add(qid)
                item = dict(q)
                item["section_key"] = section.get("key")
                item["section_title"] = section.get("title")
                item["is_red_flag"] = qid in red_flags
                item["source_complaints"] = [code]
                queue.append(item)
                if dedupe:
                    seen_dedupe[dedupe] = len(queue) - 1
    return queue


def _skipped_ids(complaint_code: str | list[str], answers: dict[str, Any]) -> set[str]:
    skipped: set[str] = set()
    for code in _as_code_list(complaint_code):
        branching = kl.load_history_branching(code) or {}
        for rule in branching.get("skip_rules") or []:
            if eval_group(rule, answers=answers, exam={}):
                skipped.update(rule.get("skip_question_ids") or [])
    return skipped


def evaluate_stop_rules(complaint_code: str | list[str], answers: dict[str, Any]) -> list[dict]:
    hits = []
    for code in _as_code_list(complaint_code):
        branching = kl.load_history_branching(code) or {}
        for rule in branching.get("stop_rules") or []:
            if eval_group(rule, answers=answers, exam={}):
                hits.append(rule)
    return hits


def next_questions(
    complaint_code: str | list[str],
    answers: list[dict] | dict[str, Any],
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """Return next unanswered questions respecting skip/stop rules.

    ``complaint_code`` may be a single code or a list — pass a list whenever
    the patient has more than one active complaint so shared questions are
    only asked once (see ``build_question_queue``).
    """
    codes = _as_code_list(complaint_code)
    answered = _answer_map(answers)
    answered_ids = {qid for qid, val in answered.items() if val is not None and str(val).strip() != ""}
    queue = build_question_queue(codes)
    skipped = _skipped_ids(codes, answered)
    stop_hits = evaluate_stop_rules(codes, answered)
    skip_low = any(h.get("skip_low_priority_remainder") for h in stop_hits)

    pending: list[dict] = []
    for q in queue:
        qid = q["id"]
        if qid in answered_ids or qid in skipped:
            continue
        if skip_low and not q.get("is_red_flag") and PRIORITY_RANK.get(q.get("priority_default", "routine"), 2) >= 2:
            continue
        pending.append(q)

    total = len(queue)
    done = sum(1 for q in queue if q["id"] in answered_ids or q["id"] in skipped)
    # Gamified numbering: "Question 4 of 22" — stable position in the merged queue.
    order_index = {q["id"]: i for i, q in enumerate(queue)}
    for q in pending:
        q["question_number"] = order_index[q["id"]] + 1
        q["question_total"] = total

    return {
        "complaint_codes": codes,
        "next": pending[:limit],
        "pending_count": len(pending),
        "answered_count": len(answered_ids),
        "skipped_count": len(skipped & {q["id"] for q in queue}),
        "total_unique_questions": total,
        "progress_pct": int(100 * done / total) if total else 100,
        "complete": len(pending) == 0,
        "stop_rules": [
            {"id": h.get("id"), "action": h.get("action"), "message": h.get("message")}
            for h in stop_hits
        ],
        "templates": [kl.load_history_template(c) for c in codes],
        # Side-panel checklist: every remaining question, in order, with its
        # number — "what's left to ask" independent of the one-at-a-time flow.
        "checklist": [
            {
                "id": q["id"],
                "number": order_index[q["id"]] + 1,
                "prompt": q.get("prompt"),
                "section_title": q.get("section_title"),
                "is_red_flag": q.get("is_red_flag", False),
                "answered": q["id"] in answered_ids,
            }
            for q in queue
            if q["id"] not in skipped
        ],
    }


def history_summary(complaint_code: str, answers: list[dict]) -> list[dict]:
    library = kl.load_question_library()
    rows = []
    for a in answers:
        if a.get("skipped"):
            continue
        q = library.get(a["question_id"], {})
        rows.append(
            {
                "question_id": a["question_id"],
                "prompt": q.get("prompt", a["question_id"]),
                "answer_text": a.get("answer_text"),
                "section_key": a.get("section_key"),
                "is_red_flag": a["question_id"] in set(
                    (kl.load_history_template(complaint_code) or {}).get("red_flag_question_ids") or []
                ),
            }
        )
    return rows


def board_state(
    complaint_code: str | list[str],
    answers: list[dict] | dict[str, Any],
    *,
    focus_qid: str | None = None,
) -> dict[str, Any]:
    """Interactive flow-board payload: sections → nodes with status + focus.

    ``complaint_code`` may be a list when the patient has multiple active
    complaints; shared questions are asked once (see ``build_question_queue``)
    and each node carries ``source_complaints`` so the UI can badge which
    complaint(s) a shared question belongs to.
    """
    codes = _as_code_list(complaint_code)
    answered = _answer_map(answers)
    answered_ids = {qid for qid, val in answered.items() if val is not None and str(val).strip() != ""}
    queue = build_question_queue(codes)
    skipped = _skipped_ids(codes, answered)
    stop_hits = evaluate_stop_rules(codes, answered)
    skip_low = any(h.get("skip_low_priority_remainder") for h in stop_hits)
    red_flags: set[str] = set()

    # Preserve section order across all selected complaints; attach nodes
    section_map: dict[str, dict] = {}
    for code in codes:
        template = kl.load_history_template(code) or {}
        red_flags |= set(template.get("red_flag_question_ids") or [])
        for section in template.get("sections") or []:
            key = section.get("key") or "other"
            if key not in section_map:
                section_map[key] = {
                    "key": key,
                    "title": section.get("title") or key,
                    "nodes": [],
                }

    total = len(queue)
    pending_order: list[str] = []
    for i, q in enumerate(queue):
        qid = q["id"]
        status = "pending"
        if qid in answered_ids:
            status = "answered"
        elif qid in skipped:
            status = "skipped"
        elif skip_low and not q.get("is_red_flag") and PRIORITY_RANK.get(q.get("priority_default", "routine"), 2) >= 2:
            status = "deferred"
        else:
            pending_order.append(qid)

        sk = q.get("section_key") or "other"
        if sk not in section_map:
            section_map[sk] = {"key": sk, "title": q.get("section_title") or sk, "nodes": []}

        node = {
            "id": qid,
            "prompt": q.get("prompt"),
            "answer_type": q.get("answer_type") or "text",
            "choices": q.get("choices") or [],
            "section_key": sk,
            "section_title": q.get("section_title"),
            "priority": q.get("priority_default") or "routine",
            "is_red_flag": qid in red_flags or bool(q.get("is_red_flag")),
            "status": status,
            "answer_text": answered.get(qid) if qid in answered_ids else None,
            "bates_domain": q.get("bates_domain"),
            "source_complaints": q.get("source_complaints") or codes,
            "question_number": i + 1,
            "question_total": total,
        }
        section_map[sk]["nodes"].append(node)

    if focus_qid and focus_qid in {n["id"] for s in section_map.values() for n in s["nodes"]}:
        focus = focus_qid
    elif pending_order:
        focus = pending_order[0]
    elif answered_ids:
        focus = queue[-1]["id"] if queue else None
    else:
        focus = None

    done = sum(1 for q in queue if q["id"] in answered_ids or q["id"] in skipped)
    sections = list(section_map.values())

    # Stage statuses for flowchart stepper
    stages = []
    for sec in sections:
        nodes = sec["nodes"]
        n_tot = len(nodes)
        n_done = sum(1 for n in nodes if n["status"] in ("answered", "skipped", "deferred"))
        n_pending = sum(1 for n in nodes if n["status"] == "pending")
        if n_tot == 0:
            st = "todo"
        elif n_pending == 0:
            st = "done"
        elif any(n["id"] == focus for n in nodes):
            st = "active"
        elif n_done > 0:
            st = "active"
        else:
            st = "todo"
        stages.append(
            {
                "key": sec["key"],
                "title": sec["title"],
                "status": st,
                "done": n_done,
                "total": n_tot,
            }
        )

    # Answered trail (short) for path visualization
    trail = []
    for q in queue:
        qid = q["id"]
        if qid not in answered_ids:
            continue
        prompt = q.get("prompt") or qid
        trail.append(
            {
                "id": qid,
                "prompt_short": (prompt[:36] + "…") if len(prompt) > 38 else prompt,
                "answer": answered.get(qid),
                "is_red_flag": qid in red_flags,
            }
        )

    focus_node = None
    for sec in sections:
        for n in sec["nodes"]:
            if n["id"] == focus:
                focus_node = n
                break
        if focus_node:
            break

    # Merge education answer_triggers from every active complaint's pack —
    # a shared question (e.g. nausea) should still surface a teaching hint
    # whichever complaint originally asked it.
    merged_triggers: list[dict] = []
    for code in (focus_node.get("source_complaints") if focus_node else None) or codes:
        edu = kl.load_education_rules(code) or {}
        merged_triggers.extend(edu.get("answer_triggers") or [])
    edu = {"answer_triggers": merged_triggers}
    branch_opts = []
    if focus_node:
        atype = focus_node.get("answer_type") or "text"
        raw_choices = []
        if atype == "boolean":
            raw_choices = ["yes", "no"]
        elif atype == "scale":
            # Compact 0–10 UI in template — not 11 flowchart arms
            raw_choices = []
        elif focus_node.get("choices"):
            raw_choices = list(focus_node["choices"])

        triggers = [
            t
            for t in (edu.get("answer_triggers") or [])
            if t.get("question_id") == focus_node["id"]
        ]

        def _hint_for(choice: str) -> dict | None:
            cl = str(choice).strip().lower()
            for t in triggers:
                exact = [str(x).strip().lower() for x in (t.get("answer_in") or [])]
                contains = [str(x).strip().lower() for x in (t.get("answer_contains_any") or [])]
                if exact and cl in exact:
                    return {"title": t.get("title"), "points": (t.get("points") or [])[:2]}
                if contains and any(c in cl for c in contains if c):
                    return {"title": t.get("title"), "points": (t.get("points") or [])[:2]}
            return None

        for ch in raw_choices:
            hint = _hint_for(ch)
            branch_opts.append(
                {
                    "value": ch,
                    "label": ch,
                    "selected": str(focus_node.get("answer_text") or "").strip().lower()
                    == str(ch).strip().lower(),
                    "opens_branch": bool(hint),
                    "hint_title": (hint or {}).get("title"),
                    "hint_points": (hint or {}).get("points") or [],
                }
            )

    next_preview = None
    if pending_order:
        nxt_id = pending_order[0] if focus != pending_order[0] else (
            pending_order[1] if len(pending_order) > 1 else None
        )
        if focus and focus in pending_order:
            idx = pending_order.index(focus)
            nxt_id = pending_order[idx + 1] if idx + 1 < len(pending_order) else None
        if nxt_id:
            for q in queue:
                if q["id"] == nxt_id:
                    np = q.get("prompt") or nxt_id
                    next_preview = {
                        "id": nxt_id,
                        "prompt_short": (np[:40] + "…") if len(np) > 42 else np,
                    }
                    break

    # Side-panel checklist: every question the clinician still needs to ask,
    # numbered, independent of which single question is currently "in focus".
    # Lets a clinician glance at "what's left" and ask the patient everything
    # before coming back to fill in the form.
    id_to_number = {q["id"]: i + 1 for i, q in enumerate(queue)}
    checklist = [
        {
            "id": qid,
            "number": id_to_number[qid],
            "prompt": next((q.get("prompt") for q in queue if q["id"] == qid), qid),
            "is_red_flag": qid in red_flags,
        }
        for qid in pending_order
    ]

    return {
        "complaint_codes": codes,
        "sections": sections,
        "focus_qid": focus,
        "focus_question_number": id_to_number.get(focus) if focus else None,
        "pending_order": pending_order,
        "checklist": checklist,
        "answered_count": len(answered_ids),
        "pending_count": len(pending_order),
        "skipped_count": len(skipped & {q["id"] for q in queue}),
        "total_unique_questions": total,
        "progress_pct": int(100 * done / total) if total else 100,
        "complete": len(pending_order) == 0,
        "stop_rules": [
            {"id": h.get("id"), "action": h.get("action"), "message": h.get("message")}
            for h in stop_hits
        ],
        "flow": {
            "stages": stages,
            "trail": trail[-8:],
            "decision": {
                "node": focus_node,
                "branches": branch_opts,
            },
            "next_preview": next_preview,
        },
    }
