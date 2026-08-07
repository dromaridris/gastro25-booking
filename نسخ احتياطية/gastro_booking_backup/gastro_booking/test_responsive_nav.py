"""Regression checks for responsive navigation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
css = (ROOT / 'static/css/style.css').read_text(encoding='utf-8')
js = (ROOT / 'static/js/responsive_nav.js').read_text(encoding='utf-8')
base = (ROOT / 'templates/base.html').read_text(encoding='utf-8')

# Desktop hover/focus must exist
assert '.nav-dropdown:hover > .nav-dropdown-menu' in css
assert '.nav-dropdown:focus-within > .nav-dropdown-menu' in css
assert '@media (min-width: 761px)' in css

# Overflow must not clip desktop dropdowns
desktop_block_start = css.index('@media (min-width: 761px)')
desktop_block = css[desktop_block_start:desktop_block_start + 600]
assert '.topbar{ overflow: visible; }' in desktop_block
assert '.mainnav{ overflow: visible; }' in desktop_block

# Mobile overflow clip stays scoped to mobile
mobile_block_start = css.index('@media (max-width: 760px)')
mobile_block = css[mobile_block_start:mobile_block_start + 400]
assert 'overflow-x: clip' in mobile_block

# JS extracted from template; single init path
assert 'responsive_nav.js' in base
assert 'navToggleBtn' in base
assert 'function closeAllDropdowns' not in base
assert 'initResponsiveNav' in js
assert 'MOBILE_MQ' in js
assert js.count('addEventListener(\'click\'') >= 3

# No duplicate desktop/mobile document click that closes mobile nav on desktop
assert 'if (isMobile())' in js
assert 'closeMobileNav' in js

print('Navigation regression checks passed')
