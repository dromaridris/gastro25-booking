"""Print layout generalization — all advanced reports except EUS."""

from advanced_reports.clinical_note_policy import is_structured_endoscopy, resolve_print_layout
from advanced_reports.configs import PROCEDURE_REGISTRY, get_config
from advanced_reports.print_metadata import build_unified_print_rows

legacy = {'eus'}
for key in PROCEDURE_REGISTRY:
    cfg = get_config(key)
    if key in legacy:
        assert not is_structured_endoscopy(key, cfg), key
        assert resolve_print_layout(key, cfg, 2) == 'default', key
    else:
        assert is_structured_endoscopy(key, cfg), key
        assert resolve_print_layout(key, cfg, 2) == 'sidebar_images', key
        assert resolve_print_layout(key, cfg, 6) == 'default', key

class _Row:
    def __init__(self, payload):
        self._data = {
            'payload_json': __import__('json').dumps(payload),
            'technician': 'Tech A',
            'assistants': '',
            'sedation': 'Midazolam',
        }

    def __getitem__(self, k):
        return self._data[k]

class _Appt:
    patient_name = 'Test Patient'
    mrn = 'MR1'
    age = 40
    gender = 'M'
    appointment_date = '2026-01-01'
    referral = 'Ward 25'

sig_cfg = get_config('sigmoidoscopy')
rows = build_unified_print_rows(
    'sigmoidoscopy',
    _Row({'urgency': 'Routine', 'indication_category': ['Screening']}),
    _Appt(),
    sig_cfg,
)
assert any(r[0] == 'Patient Name' for r in rows)
assert any(r[0] == 'Urgency' for r in rows)
assert not any(r[0] == 'Impression' for r in rows)

print('Print layout generalization tests passed')
