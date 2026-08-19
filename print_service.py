"""
Gastro25 Core Services — Print Service
-----------------------------------------
Generic helpers for assembling procedure-report print pages.

This app renders print pages as server-side HTML/Jinja templates (there
is no separate PDF-generation layer), so the reusable "Print Service" is
split across two things, both introduced in this phase and both usable
by any future procedure report:

1. This module — small, generic Python helpers for print-page context
   assembly (e.g. splitting a comma-separated staff roster string).

2. Shared Jinja partials in templates/, each covering exactly one of the
   requested building blocks and parameterized so any procedure can reuse
   them as-is:
       templates/_print_header.html         (report header + hospital logos)
       templates/_print_team_block.html     (anesthesiologist / assistants / technician)
       templates/_print_signature_block.html (endoscopist-or-any-staff signature)
       templates/_print_qr_block.html       (QR positioning)
       templates/_print_image_grid.html     (fixed-slot image layout)

Print CSS itself was already centralized before this phase — every print
page (print_list.html and ercp_print.html) already shares the same
classes in static/css/style.css (.print-header, .print-logo,
.print-signature, .signature-line, .ercp-print-table, etc.), so no new
stylesheet work was needed here; this phase only removed the duplicated
*markup* that repeated those classes, not the CSS itself.

ERCP-specific report *content* (procedure note, papilla, cannulation,
cholangiogram, stents, research, ...) is NOT handled here and stays in
the ERCP module, same as before.
"""


def split_team_names(csv_text):
    """'Nurse Sana, Nurse Bilal' -> ['Nurse Sana', 'Nurse Bilal'].
    Generic comma-separated staff roster parsing — usable for any
    procedure's assistant/team field, not just ERCP's. Identical
    behaviour to the inline list-comprehension it replaces."""
    return [name.strip() for name in (csv_text or '').split(',') if name.strip()]
