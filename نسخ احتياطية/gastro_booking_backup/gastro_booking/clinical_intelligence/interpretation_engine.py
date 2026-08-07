"""Investigation interpretation — flags/differentials/next steps from JSON rules.

Clinician supplies categorical result labels from the pack vocab; engine never invents lab numbers.
"""

from __future__ import annotations

from typing import Any

from clinical_intelligence import knowledge_loader as kl


def result_vocab(complaint_code: str) -> dict[str, list[str]]:
    pack = kl.load_interpretation_rules(complaint_code) or {}
    return dict(pack.get("result_vocab") or {})


def interpret_results(
    complaint_code: str,
    results: list[dict] | dict[str, str],
) -> dict[str, Any]:
    """
    results: list of {investigation_code, result} or map code->result
    result must be a vocab label (e.g. leukocytosis), not a free numeric invention by the engine.
    """
    pack = kl.load_interpretation_rules(complaint_code)
    if not pack:
        return {"available": False, "entries": [], "message": "No interpretation pack for complaint."}

    if isinstance(results, dict):
        result_list = [{"investigation_code": k, "result": v} for k, v in results.items()]
    else:
        result_list = list(results)

    vocab = pack.get("result_vocab") or {}
    interpretations = pack.get("interpretations") or []
    entries = []
    flags = []

    for row in result_list:
        code = row.get("investigation_code") or row.get("code")
        result = (row.get("result") or "").strip()
        if not code or not result:
            continue
        allowed = vocab.get(code)
        if allowed and result not in allowed:
            entries.append(
                {
                    "investigation_code": code,
                    "result": result,
                    "ok": False,
                    "error": f"Result '{result}' not in vocab for {code}",
                    "allowed": allowed,
                }
            )
            continue

        matched = []
        for rule in interpretations:
            if rule.get("investigation_code") != code:
                continue
            when = rule.get("when_result")
            when_list = when if isinstance(when, list) else [when]
            if result in when_list:
                matched.append(
                    {
                        "id": rule.get("id"),
                        "flag": rule.get("flag"),
                        "message": rule.get("message"),
                        "differential_hints": rule.get("differential_hints") or [],
                        "next_steps": rule.get("next_steps") or [],
                    }
                )
                if rule.get("flag"):
                    flags.append(rule["flag"])

        meta = kl.load_investigation_index().get(code, {})
        entries.append(
            {
                "investigation_code": code,
                "label": meta.get("label", code),
                "result": result,
                "ok": True,
                "interpretations": matched,
            }
        )

    return {
        "available": True,
        "entries": entries,
        "flags": sorted(set(flags)),
        "disclaimer": "Interpretations are rule-pack flags from categorical results — not automated lab analyzers.",
    }
