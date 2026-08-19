"""Regression checks for the universal A4 print-layout contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
css = (ROOT / 'static/css/style.css').read_text(encoding='utf-8')
js = (ROOT / 'static/js/print_report.js').read_text(encoding='utf-8')
ercp_print = (ROOT / 'templates/ercp_print.html').read_text(encoding='utf-8')
ercp_editor = (ROOT / 'templates/ercp_report.html').read_text(encoding='utf-8')
app = (ROOT / 'app.py').read_text(encoding='utf-8')

assert 'margin: 0;' in css
assert 'min-height:63mm' in css
assert 'height:50mm' in css
assert 'width:190mm' in css
assert 'max-height:180mm' in css
assert 'gap:2mm' in css
assert 'data-image-count="9"' in css
assert 'data-image-count="9"' not in ercp_print
assert 'data-image-count' in js
assert 'grid-template-columns:repeat(3' in css
assert 'grid-template-rows:repeat(3' in css
assert 'min-height:5mm' in css
assert 'border:0.25mm solid #000' in css
assert 'object-fit:contain' in css
assert 'flex-direction:column' in css
assert 'letterhead-mode' in js
assert 'print-without-header' not in js
assert 'printWithoutHeader()' in (ROOT / 'templates/_print_toolbar.html').read_text(encoding='utf-8')
assert 'img-caption-input' in ercp_editor
assert 'image_captions' in (ROOT / 'static/js/app.js').read_text(encoding='utf-8')
assert 'ERCP_IMAGE_SLOTS = 9' in app
assert 'DILATATION_IMAGE_SLOTS = 9' in app
assert 'caption TEXT NOT NULL DEFAULT' in app
assert 'ALTER TABLE ercp_report_image ADD COLUMN caption' in app
assert 'ercp-print-image-caption' in ercp_print
assert 'ercp-print-image-box' in ercp_print
print('Universal print-layout contract checks passed')
