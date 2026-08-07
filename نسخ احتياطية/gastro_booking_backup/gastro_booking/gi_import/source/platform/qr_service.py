"""QR code generation for entity deep links."""

from __future__ import annotations

import io

from flask import url_for

ENTITY_ROUTES = {
    "patient": ("patients.view_patient", "patient_id"),
    "appointment": ("appointments.view_appointment", "appointment_id"),
    "procedure": ("procedures.view_procedure", "procedure_id"),
    "report": ("reports.view_report", "report_id"),
}


def entity_url(entity: str, entity_id: int, *, _external: bool = True) -> str:
    if entity not in ENTITY_ROUTES:
        raise ValueError(f"Unknown entity type: {entity}")
    endpoint, param = ENTITY_ROUTES[entity]
    return url_for(endpoint, **{param: entity_id}, _external=_external)


def generate_qr_png(entity: str, entity_id: int) -> bytes:
    target = entity_url(entity, entity_id)
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(target)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (200, 200), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 180, 180], outline="black", width=2)
        draw.text((30, 90), "QR", fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
