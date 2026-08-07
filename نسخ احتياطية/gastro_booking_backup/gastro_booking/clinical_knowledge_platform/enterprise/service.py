"""Phase 8 — Enterprise platform foundations (tenancy, RBAC, integrations, ops)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Protocol


# --- Integration adapter contract ---

class IntegrationAdapter(Protocol):
    system_kind: str

    def health_check(self, config: dict) -> dict: ...

    def send(self, config: dict, payload: dict) -> dict: ...

    def fetch(self, config: dict, query: dict) -> dict: ...


class StubAdapter:
    """Working adapter pattern — realistic stubs for hospital systems."""

    def __init__(self, system_kind: str):
        self.system_kind = system_kind

    def health_check(self, config: dict) -> dict:
        return {
            "ok": True,
            "status": "stub",
            "system_kind": self.system_kind,
            "message": f"{self.system_kind} adapter is registered; no live connection configured.",
            "endpoint": (config or {}).get("base_url"),
        }

    def send(self, config: dict, payload: dict) -> dict:
        return {"ok": True, "mode": "stub_send", "accepted": True, "echo": payload, "system_kind": self.system_kind}

    def fetch(self, config: dict, query: dict) -> dict:
        return {"ok": True, "mode": "stub_fetch", "results": [], "query": query, "system_kind": self.system_kind}


ADAPTER_REGISTRY: dict[str, IntegrationAdapter] = {
    "fhir": StubAdapter("fhir"),
    "hl7_v2": StubAdapter("hl7_v2"),
    "dicom": StubAdapter("dicom"),
    "lis": StubAdapter("lis"),
    "ris": StubAdapter("ris"),
    "pacs": StubAdapter("pacs"),
    "his": StubAdapter("his"),
    "pharmacy": StubAdapter("pharmacy"),
    "scheduling": StubAdapter("scheduling"),
}


def get_adapter(name: str) -> IntegrationAdapter | None:
    return ADAPTER_REGISTRY.get(name)


def ensure_default_tenant(db: sqlite3.Connection) -> dict:
    row = db.execute("SELECT * FROM ckp_tenant WHERE code='default'").fetchone()
    if row:
        return dict(row)
    cur = db.execute(
        "INSERT INTO ckp_tenant (code, label, config_json) VALUES (?,?,?)",
        ("default", "Default Hospital Tenant", json.dumps({"locale": "en", "timezone": "Asia/Riyadh"})),
    )
    tid = int(cur.lastrowid)
    db.execute(
        "INSERT INTO ckp_department (tenant_id, code, label) VALUES (?,?,?), (?,?,?), (?,?,?)",
        (tid, "gastro", "Gastroenterology", tid, "cardio", "Cardiology", tid, "general", "General Medicine"),
    )
    # Seed integration stubs
    for kind, label in [
        ("fhir", "FHIR R4 Gateway"),
        ("hl7_v2", "HL7 v2 Interface Engine"),
        ("dicom", "DICOM Worklist/Store"),
        ("lis", "Laboratory Information System"),
        ("ris", "Radiology Information System"),
        ("pacs", "PACS"),
        ("his", "Hospital Information System"),
        ("pharmacy", "Pharmacy System"),
        ("scheduling", "Enterprise Scheduling"),
    ]:
        db.execute(
            """INSERT OR IGNORE INTO ckp_integration_endpoint
               (tenant_id, system_kind, code, label, adapter, status, config_json)
               VALUES (?,?,?,?,?,?,?)""",
            (tid, kind, f"{kind}.primary", label, kind, "stub", json.dumps({"base_url": None})),
        )
    # RBAC permission seeds
    for code, label in [
        ("ckp.encounter.read", "Read clinical encounters"),
        ("ckp.encounter.write", "Write clinical encounters"),
        ("ckp.docs.finalize", "Finalize clinical documents"),
        ("ckp.cds.view", "View CDS advisories"),
        ("ckp.research.export", "Export research datasets"),
        ("ckp.admin.tenant", "Administer tenant"),
        ("ckp.integration.manage", "Manage integrations"),
    ]:
        db.execute("INSERT OR IGNORE INTO ckp_rbac_permission (code, label) VALUES (?,?)", (code, label))
    for role, perms in [
        ("consultant", ["ckp.encounter.read", "ckp.encounter.write", "ckp.docs.finalize", "ckp.cds.view"]),
        ("specialist", ["ckp.encounter.read", "ckp.encounter.write", "ckp.cds.view"]),
        ("admin", ["ckp.encounter.read", "ckp.encounter.write", "ckp.docs.finalize", "ckp.cds.view", "ckp.research.export", "ckp.admin.tenant", "ckp.integration.manage"]),
        ("researcher", ["ckp.research.export", "ckp.cds.view"]),
    ]:
        for p in perms:
            db.execute(
                "INSERT OR IGNORE INTO ckp_rbac_role_perm (role_code, permission_code) VALUES (?,?)",
                (role, p),
            )
    # i18n foundations
    for key, en, ar in [
        ("ckp.channel.history", "History", "التاريخ المرضي"),
        ("ckp.channel.examination", "Examination", "الفحص السريري"),
        ("ckp.channel.investigations", "Investigations", "الفحوصات"),
        ("ckp.channel.summary", "Summary", "الملخص"),
        ("ckp.channel.plan", "Plan", "الخطة"),
        ("ckp.cds.advisory", "Advisory only — not an order", "استشاري فقط — ليس أمرًا"),
    ]:
        db.execute("INSERT OR IGNORE INTO ckp_i18n_string (key, locale, value) VALUES (?,?,?)", (key, "en", en))
        db.execute("INSERT OR IGNORE INTO ckp_i18n_string (key, locale, value) VALUES (?,?,?)", (key, "ar", ar))
    db.commit()
    return dict(db.execute("SELECT * FROM ckp_tenant WHERE id=?", (tid,)).fetchone())


def list_departments(db: sqlite3.Connection, tenant_id: int) -> list[dict]:
    return [dict(r) for r in db.execute("SELECT * FROM ckp_department WHERE tenant_id=?", (tenant_id,)).fetchall()]


def role_permissions(db: sqlite3.Connection, role_code: str) -> list[str]:
    return [
        r["permission_code"]
        for r in db.execute(
            "SELECT permission_code FROM ckp_rbac_role_perm WHERE role_code=?",
            (role_code,),
        ).fetchall()
    ]


def audit(db: sqlite3.Connection, *, action: str, tenant_id: int | None = None, actor_id: int | None = None, object_kind: str | None = None, object_id: str | None = None, detail: dict | None = None) -> None:
    db.execute(
        """INSERT INTO ckp_enterprise_audit (tenant_id, actor_id, action, object_kind, object_id, detail_json)
           VALUES (?,?,?,?,?,?)""",
        (tenant_id, actor_id, action, object_kind, object_id, json.dumps(detail or {}, ensure_ascii=False)),
    )
    db.commit()


def list_integrations(db: sqlite3.Connection, tenant_id: int | None = None) -> list[dict]:
    if tenant_id:
        rows = db.execute("SELECT * FROM ckp_integration_endpoint WHERE tenant_id=? ORDER BY system_kind", (tenant_id,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM ckp_integration_endpoint ORDER BY system_kind").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d.pop("config_json") or "{}")
        d["health"] = json.loads(d.pop("health_json") or "{}")
        out.append(d)
    return out


def check_integration_health(db: sqlite3.Connection, endpoint_id: int) -> dict:
    row = db.execute("SELECT * FROM ckp_integration_endpoint WHERE id=?", (endpoint_id,)).fetchone()
    if not row:
        raise ValueError("Endpoint not found")
    adapter = get_adapter(row["adapter"])
    config = json.loads(row["config_json"] or "{}")
    if not adapter:
        health = {"ok": False, "error": f"Unknown adapter {row['adapter']}"}
    else:
        health = adapter.health_check(config)
    db.execute(
        "UPDATE ckp_integration_endpoint SET health_json=?, last_checked_at=datetime('now'), status=? WHERE id=?",
        (json.dumps(health, ensure_ascii=False), "stub_ok" if health.get("ok") else "error", endpoint_id),
    )
    db.commit()
    return health


def enqueue_job(db: sqlite3.Connection, job_type: str, payload: dict | None = None) -> int:
    cur = db.execute(
        "INSERT INTO ckp_job_queue (job_type, payload_json) VALUES (?,?)",
        (job_type, json.dumps(payload or {}, ensure_ascii=False)),
    )
    db.commit()
    return int(cur.lastrowid)


def process_next_job(db: sqlite3.Connection) -> dict | None:
    row = db.execute(
        "SELECT * FROM ckp_job_queue WHERE status='queued' ORDER BY id LIMIT 1"
    ).fetchone()
    if not row:
        return None
    db.execute(
        "UPDATE ckp_job_queue SET status='running', attempts=attempts+1, updated_at=datetime('now') WHERE id=?",
        (row["id"],),
    )
    db.commit()
    # Stub processor
    db.execute(
        "UPDATE ckp_job_queue SET status='done', updated_at=datetime('now') WHERE id=?",
        (row["id"],),
    )
    db.commit()
    return {"id": row["id"], "job_type": row["job_type"], "status": "done"}


def notify(db: sqlite3.Connection, *, title: str, body: str = "", recipient: str | None = None, tenant_id: int | None = None, channel: str = "in_app") -> int:
    cur = db.execute(
        """INSERT INTO ckp_notification (tenant_id, channel, recipient, title, body, status, sent_at)
           VALUES (?,?,?,?,?,'sent',datetime('now'))""",
        (tenant_id, channel, recipient, title, body),
    )
    db.commit()
    return int(cur.lastrowid)


def index_object(db: sqlite3.Connection, *, object_kind: str, object_id: str, title: str, body: str = "", tenant_id: int | None = None) -> None:
    tokens = " ".join((title or "").lower().split() + (body or "").lower().split()[:50])
    db.execute(
        """INSERT INTO ckp_search_index (object_kind, object_id, tenant_id, title, body, tokens, updated_at)
           VALUES (?,?,?,?,?,?,datetime('now'))
           ON CONFLICT(object_kind, object_id) DO UPDATE SET
             title=excluded.title, body=excluded.body, tokens=excluded.tokens, updated_at=datetime('now')""",
        (object_kind, object_id, tenant_id, title, body, tokens),
    )
    db.commit()


def search(db: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    q = f"%{(query or '').strip().lower()}%"
    return [dict(r) for r in db.execute(
        "SELECT * FROM ckp_search_index WHERE tokens LIKE ? OR title LIKE ? ORDER BY updated_at DESC LIMIT ?",
        (q, q, limit),
    ).fetchall()]


def t(db: sqlite3.Connection, key: str, locale: str = "en") -> str:
    row = db.execute("SELECT value FROM ckp_i18n_string WHERE key=? AND locale=?", (key, locale)).fetchone()
    if row:
        return row["value"]
    row = db.execute("SELECT value FROM ckp_i18n_string WHERE key=? AND locale='en'", (key,)).fetchone()
    return row["value"] if row else key


def observability_snapshot(db: sqlite3.Connection) -> dict:
    return {
        "tenants": db.execute("SELECT COUNT(*) AS c FROM ckp_tenant").fetchone()["c"],
        "integrations": db.execute("SELECT COUNT(*) AS c FROM ckp_integration_endpoint").fetchone()["c"],
        "jobs_queued": db.execute("SELECT COUNT(*) AS c FROM ckp_job_queue WHERE status='queued'").fetchone()["c"],
        "jobs_done": db.execute("SELECT COUNT(*) AS c FROM ckp_job_queue WHERE status='done'").fetchone()["c"],
        "notifications": db.execute("SELECT COUNT(*) AS c FROM ckp_notification").fetchone()["c"],
        "search_docs": db.execute("SELECT COUNT(*) AS c FROM ckp_search_index").fetchone()["c"],
        "audit_events": db.execute("SELECT COUNT(*) AS c FROM ckp_enterprise_audit").fetchone()["c"],
    }
