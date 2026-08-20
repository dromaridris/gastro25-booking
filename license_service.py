"""Offline, signed installation licensing for Gastro Booking.

Only the public verification key is shipped with the application. Activation
codes are created by the owner's private license manager and cannot be forged
from the files installed on a customer's server.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization


PRODUCT_CODE = "GASTRO-BOOKING"
INSTALLATION_FILE = ".gastro_installation_id"
LICENSE_FILE = "gastro_license.json"
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAHmHO3nfTBHfk4F4F4e5sReJcCx5kiKCRIDhDP/bakUk=
-----END PUBLIC KEY-----
"""


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _normalise_host(host: str) -> str:
    value = (host or "localhost").strip().lower()
    if value.startswith("[") and "]" in value:  # IPv6 host, optionally with port
        return value[1:value.index("]")]
    return value.split(":", 1)[0] or "localhost"


def _atomic_write(path: str, value: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(value)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def installation_id(data_dir: str) -> str:
    path = os.path.join(data_dir, INSTALLATION_FILE)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            existing = handle.read().strip()
        if re.fullmatch(r"[0-9a-f]{32}", existing):
            return existing
    except OSError:
        pass

    generated = uuid.uuid4().hex
    _atomic_write(path, generated)
    return generated


def device_code(data_dir: str, host: str) -> str:
    raw = f"{PRODUCT_CODE}|{installation_id(data_dir)}|{_normalise_host(host)}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()[:24]
    return "GB-" + "-".join(digest[i:i + 4] for i in range(0, 24, 4))


def _decode_and_verify(activation_code: str) -> dict:
    compact = "".join((activation_code or "").split())
    parts = compact.split(".")
    if len(parts) != 2:
        raise ValueError("Activation key format is invalid.")
    try:
        payload_bytes = _b64decode(parts[0])
        signature = _b64decode(parts[1])
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        public_key.verify(signature, payload_bytes)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (InvalidSignature, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Activation key is invalid or has been altered.") from exc

    if not isinstance(payload, dict) or payload.get("product") != PRODUCT_CODE:
        raise ValueError("Activation key is not for Gastro Booking.")
    return payload


def validate_activation_code(activation_code: str, data_dir: str, host: str) -> dict:
    payload = _decode_and_verify(activation_code)
    if payload.get("device_code") != device_code(data_dir, host):
        raise ValueError("Activation key belongs to a different installation or domain.")
    expires_at = payload.get("expires_at")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Activation key expiry is invalid.") from exc
        if expiry <= datetime.now(timezone.utc):
            raise ValueError("Activation key has expired.")
    return payload


def activate(activation_code: str, data_dir: str, host: str) -> dict:
    payload = validate_activation_code(activation_code, data_dir, host)
    record = {
        "activation_code": "".join(activation_code.split()),
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "license": payload,
    }
    _atomic_write(
        os.path.join(data_dir, LICENSE_FILE),
        json.dumps(record, ensure_ascii=False, indent=2),
    )
    return payload


def license_status(data_dir: str, host: str) -> tuple[bool, dict | None, str | None]:
    path = os.path.join(data_dir, LICENSE_FILE)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
        payload = validate_activation_code(record.get("activation_code", ""), data_dir, host)
        return True, payload, None
    except FileNotFoundError:
        return False, None, "This installation has not been activated."
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return False, None, str(exc)
