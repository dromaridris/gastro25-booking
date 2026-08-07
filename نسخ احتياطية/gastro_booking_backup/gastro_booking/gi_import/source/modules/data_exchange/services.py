"""Data export services."""

import csv
import io
import json
import uuid

from flask import current_app

from app.core.base_model import utcnow
from app.core.exceptions import ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.data_exchange.models import JOB_COMPLETED, JOB_EXPORT, JOB_FAILED, DataExchangeJob
from app.modules.patients.models import Patient
from app.storage.local_backend import get_storage_backend


def _require(user, code: str):
    permission_engine.require(user, code)


def list_jobs(acting_user) -> list[DataExchangeJob]:
    _require(acting_user, "data:export")
    return DataExchangeJob.query.filter_by(is_archived=False).order_by(DataExchangeJob.created_at.desc()).limit(50).all()


def export_patients(acting_user, *, fmt: str = "csv") -> DataExchangeJob:
    _require(acting_user, "data:export")
    if fmt not in ("csv", "json"):
        raise ValidationError("Format must be csv or json.")
    job = DataExchangeJob(
        job_type=JOB_EXPORT,
        format=fmt,
        requested_by_id=acting_user.id,
        started_at=utcnow(),
        created_by_id=acting_user.id,
    )
    db.session.add(job)
    db.session.flush()
    patients = Patient.query.filter_by(is_archived=False).order_by(Patient.last_name).all()
    try:
        if fmt == "json":
            payload = [
                {"id": p.id, "mrn": p.mrn, "first_name": p.first_name, "last_name": p.last_name,
                 "date_of_birth": p.date_of_birth.isoformat(), "sex": p.sex}
                for p in patients
            ]
            data = json.dumps(payload, indent=2).encode("utf-8")
            ext = ".json"
            content_type = "application/json"
        else:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["id", "mrn", "first_name", "last_name", "date_of_birth", "sex"])
            for p in patients:
                writer.writerow([p.id, p.mrn, p.first_name, p.last_name, p.date_of_birth.isoformat(), p.sex])
            data = buf.getvalue().encode("utf-8")
            ext = ".csv"
            content_type = "text/csv"
        key = f"exports/patients/{job.id}/{uuid.uuid4().hex}{ext}"
        storage = get_storage_backend(current_app.config)
        storage.save(key, io.BytesIO(data))
        job.storage_key = key
        job.record_count = len(patients)
        job.status = JOB_COMPLETED
        job.completed_at = utcnow()
    except Exception as exc:
        job.status = JOB_FAILED
        job.error_message = str(exc)
        job.completed_at = utcnow()
    db.session.commit()
    audit_engine.log("data.export", user=acting_user, target_type="data_exchange_job", target_id=job.id, details={"format": fmt})
    return job
