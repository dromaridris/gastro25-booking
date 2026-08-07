# سجل التعارضات — Gastro25 يفوز

| المجال | GastroIntelligence | Gastro25 (معتمد) | القرار |
|--------|-------------------|------------------|--------|
| قاعدة البيانات | PostgreSQL + SQLAlchemy + Alembic | SQLite + init_db() | **Gastro25** — جداول GI additive فقط (`gi_*`, `ward_*`) |
| المصادقة | RBAC permission codes | 6 أدوار + session cookie | **Gastro25** — خريطة capabilities في `gi_platform/permissions.py` |
| الحجز / المواعيد | appointments blueprint | dashboard + appointment table | **Gastro25** — لم يُ mount GI appointments |
| ERCP | clinical_reports (GI) | ercp_* في app.py (~2630–3467) | **Gastro25 byte-for-byte** — لم يُمس |
| Research registry ERCP | research module | `/ercp-research-registry` | **Gastro25** — GI research منفصل على `/research` |
| Ward / Inpatient | inpatient ORM | `ward/*` SQLite | **Gastro25** — منطق GI مُقتبس، تنفيذ SQLite |
| Knowledge Library | PostgreSQL models | `gi_knowledge_*` SQLite | **Gastro25 adapter** — نفس مفاهيم GI |
| Clinical AI | LLM providers + Celery | `gi_ai_*` stub + audit log | **Gastro25** — جاهز للربط عبر `GI_AI_PROVIDER` |
| Global Search | Elasticsearch-style service | توسيع `/search` + context processor | **Gastro25** — booking + ward + knowledge |
| Branding / UI | GI base.html + modern-ui.css | Gastro25 base.html + style.css | **Gastro25** — قوالب GI مرجع في `gi_import/source/templates/` |
| Users module | GI users blueprint | Gastro25 `/admin` + register | **Gastro25** |
| Procedures (GI) | procedures blueprint | booking + procedure_extensions | **Gastro25** — ERCP منفصل |

## لماذا لم نُشغّل GI blueprints مباشرة؟

كود GI يستورد `from app.modules...` ويتوقع Flask-SQLAlchemy `db`. تشغيله داخل Gastro25 يتطلب محاكاة حزمة `app` كاملة وتعارض مع auth/DB. الحل المعتمد: **نسخ المرجع** في `gi_import/source/` + **تنفيذ runtime** في `gi_platform/` و `gi_routes/`.
