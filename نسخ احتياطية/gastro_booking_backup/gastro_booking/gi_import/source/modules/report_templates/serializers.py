"""Serialize structured template findings to plain text stored in ReportSection."""

import re

from app.modules.report_templates.definitions import (
    FINDINGS_MARKER_COLONOSCOPY,
    FINDINGS_MARKER_END,
    FINDINGS_MARKER_UPPER_GI,
    TEMPLATE_COLONOSCOPY,
    TEMPLATE_UPPER_GI,
)


def _clean(value):
    return (value or "").strip()


def format_colonoscopy_findings(data: dict) -> str:
    lines = [
        FINDINGS_MARKER_COLONOSCOPY,
        f"Caecum reached: {_clean(data.get('caecum_reached')) or '—'}",
        f"Terminal ileum intubated: {_clean(data.get('ileum_intubated')) or '—'}",
        (
            "BBPS: "
            f"Right {_clean(data.get('bbps_right')) or '—'} / "
            f"Transverse {_clean(data.get('bbps_transverse')) or '—'} / "
            f"Left {_clean(data.get('bbps_left')) or '—'}"
        ),
        f"Withdrawal time (minutes): {_clean(data.get('withdrawal_time_minutes')) or '—'}",
        "",
        "Polyp findings:",
        _clean(data.get("polyp_findings")) or "—",
        "",
        "Mucosal findings:",
        _clean(data.get("mucosal_findings")) or "—",
        "",
        "Other findings:",
        _clean(data.get("other_findings")) or "—",
        FINDINGS_MARKER_END,
    ]
    return "\n".join(lines)


def parse_colonoscopy_findings(content: str) -> dict:
    text = content or ""
    if FINDINGS_MARKER_COLONOSCOPY not in text:
        return _empty_colonoscopy_findings()

    block = text.split(FINDINGS_MARKER_COLONOSCOPY, 1)[1]
    if FINDINGS_MARKER_END in block:
        block = block.split(FINDINGS_MARKER_END, 1)[0]

    data = _empty_colonoscopy_findings()
    data["caecum_reached"] = _extract_line_value(block, "Caecum reached:")
    data["ileum_intubated"] = _extract_line_value(block, "Terminal ileum intubated:")
    bbps = _extract_line_value(block, "BBPS:")
    if bbps:
        match = re.search(
            r"Right\s+(\S+)\s*/\s*Transverse\s+(\S+)\s*/\s*Left\s+(\S+)",
            bbps,
        )
        if match:
            data["bbps_right"] = match.group(1)
            data["bbps_transverse"] = match.group(2)
            data["bbps_left"] = match.group(3)
    data["withdrawal_time_minutes"] = _extract_line_value(block, "Withdrawal time (minutes):")
    data["polyp_findings"] = _extract_section(
        block, "Polyp findings:", stop_labels=("Mucosal findings:", "Other findings:")
    )
    data["mucosal_findings"] = _extract_section(
        block, "Mucosal findings:", stop_labels=("Other findings:",)
    )
    data["other_findings"] = _extract_section(block, "Other findings:", stop_labels=())
    return data


def format_upper_gi_findings(data: dict) -> str:
    lines = [
        FINDINGS_MARKER_UPPER_GI,
        "Oesophagus:",
        _clean(data.get("oesophagus_findings")) or "—",
        "",
        "Stomach:",
        _clean(data.get("stomach_findings")) or "—",
        "",
        "Duodenum:",
        _clean(data.get("duodenum_findings")) or "—",
        "",
        f"D2 reached: {_clean(data.get('d2_reached')) or '—'}",
        "",
        "Other findings:",
        _clean(data.get("other_findings")) or "—",
        FINDINGS_MARKER_END,
    ]
    return "\n".join(lines)


def parse_upper_gi_findings(content: str) -> dict:
    text = content or ""
    if FINDINGS_MARKER_UPPER_GI not in text:
        return _empty_upper_gi_findings()

    block = text.split(FINDINGS_MARKER_UPPER_GI, 1)[1]
    if FINDINGS_MARKER_END in block:
        block = block.split(FINDINGS_MARKER_END, 1)[0]

    data = _empty_upper_gi_findings()
    data["oesophagus_findings"] = _extract_section(
        block, "Oesophagus:", stop_labels=("Stomach:", "Duodenum:", "D2 reached:", "Other findings:")
    )
    data["stomach_findings"] = _extract_section(
        block, "Stomach:", stop_labels=("Duodenum:", "D2 reached:", "Other findings:")
    )
    data["duodenum_findings"] = _extract_section(
        block, "Duodenum:", stop_labels=("D2 reached:", "Other findings:")
    )
    data["d2_reached"] = _extract_line_value(block, "D2 reached:")
    data["other_findings"] = _extract_section(block, "Other findings:", stop_labels=())
    return data


def format_findings(template_key: str, data: dict) -> str:
    if template_key == TEMPLATE_COLONOSCOPY:
        return format_colonoscopy_findings(data)
    if template_key == TEMPLATE_UPPER_GI:
        return format_upper_gi_findings(data)
    raise ValueError(f"Unsupported template key: {template_key}")


def parse_findings(template_key: str, content: str) -> dict:
    if template_key == TEMPLATE_COLONOSCOPY:
        return parse_colonoscopy_findings(content)
    if template_key == TEMPLATE_UPPER_GI:
        return parse_upper_gi_findings(content)
    raise ValueError(f"Unsupported template key: {template_key}")


def _empty_colonoscopy_findings():
    return {
        "caecum_reached": "",
        "ileum_intubated": "",
        "bbps_right": "",
        "bbps_transverse": "",
        "bbps_left": "",
        "withdrawal_time_minutes": "",
        "polyp_findings": "",
        "mucosal_findings": "",
        "other_findings": "",
    }


def _empty_upper_gi_findings():
    return {
        "oesophagus_findings": "",
        "stomach_findings": "",
        "duodenum_findings": "",
        "d2_reached": "",
        "other_findings": "",
    }


def _extract_line_value(block: str, label: str) -> str:
    for line in block.splitlines():
        if line.strip().startswith(label):
            return line.split(label, 1)[1].strip()
    return ""


def _extract_section(block: str, label: str, stop_labels=()) -> str:
    if label not in block:
        return ""
    after = block.split(label, 1)[1]
    lines = []
    for line in after.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(stop) for stop in stop_labels):
            break
        if not stripped and not lines:
            continue
        lines.append(line.rstrip())
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()
