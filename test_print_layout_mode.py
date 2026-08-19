"""Print layout mode resolution (≤4 vs ≥5 images)."""

from advanced_reports.clinical_note_policy import resolve_print_layout, is_structured_endoscopy
from advanced_reports.configs import get_config

assert is_structured_endoscopy('colonoscopy_v2', get_config('colonoscopy_v2'))
assert is_structured_endoscopy('sigmoidoscopy', get_config('sigmoidoscopy'))
assert is_structured_endoscopy('emr', get_config('emr'))
assert is_structured_endoscopy('capsule', get_config('capsule'))
assert not is_structured_endoscopy('eus', get_config('eus'))

assert resolve_print_layout('colonoscopy_v2', get_config('colonoscopy_v2'), 0) == 'sidebar_images'
assert resolve_print_layout('colonoscopy_v2', get_config('colonoscopy_v2'), 4) == 'sidebar_images'
assert resolve_print_layout('colonoscopy_v2', get_config('colonoscopy_v2'), 5) == 'default'
assert resolve_print_layout('sigmoidoscopy', get_config('sigmoidoscopy'), 3) == 'sidebar_images'
assert resolve_print_layout('sigmoidoscopy', get_config('sigmoidoscopy'), 5) == 'default'
assert resolve_print_layout('eus', get_config('eus'), 10) == 'default'
print('Print layout mode tests passed')
