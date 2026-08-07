"""
Gastro25 entry point (local dev + PythonAnywhere).

The full application lives in gastro_booking/app.py. This file only loads it
so `python app.py` from the repository root uses the complete routes and
templates (ERCP registry, dilatation, patient search, etc.).
"""

from __future__ import annotations

import importlib.util
import os
import sys

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
APP_DIR = os.path.join(ROOT_DIR, "gastro_booking")

# Use gastro_booking/ for DB, images, and other runtime data.
os.environ.setdefault("GASTRO_DATA_DIR", APP_DIR)

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

_spec = importlib.util.spec_from_file_location(
    "gastro_booking_main", os.path.join(APP_DIR, "app.py")
)
_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["gastro_booking_main"] = _module
_spec.loader.exec_module(_module)

app = _module.app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(debug=True, port=port)
