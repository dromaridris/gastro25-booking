"""Compress clinical report images before storage."""

import io

from PIL import Image, ImageOps

MAX_EDGE_PX = 1280
JPEG_QUALITY = 78


def compress_image(file_bytes: bytes, content_type: str) -> tuple[io.BytesIO, str]:
    """Return compressed JPEG bytes and normalized content type."""
    with Image.open(io.BytesIO(file_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        width, height = img.size
        longest = max(width, height)
        if longest > MAX_EDGE_PX:
            scale = MAX_EDGE_PX / float(longest)
            img = img.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        out.seek(0)
        return out, "image/jpeg"
