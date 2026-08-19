"""Load GI clinical report vocabulary seeds from gi_import (reference tree)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

GI_VOCAB: dict[str, list] = {}

_SEED_DIR = (
    Path(__file__).resolve().parents[1]
    / 'gi_import' / 'source' / 'modules' / 'clinical_reports' / 'vocabulary_seeds'
)


def _load_seeds() -> None:
    if GI_VOCAB:
        return
    if not _SEED_DIR.is_dir():
        return
    for pyfile in sorted(_SEED_DIR.glob('*.py')):
        if pyfile.name.startswith('_'):
            continue
        spec = importlib.util.spec_from_file_location(f'gi_vocab_{pyfile.stem}', pyfile)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            continue
        for attr in dir(mod):
            if not attr.endswith('_VOCABULARY_SEED'):
                continue
            seed = getattr(mod, attr, None)
            if isinstance(seed, dict):
                GI_VOCAB.update(seed)


def vocab_labels(source_key: str | None) -> list[str]:
    _load_seeds()
    if not source_key:
        return []
    entries = GI_VOCAB.get(source_key, [])
    labels = []
    for entry in entries:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            labels.append(str(entry[1]))
        elif isinstance(entry, str):
            labels.append(entry)
    return labels
