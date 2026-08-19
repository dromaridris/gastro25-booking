"""Freeze writes to legacy History AI Training / History Templates.

Canonical Bates history lives in Clinical Intelligence + clinical_knowledge/.
Legacy admin surfaces remain readable; creates/edits/deletes are blocked unless
explicitly overridden via GASTRO_ALLOW_LEGACY_HISTORY_WRITES=1|true|yes.
"""

from __future__ import annotations

import os

OVERRIDE_ENV = 'GASTRO_ALLOW_LEGACY_HISTORY_WRITES'

FREEZE_MESSAGE = (
    'Legacy history writes are frozen. Canonical Bates templates live in '
    'Clinical Intelligence / clinical_knowledge/. '
    f'Set {OVERRIDE_ENV}=1 only for emergency legacy edits.'
)


def legacy_history_writes_allowed() -> bool:
    return (os.environ.get(OVERRIDE_ENV) or '').strip().lower() in ('1', 'true', 'yes')


def legacy_history_writes_frozen() -> bool:
    return not legacy_history_writes_allowed()
