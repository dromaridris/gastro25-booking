"""Load GI clinical catalogue Python bundles without Flask/SQLAlchemy."""

from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path

from gi_platform.catalogue import bundle_common

_GI_CH = Path(__file__).resolve().parent.parent / 'gi_import' / 'source' / 'modules' / 'clinical_history'
_GI_RS = Path(__file__).resolve().parent.parent / 'gi_import' / 'source' / 'modules' / 'research'

_IMPORT_RE = re.compile(
    r'^from app\.modules\.clinical_history\.catalogue_bundle_common import .+$',
    re.MULTILINE,
)


def _exec_catalogue_file(filename: str) -> dict:
    path = _GI_CH / filename
    source = path.read_text(encoding='utf-8')
    source = _IMPORT_RE.sub(
        'from gi_platform.catalogue.bundle_common import common_context_rules, targets',
        source,
    )
    source = source.replace(
        'from app.modules.clinical_history.catalogue_bundle_common import common_context_rules, targets',
        'from gi_platform.catalogue.bundle_common import common_context_rules, targets',
    )
    ns: dict = {'__builtins__': __builtins__, 'json': __import__('json')}
    ns.update(vars(bundle_common))
    exec(compile(source, str(path), 'exec'), ns)  # noqa: S102 — trusted local catalogue seed
    return ns


def load_all_intelligence_bundles() -> list[dict]:
    bleeding = _exec_catalogue_file('catalogue_bundles_bleeding.py')
    luminal = _exec_catalogue_file('catalogue_bundles_luminal.py')
    hepato = _exec_catalogue_file('catalogue_bundles_hepatobiliary.py')
    diarrhea = _exec_catalogue_file('catalogue_diarrhea_intelligence.py')
    bundles = []
    for ns in (diarrhea, bleeding, luminal, hepato):
        if 'DIARRHEA_BUNDLE' in ns:
            bundles.append(ns['DIARRHEA_BUNDLE'])
        if 'BLEEDING_BUNDLES' in ns:
            bundles.extend(ns['BLEEDING_BUNDLES'])
        if 'LUMINAL_BUNDLES' in ns:
            bundles.extend(ns['LUMINAL_BUNDLES'])
        if 'HEPATOBILIARY_BUNDLES' in ns:
            bundles.extend(ns['HEPATOBILIARY_BUNDLES'])
    return bundles


def load_seed_constants() -> dict:
    path = _GI_CH / 'catalogue_seed.py'
    source = path.read_text(encoding='utf-8')
    start = source.find('CHIEF_COMPLAINTS')
    if start < 0:
        raise RuntimeError('CHIEF_COMPLAINTS not found in catalogue_seed.py')
    chunk = source[start:]
    end = chunk.find('\ndef ')
    if end > 0:
        chunk = chunk[:end]
    ns: dict = {'__builtins__': __builtins__}
    ns.update(vars(bundle_common))
    ns['ALL_INTELLIGENCE_BUNDLES'] = load_all_intelligence_bundles()
    ns['ANSWER_TYPE_BOOLEAN'] = 'boolean'
    ns['ANSWER_TYPE_CHOICE'] = 'choice'
    ns['ANSWER_TYPE_TEXT'] = 'text'
    exec(compile(chunk, str(path), 'exec'), ns)  # noqa: S102
    return ns


def load_research_seed() -> dict:
    path = _GI_RS / 'catalogue_seed.py'
    source = path.read_text(encoding='utf-8')
    start = source.find('REGISTRIES')
    chunk = source[start:]
    end = chunk.find('\ndef ')
    if end > 0:
        chunk = chunk[:end]
    ns: dict = {'__builtins__': __builtins__, 'json': __import__('json')}
    exec(compile(chunk, str(path), 'exec'), ns)  # noqa: S102
    return ns
