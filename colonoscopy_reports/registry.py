"""Colonoscopy research registry — listing and Excel export."""

from __future__ import annotations

import session_service
from registry_service import Column, build_excel_workbook, filter_by_date_range


def get_registry_rows(dbconn, start_iso: str, end_iso: str) -> list[dict]:
    rows = dbconn.execute(
        """
        SELECT
            a.id AS appointment_id,
            a.patient_name, a.mrn, a.gender, a.age, a.appointment_date,
            a.procedure_type,
            r.id AS report_id, r.status, r.payload_json,
            r.impression, r.procedure_note,
            e.full_name AS endoscopist_name,
            rs.indication_summary, rs.caecum_reached, rs.ti_intubated,
            rs.withdrawal_time_min, rs.bbps_total, rs.prep_regimen,
            rs.polypectomy_performed, rs.polyps_resected_count,
            rs.adenoma_documented, rs.immediate_complication,
            rs.procedure_completed, rs.surveillance_interval
        FROM appointment a
        LEFT JOIN colonoscopy_v2_report r ON r.appointment_id = a.id
        LEFT JOIN endoscopist e ON e.id = r.endoscopist_id
        LEFT JOIN colonoscopy_research rs ON rs.report_id = r.id
        WHERE a.procedure_type IN ('colonoscopy', 'polypectomy')
        ORDER BY a.appointment_date, a.id
        """
    ).fetchall()

    flat = [dict(row) for row in rows]
    filtered = filter_by_date_range(flat, 'appointment_date', start_iso, end_iso)

    enriched = []
    for row in filtered:
        sessions = session_service.list_sessions(
            dbconn, 'colonoscopy', row.get('mrn') or '', fallback_row=row,
        )
        session_map = session_service.number_sessions(sessions)
        appt_id = row['appointment_id']
        enriched.append({
            **row,
            'session_number': session_map.get(appt_id, 1),
            'total_sessions_for_patient': len(sessions),
            'has_multiple_sessions': len(sessions) > 1,
        })
    return enriched


REGISTRY_COLUMNS = [
    Column('appointment_date', 'Date'),
    Column('session_number', 'Session'),
    Column('total_sessions_for_patient', 'Sessions (Patient)'),
    Column('patient_name', 'Patient'),
    Column('mrn', 'MRN'),
    Column('gender', 'Gender'),
    Column('age', 'Age'),
    Column('indication_summary', 'Indication'),
    Column('endoscopist_name', 'Endoscopist'),
    Column('caecum_reached', 'Caecum'),
    Column('ti_intubated', 'TI'),
    Column('bbps_total', 'BBPS Total'),
    Column('withdrawal_time_min', 'Withdrawal (min)'),
    Column('polypectomy_performed', 'Polypectomy'),
    Column('polyps_resected_count', 'Polyps'),
    Column('adenoma_documented', 'Adenoma'),
    Column('immediate_complication', 'Complication'),
    Column('procedure_completed', 'Completed'),
    Column('surveillance_interval', 'Surveillance'),
    Column('status', 'Report Status'),
]


def build_registry_export(rows: list[dict]):
    return build_excel_workbook(
        rows, REGISTRY_COLUMNS,
        sheet_title='Colonoscopy Registry',
        header_fill_color='2B6CB0',
    )
