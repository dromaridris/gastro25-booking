"""Load structured report configs from gi_import JSON schemas."""

from __future__ import annotations

import json
from pathlib import Path

from advanced_reports.gi_vocabulary import vocab_labels

_SCHEMA_DIR = (
    Path(__file__).resolve().parents[1]
    / 'gi_import' / 'source' / 'modules' / 'clinical_reports' / 'schemas'
)

_TYPE_MAP = {
    'multi_select': 'multi_checkbox',
    'long_text': 'long_text',
    'dropdown': 'dropdown',
    'yes_no': 'yes_no',
    'text': 'text',
    'number': 'text',
    'date': 'text',
    'repeatable_group': None,
}


def _field_key(field_id: str) -> str:
    return (field_id or '').split('.')[-1]


def _convert_field(raw: dict) -> dict | None:
    ftype = _TYPE_MAP.get(raw.get('type', 'text'))
    if ftype is None:
        return None
    field = {
        'key': _field_key(raw.get('id', '')),
        'label': raw.get('label') or _field_key(raw.get('id', '')),
        'type': ftype,
    }
    src = raw.get('vocabulary_source')
    if src:
        opts = vocab_labels(src)
        if opts:
            field['options'] = opts
    return field


def load_schema_sections(schema_filename: str) -> list[dict]:
    path = _SCHEMA_DIR / schema_filename
    if not path.is_file():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    sections = []
    for sec in data.get('sections', []):
        fields = []
        for raw in sec.get('fields', []):
            converted = _convert_field(raw)
            if converted:
                fields.append(converted)
        if fields:
            sections.append({
                'id': sec.get('id', 'section'),
                'title': sec.get('label') or sec.get('id', 'Section'),
                'fields': fields,
            })
    return sections


def load_schema_meta(schema_filename: str) -> dict:
    path = _SCHEMA_DIR / schema_filename
    data = json.loads(path.read_text(encoding='utf-8'))
    return {
        'label': data.get('label') or schema_filename.replace('.json', ''),
        'template_key': data.get('template_key', ''),
    }
