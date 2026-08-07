// ------------------------------------------------------------------
// Endoscopic Dilatation Module — frontend logic (Phase 4)
// ------------------------------------------------------------------
// Loaded alongside app.js on Dilatation pages only. Reuses app.js's
// generic helpers (api(), escapeHtml(), showAlertPopup(), the shared
// follow-up modal via window.FOLLOWUP_ENDPOINTS) rather than duplicating
// them. Does not modify any ERCP-specific function in app.js.

// Follow-up endpoints for this module — passed to setFollowupEndpoints()
// (defined in app.js) so the shared follow-up modal/timeline code talks
// to Dilatation's routes instead of ERCP's.
const DILATATION_FOLLOWUP_ENDPOINTS = {
  list: (reportId) => `/api/dilatation/${reportId}/followups`,
  item: (followupId) => `/api/dilatation-followup/${followupId}`,
};

// ==================================================================
// DILATATION REPORT EDITOR
// ==================================================================
function initDilatationReport() {
  const page = document.querySelector('.ercp-page');
  if (!page) return;
  const reportId = page.dataset.reportId;
  const locked = page.dataset.locked === 'true';

  function checkedValues(containerId) {
    return Array.from(document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`)).map(el => el.value);
  }

  function gatherPayload() {
    return {
      endoscopist_id: document.getElementById('f_endoscopist_id').value || null,
      sedation: document.getElementById('f_sedation').value,
      technician: document.getElementById('f_technician').value,
      assistants: document.getElementById('f_assistants').value,
      procedure_site: document.getElementById('f_procedure_site').value,
      indication: document.getElementById('f_indication').value,
      stricture_location_detail: document.getElementById('f_stricture_location_detail').value,
      stricture_length_mm: document.getElementById('f_stricture_length_mm').value,
      stricture_severity: document.getElementById('f_stricture_severity').value,
      stricture_appearance: document.getElementById('f_stricture_appearance').value,
      endoscope_traversed: document.getElementById('f_endoscope_traversed').value,
      previous_intervention: document.getElementById('f_previous_intervention').value,
      guidewire_used: document.getElementById('f_guidewire_used').value,
      fluoroscopy_used: document.getElementById('f_fluoroscopy_used').value,
      dilatation_technique: document.getElementById('f_dilatation_technique').value,
      balloon_type: document.getElementById('f_balloon_type').value,
      balloon_starting_diameter_mm: document.getElementById('f_balloon_starting_diameter_mm').value,
      balloon_final_diameter_mm: document.getElementById('f_balloon_final_diameter_mm').value,
      balloon_inflation_time_sec: document.getElementById('f_balloon_inflation_time_sec').value,
      balloon_num_inflations: document.getElementById('f_balloon_num_inflations').value,
      balloon_resistance: document.getElementById('f_balloon_resistance').value,
      balloon_mucosal_tear: document.getElementById('f_balloon_mucosal_tear').value,
      savary_starting_size_fr: document.getElementById('f_savary_starting_size_fr').value,
      savary_final_size_fr: document.getElementById('f_savary_final_size_fr').value,
      savary_num_dilators: document.getElementById('f_savary_num_dilators').value,
      savary_resistance: document.getElementById('f_savary_resistance').value,
      savary_mucosal_tear: document.getElementById('f_savary_mucosal_tear').value,
      immediate_technical_success: document.getElementById('f_immediate_technical_success').value,
      failure_reason: document.getElementById('f_failure_reason').value,
      complications: checkedValues('f_complications'),
      procedure_note: document.getElementById('f_procedure_note').value,
      impression: document.getElementById('f_impression').value,
      recommendations: document.getElementById('f_recommendations').value,
    };
  }

  // ---- Only show fields relevant to the selected technique ----
  function setupTechniqueToggle() {
    const select = document.getElementById('f_dilatation_technique');
    const balloonFields = document.getElementById('balloonFields');
    const savaryFields = document.getElementById('savaryFields');
    if (!select || !balloonFields || !savaryFields) return;
    function sync() {
      balloonFields.hidden = select.value !== 'Balloon Dilatation';
      savaryFields.hidden = select.value !== 'Savary-Gilliard Dilatation';
    }
    select.addEventListener('change', sync);
    sync();
  }

  // ---- Reason for Failure only shown when Immediate Technical Success is Failed ----
  function setupFailureReasonToggle() {
    const select = document.getElementById('f_immediate_technical_success');
    const field = document.getElementById('failureReasonField');
    if (!select || !field) return;
    function sync() {
      field.hidden = select.value !== 'Failed';
    }
    select.addEventListener('change', sync);
    sync();
  }

  async function saveReport(silent) {
    try {
      await api(`/dilatation/${reportId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gatherPayload()),
      });
      if (window.markReportSaved) window.markReportSaved();
      if (!silent) {
        const notice = document.getElementById('dilatationSaveNotice');
        notice.hidden = false;
        setTimeout(() => { notice.hidden = true; }, 2500);
      }
      return true;
    } catch (err) {
      showAlertPopup(err.message);
      return false;
    }
  }

  const saveBtn = document.getElementById('saveDilatationReportBtn');
  if (saveBtn) saveBtn.addEventListener('click', () => saveReport(false));

  const generateBtn = document.getElementById('generateDilatationNoteBtn');
  if (generateBtn) {
    generateBtn.addEventListener('click', async () => {
      const noteField = document.getElementById('f_procedure_note');
      if (noteField.value.trim() && !confirm('This will replace the current note text with a freshly generated draft. Continue?')) {
        return;
      }
      try {
        const payload = gatherPayload();
        const result = await api(`/dilatation/${reportId}/generate-note`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        noteField.value = result.note;
      } catch (err) {
        showAlertPopup(err.message);
      }
    });
  }

  const finalizeBtn = document.getElementById('finalizeDilatationReportBtn');
  if (finalizeBtn) {
    finalizeBtn.addEventListener('click', async () => {
      if (!confirm('Finalize this report? It will become read-only — only an Admin can unlock it afterward.')) return;
      const saved = await saveReport(true);
      if (!saved) return;
      try {
        await api(`/dilatation/${reportId}/finalize`, { method: 'POST' });
        window.location.reload();
      } catch (err) {
        showAlertPopup(err.message);
      }
    });
  }

  if (!locked) {
    document.querySelectorAll('.dilatation-image-input').forEach(input => {
      input.addEventListener('change', async () => {
        const slot = input.dataset.slot;
        if (!input.files || !input.files[0]) return;
        const fd = new FormData();
        fd.append('image', input.files[0]);
        try {
          const res = await fetch(`/dilatation/${reportId}/image/${slot}`, { method: 'POST', body: fd });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || 'Upload failed.');
          window.location.reload();
        } catch (err) {
          showAlertPopup(err.message);
        }
      });
    });
    setupTechniqueToggle();
    setupFailureReasonToggle();
    initUnsavedChangesGuard('#dilatationFieldset', saveReport);
  }
}

async function dilatationDeleteImage(slot) {
  const page = document.querySelector('.ercp-page');
  if (!page) return;
  const reportId = page.dataset.reportId;
  if (!confirm('Remove this image?')) return;
  try {
    await api(`/dilatation/${reportId}/image/${slot}/delete`, { method: 'POST' });
    window.location.reload();
  } catch (err) {
    showAlertPopup(err.message);
  }
}

// ==================================================================
// RESEARCH DATA (Phase 6) — deliberately independent of the report's
// finalize/lock status. Its fields live outside the disabled fieldset in
// the template, and this always registers its Save handler regardless of
// lock state, so research stays editable even after finalizing.
// ==================================================================
function initDilatationResearch() {
  const page = document.querySelector('.ercp-page');
  if (!page) return;
  const reportId = page.dataset.reportId;

  const saveBtn = document.getElementById('saveDilatationResearchBtn');
  if (!saveBtn) return;

  saveBtn.addEventListener('click', async () => {
    const payload = {
      stricture_etiology: document.getElementById('r_stricture_etiology').value,
      estimated_diameter_before_mm: document.getElementById('r_estimated_diameter_before_mm').value,
      estimated_diameter_after_mm: document.getElementById('r_estimated_diameter_after_mm').value,
      guidewire_type: document.getElementById('r_guidewire_type').value,
      balloon_brand: document.getElementById('r_balloon_brand').value,
      savary_set_used: document.getElementById('r_savary_set_used').value,
      technical_difficulty: document.getElementById('r_technical_difficulty').value,
      clinical_success: document.getElementById('r_clinical_success').value,
      need_repeat_dilatation: document.getElementById('r_need_repeat_dilatation').value,
      followup_interval: document.getElementById('r_followup_interval').value,
    };
    try {
      await api(`/dilatation/${reportId}/research/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const notice = document.getElementById('dilatationResearchSaveNotice');
      notice.hidden = false;
      setTimeout(() => { notice.hidden = true; }, 2500);
    } catch (err) {
      showAlertPopup(err.message);
    }
  });
}

// ==================================================================
// SCHEDULE REPEAT DILATATION MODAL (shared by dilatation_report.html and
// dilatation_patient_overview.html). No weekday-eligibility restriction —
// unlike ERCP, Dilatation isn't limited to specific days.
// ==================================================================
function initRepeatDilatationModal() {
  const modalEl = document.getElementById('repeatDilatationModal');
  if (!modalEl) return;

  const form = document.getElementById('repeatDilatationForm');
  const apptIdField = document.getElementById('repeatDilatationSourceApptId');
  const dateField = document.getElementById('repeatDilatationDateField');
  const infoEl = document.getElementById('repeatDilatationPatientInfo');
  const errorEl = document.getElementById('repeatDilatationError');

  window.openRepeatDilatationModal = function (apptId, patientLabel) {
    apptIdField.value = apptId;
    dateField.value = '';
    infoEl.textContent = patientLabel || '';
    errorEl.hidden = true;
    modalEl.hidden = false;
  };

  document.getElementById('closeRepeatDilatationBtn').addEventListener('click', () => { modalEl.hidden = true; });
  document.getElementById('cancelRepeatDilatationBtn').addEventListener('click', () => { modalEl.hidden = true; });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    try {
      const result = await api(`/api/appointment/${apptIdField.value}/repeat-dilatation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appointment_date: dateField.value }),
      });
      modalEl.hidden = true;
      if (result.appointment) {
        window.location.href = `/dilatation-patient-overview/${result.appointment.repeat_of_appointment_id}`;
      } else {
        window.location.reload();
      }
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    }
  });
}
