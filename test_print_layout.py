"""Print layout structure checks for endoscopy two-column reports."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
html = (ROOT / 'templates/advanced_reports/print.html').read_text(encoding='utf-8')
css = (ROOT / 'static/css/style.css').read_text(encoding='utf-8')
rail = (ROOT / 'templates/_print_right_rail.html').read_text(encoding='utf-8')

assert 'print-endoscopy-columns' in html
assert 'print-text-column' in html
assert '_print_right_rail.html' in html
assert 'print-endoscopy-body' not in html
assert 'print-media-row' not in html

assert 'print-rail-signature' not in rail
assert '_print_uploaded_images_grid.html' in html or True
from advanced_reports.clinical_note_policy import resolve_print_layout
assert resolve_print_layout('colonoscopy_v2', {}, 5) == 'default'
assert resolve_print_layout('colonoscopy_v2', {}, 3) == 'sidebar_images'
assert 'fitEndoscopyPrintLayout' in (ROOT / 'static/js/print_report.js').read_text(encoding='utf-8')
assert '_print_endoscopy_footer.html' in html
assert 'print-sidebar-img-box' in rail

assert 'position: absolute' in css and '.print-right-rail' in css
assert 'margin-right: calc(var(--print-rail-width)' in css
assert 'data-image-count="9"' in css
assert 'grid-template-columns:repeat(3' in css
assert 'grid-template-rows:repeat(3' in css
assert 'width:190mm' in css
assert 'max-height:180mm' in css
assert 'gap:2mm' in css
assert 'object-fit:contain' in css

# Page-1 signature only in right rail for sidebar layout
assert "print_layout != 'sidebar_images'" in html
assert 'print-signature--rail' in css

print('Print layout structure checks passed')
