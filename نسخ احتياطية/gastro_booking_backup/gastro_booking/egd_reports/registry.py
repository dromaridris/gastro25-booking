"""EGD (Upper GI) research registry — listing and Excel export."""

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
            rs.indication_summary, rs.urgency, rs.d2_reached,
            rs.retroflexion_performed, rs.variceal_banding_performed,
            rs.bands_placed, rs.variceal_grade,
            rs.hemostasis_performed, rs.forrest_classification,
            rs.hemostasis_success, rs.sclerotherapy_performed,
            rs.intervention_peg, rs.intervention_polypectomy,
            rs.immediate_complication,
            rs.procedure_completed, rs.surveillance_interval
        FROM appointment a
        LEFT JOIN upper_gi_v2_report r ON r.appointment_id = a.id
        LEFT JOIN endoscopist e ON e.id = r.endoscopist_id
        LEFT JOIN upper_gi_research rs ON rs.report_id = r.id
        WHERE a.procedure_type IN ('upper_gi', 'peg_tube')
        ORDER BY a.appointment_date, a.id
        """
    ).fetchall()

    flat = [dict(row) for row in rows]
    filtered = filter_by_date_range(flat, 'appointment_date', start_iso, end_iso)

    enriched = []
    for row in filtered:
        sessions = session_service.list_sessions(
            dbconn, 'upper_gi', row.get('mrn') or '', fallback_row=row,
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
    Column('d2_reached', 'D2 Reached'),
    Column('retroflexion_performed', 'Retroflexion'),
    Column('variceal_banding_performed', 'Variceal Banding'),
    Column('bands_placed', 'Bands'),
    Column('variceal_grade', 'Variceal Grade'),
    Column('hemostasis_performed', 'Haemostasis'),
    Column('forrest_classification', 'Forrest Class'),
    Column('hemostasis_success', 'Haemostasis OK'),
    Column('sclerotherapy_performed', 'Sclerotherapy'),
    Column('intervention_peg', 'PEG'),
    Column('intervention_polypectomy', 'Polypectomy'),
    Column('immediate_complication', 'Complication'),
    Column('procedure_completed', 'Completed'),
    Column('surveillance_interval', 'Surveillance'),
    Column('status', 'Report Status'),
]


def build_registry_export(rows: list[dict]):
    return build_excel_workbook(
        rows, REGISTRY_COLUMNS,
        sheet_title='EGD Registry',
        header_fill_color='A6192E',
    )
