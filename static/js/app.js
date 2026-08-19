// ------------------------------------------------------------------
// JPMC Gastroenterology & Hepatology — shared frontend logic
// ------------------------------------------------------------------

let ME = null; // { username, role, role_label, can_override, can_book_ercp, can_book_special }
const APPT_CACHE = {}; // id -> appointment object, populated whenever we render a list

function toggleColumn(headerEl) {
  const list = headerEl.nextElementSibling;
  if (!list) return;
  list.classList.toggle('collapsed');
  headerEl.classList.toggle('is-collapsed');
}

async function api(url, options) {
  const res = await fetch(url, options);
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const msg = (data && data.error) ? data.error : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

async function loadMe() {
  if (!ME) ME = await api('/api/me');
  return ME;
}

function hasFullAccess(me) {
  return !!(me && (me.has_full_access || me.role === 'admin' || me.role === 'hod'));
}

function canManage(appt) {
  if (!ME) return false;
  return appt.booked_by_username === ME.username || ME.can_override || hasFullAccess(ME);
}

// Mirrors the backend's SCHEDULER_LIKE_ROLES — Endoscopy Staff has identical
// authority to Scheduler everywhere, including this edit/delete time-lock.
function isSchedulerLikeRole(role) {
  return role === 'scheduler' || role === 'endoscopy_staff';
}

// Mirrors the server-side rule: once the appointment day has arrived OR 48h
// have passed since booking, Scheduler/Endoscopy Staff accounts lose edit rights and only
// Admin retains delete rights. This is a UX convenience only — the server
// enforces the real rule regardless of what the client shows.
function isTimeLocked(a) {
  const todayStr = new Date().toISOString().slice(0, 10);
  const dayArrived = a.appointment_date <= todayStr;
  const createdMs = new Date(a.created_at + 'Z').getTime();
  const hoursSince = (Date.now() - createdMs) / 3600000;
  return dayArrived || (isFinite(hoursSince) && hoursSince >= 48);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : str;
  return div.innerHTML;
}

// Shared by the booking modal's ERCP option and the Repeat ERCP modal —
// ERCP can only be scheduled on Tuesdays or Saturdays.
function isErcpEligible(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const day = d.getDay(); // 0=Sun ... 2=Tue ... 6=Sat
  return day === 2 || day === 6;
}

function apptCardHTML(a) {
  APPT_CACHE[a.id] = a;
  const bleedTag = a.is_bleeding ? '<span class="appt-bleeding-tag">⚠ Bleeding</span>' : '';
  const noShowTag = a.no_show ? '<span class="appt-noshow-tag">No-Show</span>' : '';
  const notes = a.clinical_notes ? `<div class="appt-notes">${escapeHtml(a.clinical_notes)}</div>` : '';
  const labParts = [];
  if (a.on_admission_hb) labParts.push(`Hb ${escapeHtml(a.on_admission_hb)}`);
  if (a.platelet) labParts.push(`Plt ${escapeHtml(a.platelet)}`);
  if (a.inr) labParts.push(`INR ${escapeHtml(a.inr)}`);
  if (a.comorbs_etiology) labParts.push(escapeHtml(a.comorbs_etiology));
  const labs = labParts.length ? `<div class="appt-labs">${labParts.join(' · ')}</div>` : '';
  const overrideTag = a.is_override ? ' · <strong>override</strong>' : '';
  const mrnPart = a.mrn ? ` · MRN ${escapeHtml(a.mrn)}` : '';
  const referralPart = a.referral ? ` · Ref: ${escapeHtml(a.referral)}` : '';

  const manage = canManage(a);
  const locked = isTimeLocked(a);
  const canEdit = manage && !(ME && isSchedulerLikeRole(ME.role) && locked && !hasFullAccess(ME));
  const canDelete = manage && (hasFullAccess(ME) || !locked);

  const manageButtons = [];
  if (canEdit) manageButtons.push(`<button class="appt-cancel" onclick="openBookingModalForEdit(${a.id})">edit</button>`);
  if (canEdit) manageButtons.push(`<button class="appt-cancel" onclick="openRescheduleModal(${a.id})">reschedule</button>`);
  if (canDelete) manageButtons.push(`<button class="appt-cancel" onclick="cancelAppointment(${a.id})">cancel</button>`);
  if (manage && !canEdit && !canDelete) manageButtons.push('<span class="appt-locked-note">locked</span>');

  // No-show toggle is available to every role, unconditionally.
  manageButtons.push(`<button class="appt-cancel" onclick="toggleNoShow(${a.id})">${a.no_show ? 'unmark no-show' : 'mark no-show'}</button>`);
  if (a.procedure_type === 'ercp' && ME && ['admin', 'specialist', 'nurse_manager'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/ercp/${a.id}">📋 Open Report</a>`);
  }
  // Phase 4: Endoscopic Dilatation Module — same role gate as ERCP reports
  // (CAN_ACCESS_DILATATION_REPORTS is the same role tuple server-side).
  if (['dilatation', 'balloon_dilatation', 'esophageal_dilatation'].includes(a.procedure_type) && ME && ['admin', 'specialist', 'nurse_manager'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/dilatation/${a.id}">📋 Open Report</a>`);
  }
  if (a.procedure_type === 'upper_gi' && ME && ['admin', 'specialist', 'nurse_manager', 'registrar', 'general_endoscopy', 'pg_trainee'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/upper-gi/${a.id}">📋 EGD Report</a>`);
  }
  if (a.procedure_type === 'colonoscopy' && ME && ['admin', 'specialist', 'nurse_manager', 'registrar', 'general_endoscopy', 'pg_trainee'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/colonoscopy/${a.id}">📋 Colonoscopy Report</a>`);
  }
  if (a.procedure_type === 'peg_tube' && ME && ['admin', 'specialist', 'nurse_manager', 'registrar', 'general_endoscopy', 'pg_trainee'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/upper-gi/${a.id}">📋 PEG / EGD Report</a>`);
  }
  if (a.procedure_type === 'polypectomy' && ME && ['admin', 'specialist', 'nurse_manager', 'registrar', 'general_endoscopy', 'pg_trainee'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/colonoscopy/${a.id}">📋 Polypectomy / Col Report</a>`);
  }
  if (a.procedure_type === 'eus' && ME && ['admin', 'specialist', 'nurse_manager', 'consultant', 'hod'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/eus/${a.id}">📋 Open Report</a>`);
  }
  if (a.procedure_type === 'capsule_endoscopy' && ME && ['admin', 'specialist', 'nurse_manager', 'consultant', 'hod'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="/capsule-endoscopy/${a.id}">📋 Open Report</a>`);
  }
  const ADVANCED_REPORT_ROUTES = {
    sigmoidoscopy: '/sigmoidoscopy/',
    proctoscopy: '/proctoscopy/',
    enteroscopy: '/enteroscopy/',
    emr: '/emr/',
    esd: '/esd/',
    variceal_band_ligation: '/variceal-band-ligation/',
    sclerotherapy: '/sclerotherapy/',
    stent_placement: '/stent-placement/',
    liver_biopsy: '/liver-biopsy/',
  };
  if (ADVANCED_REPORT_ROUTES[a.procedure_type] && ME && ['admin', 'specialist', 'nurse_manager', 'consultant', 'hod'].includes(ME.role)) {
    manageButtons.push(`<a class="appt-cancel" href="${ADVANCED_REPORT_ROUTES[a.procedure_type]}${a.id}">📋 Open Report</a>`);
  }
  const actions = manageButtons.join(' · ');

  const COLUMN_TYPES = new Set(['upper_gi', 'colonoscopy', 'peg_tube', 'ercp']);
  const procLabel = a.procedure_label || a.procedure_type;
  const nameHtml = COLUMN_TYPES.has(a.procedure_type)
    ? escapeHtml(a.patient_name)
    : `${escapeHtml(a.patient_name)} <span class="appt-procedure">— ${escapeHtml(procLabel)}</span>`;

  return `
    <div class="appt-card ${a.is_bleeding ? 'is-bleeding' : ''} ${a.no_show ? 'is-no-show' : ''}" data-id="${a.id}">
      <div class="appt-card-top">
        <span class="appt-name">${nameHtml}</span>
        ${bleedTag}${noShowTag}
      </div>
      <div class="appt-meta">
        <span>${escapeHtml(a.gender)} / ${a.age}y</span>
        <span>${escapeHtml(a.phone)}${mrnPart}${referralPart}</span>
      </div>
      ${notes}
      ${labs}
      <div class="appt-audit">
        Booked by: ${escapeHtml(a.booked_by_username)} (${escapeHtml(a.booked_by_role)})${overrideTag}
        ${actions ? ' · ' + actions : ''}
      </div>
    </div>`;
}

async function cancelAppointment(id) {
  if (!confirm('Cancel this booking?')) return;
  try {
    await api(`/api/appointment/${id}`, { method: 'DELETE' });
    if (typeof refreshCurrentView === 'function') refreshCurrentView();
  } catch (e) {
    alert(e.message);
  }
}

async function toggleNoShow(id) {
  try {
    await api(`/api/appointment/${id}/no-show`, { method: 'POST' });
    if (typeof refreshCurrentView === 'function') refreshCurrentView();
  } catch (e) {
    alert(e.message);
  }
}

function showWarningBanner(text) {
  const el = document.getElementById('warningBanner');
  if (!el) return;
  el.textContent = '⚠ ' + text;
  el.hidden = false;
}

function showAlertPopup(message) {
  const popup = document.getElementById('alertPopup');
  const msgEl = document.getElementById('alertPopupMessage');
  if (!popup || !msgEl) { alert(message); return; }
  msgEl.textContent = message;
  popup.hidden = false;
}

function hideAlertPopup() {
  const popup = document.getElementById('alertPopup');
  if (popup) popup.hidden = true;
}

// ==================================================================
// SHARED BOOKING MODAL (used by both the dashboard and calendar pages)
// ==================================================================
let refreshCurrentView = null; // set by whichever page initializes the modal

function initBookingModal(onSaved) {
  const modalEl = document.getElementById('bookingModal');
  if (!modalEl) return;

  refreshCurrentView = onSaved;

  const defaultDate = modalEl.dataset.defaultDate;
  const canOverride = modalEl.dataset.canOverride === 'true';
  const canErcp = modalEl.dataset.canErcp === 'true';
  const canSpecial = modalEl.dataset.canSpecial === 'true';

  const form = document.getElementById('bookingForm');
  const modalTitle = document.getElementById('bookingModalTitle');
  const submitBtn = document.getElementById('bookingSubmitBtn');
  const apptIdField = document.getElementById('apptIdField');
  const procedureSelect = document.getElementById('procedureType');
  const apptDate = document.getElementById('apptDate');
  const overrideRow = document.getElementById('overrideRow');
  const formError = document.getElementById('formError');
  const dateWarningEl = document.getElementById('dateRestrictionWarning');

  apptDate.value = defaultDate;

  const ercpOpt = document.getElementById('ercpOption');
  const dilOpt = document.getElementById('dilatationOption');
  const polOpt = document.getElementById('polypectomyOption');
  const advancedGroup = document.getElementById('advancedGroup');
  if (!canErcp) {
    if (ercpOpt) ercpOpt.remove();
    if (advancedGroup) advancedGroup.remove();
  }
  if (!canSpecial) {
    if (dilOpt) dilOpt.remove();
    if (polOpt) polOpt.remove();
  }
  if (canOverride) overrideRow.hidden = false;

  function syncErcpAvailability() {
    const opt = document.getElementById('ercpOption');
    if (!opt) return;
    const eligible = isErcpEligible(apptDate.value);
    opt.disabled = !eligible;
    if (!eligible && procedureSelect.value === 'ercp') {
      procedureSelect.value = 'upper_gi';
    }
  }

  async function syncDateRestriction() {
    if (ME && canOverride) {
      dateWarningEl.hidden = true;
      submitBtn.disabled = false;
      return;
    }
    try {
      const info = await api(`/api/day/${apptDate.value}`);
      if (info.is_sunday || info.holiday_name) {
        dateWarningEl.textContent = info.holiday_name
          ? `🚫 ${info.holiday_name} — only Admin/Specialist accounts can book on this date.`
          : `🚫 Sunday — only Admin/Specialist accounts can book on this date.`;
        dateWarningEl.hidden = false;
        submitBtn.disabled = true;
      } else {
        dateWarningEl.hidden = true;
        submitBtn.disabled = false;
      }
    } catch (e) {
      dateWarningEl.hidden = true;
      submitBtn.disabled = false;
    }
  }

  apptDate.addEventListener('change', () => { syncErcpAvailability(); syncDateRestriction(); });
  syncErcpAvailability();
  syncDateRestriction();

  function resetToNewMode(dateStr) {
    form.reset();
    apptIdField.value = '';
    apptDate.value = dateStr || defaultDate;
    modalTitle.textContent = 'New Booking';
    submitBtn.textContent = 'Confirm Booking';
    formError.hidden = true;
    syncErcpAvailability();
    syncDateRestriction();
  }

  window.openBookingModalForNew = function (dateStr) {
    resetToNewMode(dateStr);
    modalEl.hidden = false;
  };

  window.openBookingModalForEdit = function (apptId) {
    const appt = APPT_CACHE[apptId];
    if (!appt) { alert('Could not find that booking — try refreshing.'); return; }
    if (ME && isSchedulerLikeRole(ME.role) && isTimeLocked(appt)) {
      alert('Scheduler/Endoscopy Staff accounts can no longer edit this booking — the appointment day has arrived or 48 hours have passed since it was booked.');
      return;
    }
    form.reset();
    apptIdField.value = appt.id;
    form.procedure_type.value = appt.procedure_type;
    form.appointment_date.value = appt.appointment_date;
    form.patient_name.value = appt.patient_name;
    form.gender.value = appt.gender;
    form.age.value = appt.age;
    form.phone.value = appt.phone;
    form.mrn.value = appt.mrn || '';
    form.clinical_notes.value = appt.clinical_notes || '';
    form.on_admission_hb.value = appt.on_admission_hb || '';
    form.platelet.value = appt.platelet || '';
    form.inr.value = appt.inr || '';
    form.total_bilirubin.value = appt.total_bilirubin || '';
    form.ggt.value = appt.ggt || '';
    form.alp.value = appt.alp || '';
    form.tlc.value = appt.tlc || '';
    form.alt.value = appt.alt || '';
    form.us_findings.value = appt.us_findings || '';
    form.mrcp_findings.value = appt.mrcp_findings || '';
    form.previous_labs.value = appt.previous_labs || '';
    form.comorbs_etiology.value = appt.comorbs_etiology || '';
    form.referral.value = appt.referral || '';
    form.is_bleeding.checked = !!appt.is_bleeding;
    if (form.is_override) form.is_override.checked = !!appt.is_override;
    modalTitle.textContent = 'Edit Booking';
    submitBtn.textContent = 'Save Changes';
    formError.hidden = true;
    syncErcpAvailability();
    syncDateRestriction();
    modalEl.hidden = false;
  };

  document.getElementById('openBookingBtn').addEventListener('click', () => window.openBookingModalForNew());
  document.getElementById('closeBookingBtn').addEventListener('click', () => { modalEl.hidden = true; });
  document.getElementById('cancelBookingBtn').addEventListener('click', () => { modalEl.hidden = true; });

  ['f_followup_eckardt_dysphagia', 'f_followup_eckardt_regurgitation', 'f_followup_eckardt_chest_pain', 'f_followup_eckardt_weight_loss'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', syncFollowupEckardtTotal);
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    formError.hidden = true;
    const fd = new FormData(form);
    const payload = {
      procedure_type: fd.get('procedure_type'),
      appointment_date: fd.get('appointment_date'),
      patient_name: fd.get('patient_name'),
      gender: fd.get('gender'),
      age: fd.get('age'),
      phone: fd.get('phone'),
      mrn: fd.get('mrn'),
      clinical_notes: fd.get('clinical_notes'),
      on_admission_hb: fd.get('on_admission_hb'),
      platelet: fd.get('platelet'),
      inr: fd.get('inr'),
      total_bilirubin: fd.get('total_bilirubin'),
      ggt: fd.get('ggt'),
      alp: fd.get('alp'),
      tlc: fd.get('tlc'),
      alt: fd.get('alt'),
      us_findings: fd.get('us_findings'),
      mrcp_findings: fd.get('mrcp_findings'),
      previous_labs: fd.get('previous_labs'),
      comorbs_etiology: fd.get('comorbs_etiology'),
      referral: fd.get('referral'),
      is_bleeding: fd.get('is_bleeding') === 'on',
      is_override: fd.get('is_override') === 'on',
    };
    const editId = fd.get('appt_id');
    try {
      const result = editId
        ? await api(`/api/appointment/${editId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          })
        : await api('/api/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
      modalEl.hidden = true;
      resetToNewMode();
      if (result.warning) showWarningBanner(result.warning);
      if (refreshCurrentView) refreshCurrentView();
    } catch (err) {
      showAlertPopup(err.message);
    }
  });
}

// ==================================================================
// RESCHEDULE MODAL — change just the date, all other data carries over
// ==================================================================
function initRescheduleModal(onSaved) {
  const modalEl = document.getElementById('rescheduleModal');
  if (!modalEl) return;

  const form = document.getElementById('rescheduleForm');
  const apptIdField = document.getElementById('rescheduleApptId');
  const dateField = document.getElementById('rescheduleDateField');
  const infoEl = document.getElementById('reschedulePatientInfo');
  const errorEl = document.getElementById('rescheduleError');

  window.openRescheduleModal = function (apptId) {
    const appt = APPT_CACHE[apptId];
    if (!appt) { alert('Could not find that booking — try refreshing.'); return; }
    if (ME && isSchedulerLikeRole(ME.role) && isTimeLocked(appt)) {
      alert('Scheduler/Endoscopy Staff accounts can no longer modify this booking — the appointment day has arrived or 48 hours have passed since it was booked.');
      return;
    }
    apptIdField.value = appt.id;
    dateField.value = appt.appointment_date;
    const procLabel = appt.procedure_label || appt.procedure_type;
    infoEl.textContent = `${appt.patient_name} — ${procLabel} (currently ${appt.appointment_date})`;
    errorEl.hidden = true;
    modalEl.hidden = false;
  };

  document.getElementById('closeRescheduleBtn').addEventListener('click', () => { modalEl.hidden = true; });
  document.getElementById('cancelRescheduleBtn').addEventListener('click', () => { modalEl.hidden = true; });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    const id = apptIdField.value;
    const appt = APPT_CACHE[id];
    if (!appt) return;

    const payload = {
      procedure_type: appt.procedure_type,
      appointment_date: dateField.value,
      patient_name: appt.patient_name,
      gender: appt.gender,
      age: appt.age,
      phone: appt.phone,
      mrn: appt.mrn,
      clinical_notes: appt.clinical_notes,
      on_admission_hb: appt.on_admission_hb,
      platelet: appt.platelet,
      inr: appt.inr,
      total_bilirubin: appt.total_bilirubin,
      ggt: appt.ggt,
      alp: appt.alp,
      tlc: appt.tlc,
      alt: appt.alt,
      us_findings: appt.us_findings,
      mrcp_findings: appt.mrcp_findings,
      previous_labs: appt.previous_labs,
      comorbs_etiology: appt.comorbs_etiology,
      referral: appt.referral,
      is_bleeding: appt.is_bleeding,
      is_override: false, // reschedule always re-validates fresh against the new date's capacity
    };

    try {
      const result = await api(`/api/appointment/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      modalEl.hidden = true;
      if (result.warning) showWarningBanner(result.warning);
      if (onSaved) onSaved();
    } catch (err) {
      showAlertPopup(err.message);
    }
  });
}

// ==================================================================
// SCHEDULE REPEAT ERCP MODAL (shared by ercp_report.html and
// patient_ercp_overview.html)
// ==================================================================
function initRepeatErcpModal() {
  const modalEl = document.getElementById('repeatErcpModal');
  if (!modalEl) return;

  const form = document.getElementById('repeatErcpForm');
  const apptIdField = document.getElementById('repeatSourceApptId');
  const dateField = document.getElementById('repeatErcpDateField');
  const infoEl = document.getElementById('repeatErcpPatientInfo');
  const errorEl = document.getElementById('repeatErcpError');

  window.openRepeatErcpModal = function (apptId, patientLabel) {
    apptIdField.value = apptId;
    dateField.value = '';
    infoEl.textContent = patientLabel || '';
    errorEl.hidden = true;
    modalEl.hidden = false;
  };

  document.getElementById('closeRepeatErcpBtn').addEventListener('click', () => { modalEl.hidden = true; });
  document.getElementById('cancelRepeatErcpBtn').addEventListener('click', () => { modalEl.hidden = true; });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    if (!isErcpEligible(dateField.value)) {
      errorEl.textContent = 'ERCP can only be scheduled on Tuesdays or Saturdays.';
      errorEl.hidden = false;
      return;
    }
    try {
      const result = await api(`/api/appointment/${apptIdField.value}/repeat-ercp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appointment_date: dateField.value }),
      });
      modalEl.hidden = true;
      // The overview page recomputes all sessions fresh from the DB (by
      // MRN) on every load, so a full reload is enough to show the new
      // session — no client-side state to reconcile.
      if (result.appointment) {
        window.location.href = `/patient-overview/${result.appointment.repeat_of_appointment_id}`;
      } else {
        window.location.reload();
      }
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    }
  });
}

// ==================================================================
// FOLLOW-UP MODULE (shared by ercp_report.html/patient_ercp_overview.html
// AND, since Phase 4, dilatation_report.html/dilatation_patient_overview.html
// — one timeline per report). The endpoint URLs are procedure-specific, so
// they're parameterized via window.FOLLOWUP_ENDPOINTS (set once per page
// with setFollowupEndpoints()) rather than hardcoded — this default is
// ERCP's original endpoints, so any page that never calls
// setFollowupEndpoints() (i.e. every existing ERCP page) behaves exactly
// as before.
// ==================================================================
const ERCP_FOLLOWUP_ENDPOINTS = {
  list: (reportId) => `/api/ercp/${reportId}/followups`,
  item: (followupId) => `/api/followup/${followupId}`,
};
window.FOLLOWUP_ENDPOINTS = window.FOLLOWUP_ENDPOINTS || ERCP_FOLLOWUP_ENDPOINTS;

function setFollowupEndpoints(endpoints) {
  window.FOLLOWUP_ENDPOINTS = endpoints;
}

const FOLLOWUP_CACHE = {};
window.FOLLOWUP_REPORT_IDS = window.FOLLOWUP_REPORT_IDS || [];

function followupTimelineHTML(followups) {
  if (!followups.length) return '<p class="muted">No follow-up records yet.</p>';
  return followups.map(f => {
    FOLLOWUP_CACHE[f.id] = f;
    const statusTag = f.clinical_status ? `<span class="followup-tag">${escapeHtml(f.clinical_status)}</span>` : '';
    const outcomeTag = f.outcome ? `<span class="followup-tag followup-tag--outcome">${escapeHtml(f.outcome)}</span>` : '';
    const rows = [
      ['Clinical Notes', f.clinical_notes],
      ['Histopathology / Biopsy', f.histopathology_result],
      ['Laboratory Results', f.lab_results],
      ['Imaging Results', f.imaging_results],
      ['Management / Plan', f.management_plan],
      ['Notes', f.free_notes],
      ['Eckardt Score', f.followup_eckardt_total ? `${f.followup_eckardt_total} / 12` : ''],
    ].filter(([, v]) => v && v.trim());
    const rowsHtml = rows.map(([label, v]) => `<p class="followup-field"><strong>${label}:</strong> ${escapeHtml(v)}</p>`).join('');
    return `
      <div class="timeline-item timeline-item--followup">
        <div class="timeline-dot timeline-dot--followup"></div>
        <div class="timeline-card timeline-card--followup">
          <div class="timeline-card-head">
            <span class="timeline-date">${escapeHtml(f.followup_date)}</span>
            ${statusTag}${outcomeTag}
            <span class="timeline-actions no-print">
              <button class="appt-cancel" onclick="openFollowupModalForEdit(${f.id})">edit</button>
              <button class="appt-cancel" onclick="deleteFollowup(${f.id})">delete</button>
            </span>
          </div>
          ${rowsHtml || '<p class="muted">No additional details recorded.</p>'}
        </div>
      </div>`;
  }).join('');
}

async function loadFollowupTimeline(reportId) {
  const container = document.getElementById(`followupTimeline-${reportId}`);
  if (!container) return;
  try {
    const data = await api(window.FOLLOWUP_ENDPOINTS.list(reportId));
    container.innerHTML = followupTimelineHTML(data.followups);
  } catch (err) {
    container.innerHTML = `<p class="form-error">${escapeHtml(err.message)}</p>`;
  }
}

function registerFollowupTimeline(reportId) {
  if (!window.FOLLOWUP_REPORT_IDS.includes(reportId)) window.FOLLOWUP_REPORT_IDS.push(reportId);
  loadFollowupTimeline(reportId);
}

function refreshAllFollowupTimelines() {
  window.FOLLOWUP_REPORT_IDS.forEach(id => loadFollowupTimeline(id));
}

async function deleteFollowup(followupId) {
  if (!confirm('Delete this follow-up record?')) return;
  try {
    await api(window.FOLLOWUP_ENDPOINTS.item(followupId), { method: 'DELETE' });
    refreshAllFollowupTimelines();
  } catch (err) {
    alert(err.message);
  }
}

// ==================================================================
// UNSAVED CHANGES GUARD (shared by ercp_report.html and
// dilatation_report.html). Two layers:
//  1. Browser-level navigation (tab close, refresh, typing a new URL) can
//     only trigger the browser's own generic "leave site?" dialog via
//     beforeunload — its text and buttons are controlled by the browser,
//     not customizable, that's a browser security restriction.
//  2. In-app link clicks (nav bar, "Open Report" links, etc.) are under
//     our control, so those show a custom modal with real Save Draft /
//     Discard / Cancel choices before navigating away.
// ==================================================================
function initUnsavedChangesGuard(fieldsetSelector, saveFn) {
  const fieldset = document.querySelector(fieldsetSelector);
  const modalEl = document.getElementById('leaveConfirmModal');
  if (!fieldset || !modalEl) return;

  let isDirty = false;
  let pendingHref = null;

  fieldset.addEventListener('input', () => { isDirty = true; });
  fieldset.addEventListener('change', () => { isDirty = true; });

  window.markReportSaved = function () { isDirty = false; };

  window.addEventListener('beforeunload', (e) => {
    if (!isDirty) return;
    e.preventDefault();
    e.returnValue = '';
  });

  document.addEventListener('click', function (e) {
    const link = e.target.closest('a[href]');
    if (!link || !isDirty) return;
    if (link.target === '_blank') return; // e.g. "Print Report" opens a new tab — don't block that
    e.preventDefault();
    pendingHref = link.href;
    modalEl.hidden = false;
  }, true);

  const saveBtn = document.getElementById('leaveSaveBtn');
  const discardBtn = document.getElementById('leaveDiscardBtn');
  const cancelBtn = document.getElementById('leaveCancelBtn');

  if (saveBtn) saveBtn.addEventListener('click', async () => {
    const ok = await saveFn(true);
    if (ok) {
      isDirty = false;
      modalEl.hidden = true;
      if (pendingHref) window.location.href = pendingHref;
    } else {
      modalEl.hidden = true;
    }
  });
  if (discardBtn) discardBtn.addEventListener('click', () => {
    isDirty = false;
    modalEl.hidden = true;
    if (pendingHref) window.location.href = pendingHref;
  });
  if (cancelBtn) cancelBtn.addEventListener('click', () => {
    modalEl.hidden = true;
    pendingHref = null;
  });
}

function initFollowupModal(onSaved) {
  const modalEl = document.getElementById('followupModal');
  if (!modalEl) return;

  const form = document.getElementById('followupForm');
  const reportIdField = document.getElementById('followupReportId');
  const followupIdField = document.getElementById('followupId');
  const modalTitle = document.getElementById('followupModalTitle');
  const errorEl = document.getElementById('followupError');
  const submitBtn = document.getElementById('followupSubmitBtn');

  function isAchalasiaFollowupReport(reportId) {
    const ids = window.DILATATION_ACHALASIA_REPORT_IDS || [];
    return ids.map(String).includes(String(reportId));
  }

  function syncAchalasiaFollowupVisibility(reportId) {
    const section = document.getElementById('achalasiaFollowupSection');
    if (section) section.hidden = !isAchalasiaFollowupReport(reportId);
  }

  function resetForm() {
    form.reset();
    followupIdField.value = '';
    modalTitle.textContent = 'Add Follow-up';
    submitBtn.textContent = 'Save Follow-up';
    errorEl.hidden = true;
    const achalasiaSection = document.getElementById('achalasiaFollowupSection');
    if (achalasiaSection) achalasiaSection.hidden = true;
    const scoreTotal = document.getElementById('f_followup_eckardt_total');
    if (scoreTotal) scoreTotal.value = 'Not calculated';
  }

  function syncFollowupEckardtTotal() {
    const ids = ['f_followup_eckardt_dysphagia', 'f_followup_eckardt_regurgitation', 'f_followup_eckardt_chest_pain', 'f_followup_eckardt_weight_loss'];
    const total = document.getElementById('f_followup_eckardt_total');
    if (!total) return;
    const values = ids.map(id => document.getElementById(id)?.value || '');
    total.value = values.some(v => v === '') ? 'Not calculated' : `${values.reduce((sum, v) => sum + Number(v), 0)} / 12`;
  }

  window.openFollowupModalForNew = function (reportId) {
    resetForm();
    reportIdField.value = reportId;
    syncAchalasiaFollowupVisibility(reportId);
    modalEl.hidden = false;
  };

  window.openFollowupModalForEdit = function (followupId) {
    const f = FOLLOWUP_CACHE[followupId];
    if (!f) { alert('Could not find that follow-up record — try refreshing.'); return; }
    resetForm();
    followupIdField.value = f.id;
    reportIdField.value = f.report_id;
    syncAchalasiaFollowupVisibility(f.report_id);
    document.getElementById('f_followup_date').value = f.followup_date;
    document.getElementById('f_followup_clinical_status').value = f.clinical_status || '';
    document.getElementById('f_followup_outcome').value = f.outcome || '';
    document.getElementById('f_followup_clinical_notes').value = f.clinical_notes || '';
    document.getElementById('f_followup_histopathology').value = f.histopathology_result || '';
    document.getElementById('f_followup_labs').value = f.lab_results || '';
    document.getElementById('f_followup_imaging').value = f.imaging_results || '';
    document.getElementById('f_followup_management').value = f.management_plan || '';
    document.getElementById('f_followup_free_notes').value = f.free_notes || '';
    document.getElementById('f_followup_eckardt_dysphagia').value = f.followup_eckardt_dysphagia || '';
    document.getElementById('f_followup_eckardt_regurgitation').value = f.followup_eckardt_regurgitation || '';
    document.getElementById('f_followup_eckardt_chest_pain').value = f.followup_eckardt_chest_pain || '';
    document.getElementById('f_followup_eckardt_weight_loss').value = f.followup_eckardt_weight_loss || '';
    syncFollowupEckardtTotal();
    modalTitle.textContent = 'Edit Follow-up';
    submitBtn.textContent = 'Save Changes';
    modalEl.hidden = false;
  };

  document.getElementById('closeFollowupBtn').addEventListener('click', () => { modalEl.hidden = true; });
  document.getElementById('cancelFollowupBtn').addEventListener('click', () => { modalEl.hidden = true; });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    const payload = {
      followup_date: document.getElementById('f_followup_date').value,
      clinical_status: document.getElementById('f_followup_clinical_status').value,
      outcome: document.getElementById('f_followup_outcome').value,
      clinical_notes: document.getElementById('f_followup_clinical_notes').value,
      histopathology_result: document.getElementById('f_followup_histopathology').value,
      lab_results: document.getElementById('f_followup_labs').value,
      imaging_results: document.getElementById('f_followup_imaging').value,
      management_plan: document.getElementById('f_followup_management').value,
      free_notes: document.getElementById('f_followup_free_notes').value,
      followup_eckardt_dysphagia: document.getElementById('f_followup_eckardt_dysphagia')?.value || '',
      followup_eckardt_regurgitation: document.getElementById('f_followup_eckardt_regurgitation')?.value || '',
      followup_eckardt_chest_pain: document.getElementById('f_followup_eckardt_chest_pain')?.value || '',
      followup_eckardt_weight_loss: document.getElementById('f_followup_eckardt_weight_loss')?.value || '',
    };
    const reportId = reportIdField.value;
    const followupId = followupIdField.value;
    try {
      followupId
        ? await api(window.FOLLOWUP_ENDPOINTS.item(followupId), {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
          })
        : await api(window.FOLLOWUP_ENDPOINTS.list(reportId), {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
          });
      modalEl.hidden = true;
      if (onSaved) onSaved();
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    }
  });
}

// ==================================================================
// DASHBOARD
// ==================================================================
function initDashboard() {
  const dash = document.querySelector('.dash');
  const today = dash.dataset.today;

  async function refresh() {
    const data = await api(`/api/day/${today}`);
    renderDashboardData(data);
  }

  loadMe().then(() => {
    initBookingModal(refresh);
    initRescheduleModal(refresh);
    refresh();
  });
}

function renderDashboardData(data) {
  const groups = { upper_gi: [], colonoscopy: [], peg_tube: [], ercp: [], special: [] };
  data.appointments.forEach(a => {
    if (a.procedure_type === 'upper_gi') groups.upper_gi.push(a);
    else if (a.procedure_type === 'colonoscopy') groups.colonoscopy.push(a);
    else if (a.procedure_type === 'peg_tube') groups.peg_tube.push(a);
    else if (a.procedure_type === 'ercp') groups.ercp.push(a);
    else groups.special.push(a);
  });

  const renderList = (id, countId, items) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = items.length
      ? items.map(apptCardHTML).join('')
      : '<div class="appt-empty">No cases booked.</div>';
    const countEl = document.getElementById(countId);
    if (countEl) countEl.textContent = `(${items.length})`;
  };
  renderList('listUpperGi', 'countUpperGi', groups.upper_gi);
  renderList('listColonoscopy', 'countColonoscopy', groups.colonoscopy);
  renderList('listPeg', 'countPeg', groups.peg_tube);
  renderList('listErcp', 'countErcp', groups.ercp);
  renderList('listSpecial', 'countSpecial', groups.special);

  const capEl = document.getElementById('capSummary');
  if (capEl) {
    const ugiCls = data.counts.upper_gi >= data.caps.global_upper_gi ? 'chip--full'
                 : data.counts.upper_gi >= data.caps.global_upper_gi * 0.6 ? 'chip--high' : '';
    const colCls = data.counts.colonoscopy >= data.caps.global_colono ? 'chip--full'
                 : data.counts.colonoscopy >= data.caps.global_colono * 0.6 ? 'chip--high' : '';
    const pegCls = data.counts.peg_tube >= data.caps.global_peg ? 'chip--full'
                 : data.counts.peg_tube >= data.caps.global_peg * 0.6 ? 'chip--high' : '';
    capEl.innerHTML = `
      <span class="cap-chip ${ugiCls}">UGI ${data.counts.upper_gi}/${data.caps.global_upper_gi}</span>
      <span class="cap-chip ${colCls}">Colono ${data.counts.colonoscopy}/${data.caps.global_colono}</span>
      <span class="cap-chip ${pegCls}">PEG ${data.counts.peg_tube}/${data.caps.global_peg}</span>
    `;
  }

  const warnEl = document.getElementById('warningBanner');
  if (warnEl) {
    if (data.counts.regular_total > data.warning_threshold) {
      warnEl.textContent = `⚠ Regular case list exceeds ${data.warning_threshold} cases (currently ${data.counts.regular_total}).`;
      warnEl.hidden = false;
    } else {
      warnEl.hidden = true;
    }
  }
}

// ==================================================================
// CALENDAR
// ==================================================================
let calYear, calMonth, currentOpenDate = null;

function initCalendar() {
  const now = new Date();
  calYear = now.getFullYear();
  calMonth = now.getMonth() + 1;

  document.getElementById('prevMonthBtn').addEventListener('click', () => shiftMonth(-1));
  document.getElementById('nextMonthBtn').addEventListener('click', () => shiftMonth(1));
  document.getElementById('closeDayModalBtn').addEventListener('click', () => {
    document.getElementById('dayModal').hidden = true;
    currentOpenDate = null;
  });

  async function refresh() {
    if (currentOpenDate) await openDayModal(currentOpenDate);
    await renderCalendar();
  }

  loadMe().then(() => {
    initBookingModal(refresh);
    initRescheduleModal(refresh);
    renderCalendar();
  });
}

function shiftMonth(delta) {
  calMonth += delta;
  if (calMonth > 12) { calMonth = 1; calYear++; }
  if (calMonth < 1) { calMonth = 12; calYear--; }
  renderCalendar();
}

async function renderCalendar() {
  const label = new Date(calYear, calMonth - 1, 1).toLocaleString('default', { month: 'long', year: 'numeric' });
  document.getElementById('calMonthLabel').textContent = label;

  const data = await api(`/api/month-summary?year=${calYear}&month=${calMonth}`);
  const grid = document.getElementById('calGrid');
  grid.innerHTML = '';

  ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(d => {
    const el = document.createElement('div');
    el.className = 'cal-dow';
    el.textContent = d;
    grid.appendChild(el);
  });

  const firstDay = new Date(calYear, calMonth - 1, 1);
  const startOffset = firstDay.getDay();
  for (let i = 0; i < startOffset; i++) {
    const el = document.createElement('div');
    el.className = 'cal-cell empty';
    grid.appendChild(el);
  }

  const daysInMonth = new Date(calYear, calMonth, 0).getDate();
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${calYear}-${String(calMonth).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
    const info = data[dateStr] || { status: 'green', upper_gi: 0, colonoscopy: 0, peg_tube: 0, ercp: 0, is_ercp_day: false, is_sunday: false, holiday_name: null };
    const cell = document.createElement('div');
    const isHoliday = !!(info.holiday_name || info.is_sunday);
    cell.className = `cal-cell status-${info.status} ${info.is_ercp_day ? 'is-saturday' : ''} ${isHoliday ? 'is-holiday' : ''}`;
    if (info.holiday_name) {
      cell.title = info.holiday_name;
    } else if (info.is_sunday) {
      cell.title = 'Sunday — booking restricted to Admin/Specialist';
    }
    const holidayBadge = isHoliday ? `<div class="cal-holiday-badge">🚫${info.holiday_name ? ' ' + escapeHtml(info.holiday_name) : ''}</div>` : '';
    cell.innerHTML = `
      <div class="cal-daynum">${day}</div>
      ${holidayBadge}
      <div class="cal-cell-counts">UGI ${info.upper_gi} · Col ${info.colonoscopy}${info.peg_tube ? ' · PEG ' + info.peg_tube : ''}${info.ercp ? ' · ERCP ' + info.ercp : ''}</div>
    `;
    cell.addEventListener('click', () => openDayModal(dateStr));
    grid.appendChild(cell);
  }
}

async function openDayModal(dateStr) {
  currentOpenDate = dateStr;
  const data = await api(`/api/day/${dateStr}`);
  const modal = document.getElementById('dayModal');
  const title = document.getElementById('dayModalTitle');
  const body = document.getElementById('dayModalBody');

  const d = new Date(dateStr + 'T00:00:00');
  title.textContent = d.toLocaleDateString('default', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  const byType = { upper_gi: [], colonoscopy: [], peg_tube: [], ercp: [], other: [] };
  data.appointments.forEach(a => {
    if (byType[a.procedure_type]) byType[a.procedure_type].push(a);
    else byType.other.push(a);
  });

  const column = (label, colorClass, items) => `
    <div class="dash-col">
      <h2 class="col-title ${colorClass} is-collapsed" onclick="toggleColumn(this)">
        <span class="col-title-text">${label}</span>
        <span class="col-count">(${items.length})</span>
        <span class="col-arrow">▾</span>
      </h2>
      <div class="appt-list collapsed">
        ${items.length ? items.map(apptCardHTML).join('') : '<div class="appt-empty">No cases.</div>'}
      </div>
    </div>`;

  const printButtons = data.is_ercp_day
    ? `<button class="btn btn--sm btn--outline" onclick="window.open('/print/${dateStr}?only=other','_blank')">🖨 Endoscopy List</button>
       <button class="btn btn--sm btn--outline" onclick="window.open('/print/${dateStr}?only=ercp','_blank')">🖨 ERCP List</button>`
    : `<button class="btn btn--sm btn--outline" onclick="window.open('/print/${dateStr}','_blank')">🖨 Print</button>`;

  const holidayBanner = (data.holiday_name || data.is_sunday)
    ? `<div class="holiday-banner">🚫 ${data.holiday_name ? escapeHtml(data.holiday_name) : 'Sunday'} — booking on this date is restricted to Admin/Specialist accounts.</div>`
    : '';

  body.innerHTML = `
    ${holidayBanner}
    <div class="day-modal-actions">
      <p class="muted">UGI ${data.counts.upper_gi}/${data.caps.global_upper_gi} ·
         Colonoscopy ${data.counts.colonoscopy}/${data.caps.global_colono} ·
         PEG ${data.counts.peg_tube}/${data.caps.global_peg} ·
         ${data.is_ercp_day ? 'ERCP eligible (Tue/Sat)' : 'ERCP not available this day'}</p>
      <div class="day-modal-buttons">
        ${printButtons}
        <button class="btn btn--sm btn--primary" onclick="openBookingModalForNew('${dateStr}')">+ New Booking</button>
      </div>
    </div>
    <div class="day-modal-grid">
      ${column('Upper GI Endoscopy', 'col-title--green', byType.upper_gi)}
      ${column('Colonoscopy', 'col-title--blue', byType.colonoscopy)}
      ${column('PEG Tube Insertion', 'col-title--teal', byType.peg_tube)}
      ${column('ERCP', 'col-title--purple', byType.ercp)}
      ${column('Special Cases', 'col-title--amber', byType.other)}
    </div>
  `;
  modal.hidden = false;
}

// ==================================================================
// ERCP REPORT EDITOR
// ==================================================================
function initErcpReport() {
  const page = document.querySelector('.ercp-page');
  if (!page) return;
  const reportId = page.dataset.reportId;
  const locked = page.dataset.locked === 'true';

  function checkedValues(containerId) {
    return Array.from(document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`)).map(el => el.value);
  }

  function cholangioFindingsValues(containerId) {
    const checkboxValues = checkedValues(containerId);
    const toggleValues = Array.from(document.querySelectorAll(`#${containerId} .ercp-cholangio-toggle-opt.is-selected`))
      .map(el => el.dataset.value);
    return checkboxValues.concat(toggleValues);
  }

  function setupCholangioToggleLists(containerId) {
    document.querySelectorAll(`#${containerId} .ercp-cholangio-toggle-opt`).forEach(opt => {
      function toggle() {
        const nowSelected = !opt.classList.contains('is-selected');
        opt.classList.toggle('is-selected', nowSelected);
        opt.setAttribute('aria-selected', nowSelected ? 'true' : 'false');
        opt.dispatchEvent(new CustomEvent('cholangio-toggle', { bubbles: true }));
      }
      opt.addEventListener('click', toggle);
      opt.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
      });
    });
  }

  function gatherPayload() {
    const image_captions = {};
    document.querySelectorAll('.img-caption-input[data-slot]').forEach((input) => {
      const slot = input.dataset.slot;
      if (slot) image_captions[slot] = (input.value || '').trim();
    });
    return {
      image_captions,
      endoscopist_id: document.getElementById('f_endoscopist_id').value || null,
      sedation: document.getElementById('f_sedation').value,
      anesthesiologist: document.getElementById('f_anesthesiologist').value,
      assistants: document.getElementById('f_assistants').value,
      technician: document.getElementById('f_technician').value,
      indication: document.getElementById('f_indication').value,
      duodenoscope_advancement: document.getElementById('f_duodenoscope_advancement').value,
      papilla: document.getElementById('f_papilla').value,
      papilla_location: document.getElementById('f_papilla_location').value,
      papilla_access: document.getElementById('f_papilla_access').value,
      cannulation: document.getElementById('f_cannulation').value,
      cannulation_rescue_techniques: checkedValues('f_cannulation_rescue'),
      guidewire_used: document.getElementById('f_guidewire_used').value,
      guidewire_size: document.getElementById('f_guidewire_size').value,
      cholangiogram_findings: cholangioFindingsValues('f_cholangiogram_findings'),
      cholangio_cbd_mm: document.getElementById('f_cholangio_cbd_mm').value,
      cholangio_chd_mm: document.getElementById('f_cholangio_chd_mm').value,
      cholangio_rhd_mm: document.getElementById('f_cholangio_rhd_mm').value,
      cholangio_lhd_mm: document.getElementById('f_cholangio_lhd_mm').value,
      cholangio_largest_stone_mm: document.getElementById('f_cholangio_largest_stone_mm').value,
      cholangio_stone_count: document.getElementById('f_cholangio_stone_count').value,
      cholangio_stricture_length_mm: document.getElementById('f_cholangio_stricture_length_mm').value,
      stricture_morphology: checkedValues('f_stricture_morphology'),
      stricture_severity: document.getElementById('f_stricture_severity').value,
      stricture_appearance: document.getElementById('f_stricture_appearance').value,
      upstream_dilatation: document.getElementById('f_upstream_dilatation').value,
      bile_leak_severity: document.getElementById('f_bile_leak_severity').value,
      therapeutic_procedures: checkedValues('f_therapeutic_procedures'),
      sphincteroplasty_balloon_size_mm: document.getElementById('f_sphincteroplasty_balloon_size_mm').value,
      balloon_dilation_location: document.getElementById('f_balloon_dilation_location').value,
      balloon_dilation_size_mm: document.getElementById('f_balloon_dilation_size_mm').value,
      stent_placed: document.getElementById('f_stent_placed').value,
      stent_type: document.getElementById('f_stent_type').value,
      stent_manufacturer: document.getElementById('f_stent_manufacturer').value,
      stent_diameter: document.getElementById('f_stent_diameter').value,
      stent_length: document.getElementById('f_stent_length').value,
      stent_count: document.getElementById('f_stent_count').value,
      stent_location: document.getElementById('f_stent_location').value,
      stent_deployment: document.getElementById('f_stent_deployment').value,
      stent_drainage: document.getElementById('f_stent_drainage').value,
      stent_configuration: document.getElementById('f_stent_configuration').value,
      biopsy: document.getElementById('f_biopsy').value,
      tissue_sampling_site: document.getElementById('f_tissue_sampling_site').value,
      tissue_sampling_method: document.getElementById('f_tissue_sampling_method').value,
      cholangioscopy_performed: document.getElementById('f_cholangioscopy_performed').value,
      cholangioscopy_findings: checkedValues('f_cholangioscopy_findings'),
      stent_indication: document.getElementById('f_stent_indication').value,
      therapeutic_outcome: document.getElementById('f_therapeutic_outcome').value,
      therapeutic_incomplete_reason: document.getElementById('f_therapeutic_incomplete_reason').value,
      complications: checkedValues('f_complications'),
      procedure_note: document.getElementById('f_procedure_note').value,
      impression: document.getElementById('f_impression').value,
      recommendations: document.getElementById('f_recommendations').value,
      lab_total_bilirubin: document.getElementById('f_lab_total_bilirubin').value,
      lab_direct_bilirubin: document.getElementById('f_lab_direct_bilirubin').value,
      lab_alt: document.getElementById('f_lab_alt').value,
      lab_ast: document.getElementById('f_lab_ast').value,
      lab_alp: document.getElementById('f_lab_alp').value,
      lab_ggt: document.getElementById('f_lab_ggt').value,
      lab_albumin: document.getElementById('f_lab_albumin').value,
      lab_hb: document.getElementById('f_lab_hb').value,
      lab_wbc: document.getElementById('f_lab_wbc').value,
      lab_platelets: document.getElementById('f_lab_platelets').value,
      lab_pt: document.getElementById('f_lab_pt').value,
      lab_inr: document.getElementById('f_lab_inr').value,
      lab_creatinine: document.getElementById('f_lab_creatinine').value,
      imaging_us: document.getElementById('f_imaging_us').value,
      imaging_ct: document.getElementById('f_imaging_ct').value,
      imaging_mrcp: document.getElementById('f_imaging_mrcp').value,
      pep_nsaid_prophylaxis: document.getElementById('f_pep_nsaid_prophylaxis').value,
      pep_pd_stent_prophylaxis: document.getElementById('f_pep_pd_stent_prophylaxis').value,
      research: {
        fluoro_time_sec: document.getElementById('r_fluoro_time_sec').value,
        contrast_volume_ml: document.getElementById('r_contrast_volume_ml').value,
        stone_clearance: document.getElementById('r_stone_clearance').value,
        pd_findings: document.getElementById('r_pd_findings').value,
        pd_intervention: document.getElementById('r_pd_intervention').value,
        device_details: document.getElementById('r_device_details').value,
        procedure_duration_min: document.getElementById('r_procedure_duration_min').value,
        asa_class: document.getElementById('r_asa_class').value,
        complication_severity: document.getElementById('r_complication_severity').value,
        disposition: document.getElementById('r_disposition').value,
        followup_plan: document.getElementById('r_followup_plan').value,
        ampullary_appearance: checkedValues('r_ampullary_appearance'),
        ampullary_appearance_other: document.getElementById('r_ampullary_appearance_other').value,
        papilla_orientation: document.getElementById('r_papilla_orientation').value,
        papilla_accessibility: document.getElementById('r_papilla_accessibility').value,
        difficult_cannulation: document.getElementById('r_difficult_cannulation').value,
        time_to_cannulation_min: document.getElementById('r_time_to_cannulation_min').value,
        cannulation_attempts: document.getElementById('r_cannulation_attempts').value,
        unintentional_pd_cannulation: document.getElementById('r_unintentional_pd_cannulation').value,
      },
    };
  }

  // ---- Biliary Dilatation: live severity badge (documentation aid only —
  // the authoritative classification is computed server-side from the same
  // thresholds whenever the note is generated or the report is printed) ----
  function updateDilatationBadge() {
    const badge = document.getElementById('dilatationClassBadge');
    if (!badge) return;
    const ids = ['f_cholangio_cbd_mm', 'f_cholangio_chd_mm', 'f_cholangio_rhd_mm', 'f_cholangio_lhd_mm'];
    const values = ids
      .map(id => document.getElementById(id))
      .filter(Boolean)
      .map(el => parseFloat(el.value))
      .filter(v => !isNaN(v));
    if (!values.length) { badge.textContent = '—'; return; }
    const maxVal = Math.max(...values);
    let cls;
    if (maxVal >= 15) cls = 'Marked';
    else if (maxVal >= 10) cls = 'Moderate';
    else if (maxVal >= 7) cls = 'Mild';
    else cls = 'No dilatation';
    badge.textContent = `${cls} (max ${maxVal} mm)`;
  }

  // ---- Normal Cholangiogram auto-deselects itself if any abnormal finding
  // (checkbox, toggle-list selection, or measurement) is entered, and clears
  // abnormal findings if re-checked ----
  // ---- Stricture details: show only when an actual stricture option is selected.
  // "No stricture" must never expose the stricture-detail fields. Existing
  // saved detail values are intentionally preserved when the section is hidden.
  function setupStrictureDetailsToggle() {
    const wrap = document.getElementById('f_cholangiogram_findings');
    const details = document.getElementById('strictureDetailFields');
    if (!wrap || !details) return;

    function hasActualStricture() {
      return Array.from(wrap.querySelectorAll('.ercp-cholangio-toggle-opt.is-selected'))
        .some(opt => {
          const value = (opt.dataset.value || '').trim().toLowerCase();
          return value && value !== 'no stricture';
        });
    }

    function sync() {
      details.hidden = !hasActualStricture();
    }

    wrap.addEventListener('cholangio-toggle', sync);
    sync();
  }

  function setupNormalCholangiogramToggle() {
    const wrap = document.getElementById('f_cholangiogram_findings');
    if (!wrap) return;
    const normalCheckbox = wrap.querySelector('input[type="checkbox"][value="Normal cholangiogram"]');
    if (!normalCheckbox) return;
    const abnormalCheckboxes = Array.from(wrap.querySelectorAll('input[type="checkbox"]')).filter(cb => cb !== normalCheckbox);
    const numericFieldIds = [
      'f_cholangio_cbd_mm', 'f_cholangio_chd_mm', 'f_cholangio_rhd_mm', 'f_cholangio_lhd_mm',
      'f_cholangio_largest_stone_mm', 'f_cholangio_stone_count', 'f_cholangio_stricture_length_mm',
    ];
    const numericFields = numericFieldIds.map(id => document.getElementById(id)).filter(Boolean);

    abnormalCheckboxes.forEach(cb => cb.addEventListener('change', () => {
      if (cb.checked) normalCheckbox.checked = false;
    }));
    wrap.addEventListener('cholangio-toggle', (e) => {
      if (e.target.classList.contains('is-selected')) normalCheckbox.checked = false;
    });
    numericFields.forEach(f => f.addEventListener('input', () => {
      if (f.value.trim() !== '') normalCheckbox.checked = false;
      updateDilatationBadge();
    }));
    normalCheckbox.addEventListener('change', () => {
      if (normalCheckbox.checked) {
        abnormalCheckboxes.forEach(cb => { cb.checked = false; });
        wrap.querySelectorAll('.ercp-cholangio-toggle-opt.is-selected').forEach(opt => {
          opt.classList.remove('is-selected');
          opt.setAttribute('aria-selected', 'false');
        });
        numericFields.forEach(f => { f.value = ''; });
        updateDilatationBadge();
      }
    });
  }

  // ---- Biliary Stent Placement: show the structured detail fields only
  // when "Stent placed" is Yes ----
  function setupStentFieldsToggle() {
    const stentPlacedSelect = document.getElementById('f_stent_placed');
    const stentDetailsFields = document.getElementById('stentDetailsFields');
    if (!stentPlacedSelect || !stentDetailsFields) return;
    function sync() {
      stentDetailsFields.hidden = stentPlacedSelect.value !== 'Yes';
    }
    stentPlacedSelect.addEventListener('change', sync);
    sync();
  }

  // ---- Cholangioscopy: show visual findings only when performed ----
  function setupCholangioscopyFieldsToggle() {
    const performed = document.getElementById('f_cholangioscopy_performed');
    const findings = document.getElementById('cholangioscopyFindingsFields');
    if (!performed || !findings) return;
    function sync() { findings.hidden = performed.value !== 'Yes'; }
    performed.addEventListener('change', sync);
    sync();
  }

  // ---- Therapeutic outcome: show reason only for partial/failed/staged therapy ----
  function setupTherapeuticOutcomeFieldsToggle() {
    const outcome = document.getElementById('f_therapeutic_outcome');
    const reason = document.getElementById('therapeuticIncompleteReasonFields');
    if (!outcome || !reason) return;
    function sync() {
      reason.hidden = !['Partially successful', 'Failed', 'Staged procedure'].includes(outcome.value);
    }
    outcome.addEventListener('change', sync);
    sync();
  }

  // ---- Guidewire: show the Size field only when Guidewire Used is Yes ----
  function setupGuidewireFieldsToggle() {
    const usedSelect = document.getElementById('f_guidewire_used');
    const sizeField = document.getElementById('guidewireSizeField');
    if (!usedSelect || !sizeField) return;
    function sync() {
      sizeField.hidden = usedSelect.value !== 'Yes';
    }
    usedSelect.addEventListener('change', sync);
    sync();
  }

  // ---- Balloon Sphincteroplasty Size: show only when "Sphincteroplasty" is
  // checked under Therapeutic Procedures ----
  function setupSphincteroplastyFieldsToggle() {
    const grid = document.getElementById('f_therapeutic_procedures');
    const sizeFields = document.getElementById('sphincteroplastyFields');
    if (!grid || !sizeFields) return;
    const checkbox = Array.from(grid.querySelectorAll('input[type="checkbox"]'))
      .find(cb => cb.value === 'Sphincteroplasty');
    if (!checkbox) return;
    function sync() {
      sizeFields.hidden = !checkbox.checked;
    }
    checkbox.addEventListener('change', sync);
    sync();
  }

  // ---- Balloon Dilation location/size: show only when "Balloon dilation"
  // is checked under Therapeutic Procedures — distinct from Sphincteroplasty ----
  function setupBalloonDilationFieldsToggle() {
    const grid = document.getElementById('f_therapeutic_procedures');
    const detailFields = document.getElementById('balloonDilationFields');
    if (!grid || !detailFields) return;
    const checkbox = Array.from(grid.querySelectorAll('input[type="checkbox"]'))
      .find(cb => cb.value === 'Balloon dilation');
    if (!checkbox) return;
    function sync() {
      detailFields.hidden = !checkbox.checked;
    }
    checkbox.addEventListener('change', sync);
    sync();
  }

  async function saveReport(silent) {
    try {
      await api(`/ercp/${reportId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gatherPayload()),
      });
      if (window.markReportSaved) window.markReportSaved();
      if (!silent) {
        const notice = document.getElementById('ercpSaveNotice');
        notice.hidden = false;
        setTimeout(() => { notice.hidden = true; }, 2500);
      }
      return true;
    } catch (err) {
      showAlertPopup(err.message);
      return false;
    }
  }

  const saveBtn = document.getElementById('saveReportBtn');
  if (saveBtn) saveBtn.addEventListener('click', () => saveReport(false));

  // Print must reflect what is currently on screen. For an editable draft,
  // persist the full payload first (including image captions), then open the
  // print route. Finalized/locked reports are already persisted and can open
  // directly without an unnecessary save request.
  const printReportLink = document.getElementById('ercpPrintReportLink');
  if (printReportLink && !locked) {
    printReportLink.addEventListener('click', async (event) => {
      event.preventDefault();
      if (printReportLink.dataset.printBusy === '1') return;

      const printUrl = printReportLink.href;
      printReportLink.dataset.printBusy = '1';
      printReportLink.setAttribute('aria-busy', 'true');

      // Open a blank tab immediately so browsers do not block the popup after
      // the asynchronous save. It is navigated only after a successful save.
      const printWindow = window.open('', '_blank');
      try {
        const saved = await saveReport(true);
        if (!saved) {
          if (printWindow) printWindow.close();
          return;
        }
        if (printWindow) {
          printWindow.location.href = printUrl;
        } else {
          window.location.href = printUrl;
        }
      } finally {
        delete printReportLink.dataset.printBusy;
        printReportLink.removeAttribute('aria-busy');
      }
    });
  }

  const generateBtn = document.getElementById('generateNoteBtn');
  if (generateBtn) {
    generateBtn.addEventListener('click', async () => {
      const noteField = document.getElementById('f_procedure_note');
      if (noteField.value.trim() && !confirm('This will replace the current note text with a freshly generated draft. Continue?')) {
        return;
      }
      try {
        const payload = gatherPayload();
        const result = await api(`/ercp/${reportId}/generate-note`, {
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

  const finalizeBtn = document.getElementById('finalizeReportBtn');
  if (finalizeBtn) {
    finalizeBtn.addEventListener('click', async () => {
      if (!confirm('Finalize this report? It will become read-only — only an Admin can unlock it afterward.')) return;
      const saved = await saveReport(true);
      if (!saved) return;
      try {
        await api(`/ercp/${reportId}/finalize`, { method: 'POST' });
        window.location.reload();
      } catch (err) {
        showAlertPopup(err.message);
      }
    });
  }

  if (!locked) {
    document.querySelectorAll('.ercp-image-input').forEach(input => {
      input.addEventListener('change', async () => {
        const slot = input.dataset.slot;
        if (!input.files || !input.files[0]) return;
        const fd = new FormData();
        fd.append('image', input.files[0]);
        try {
          const res = await fetch(`/ercp/${reportId}/image/${slot}`, { method: 'POST', body: fd });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || 'Upload failed.');
          window.location.reload();
        } catch (err) {
          showAlertPopup(err.message);
        }
      });
    });
    setupCholangioToggleLists('f_cholangiogram_findings');
    setupStrictureDetailsToggle();
    setupNormalCholangiogramToggle();
    setupStentFieldsToggle();
    setupGuidewireFieldsToggle();
    setupSphincteroplastyFieldsToggle();
    setupBalloonDilationFieldsToggle();
    setupCholangioscopyFieldsToggle();
    setupTherapeuticOutcomeFieldsToggle();
    initUnsavedChangesGuard('#ercpFieldset', saveReport);
  }
  updateDilatationBadge();
}

async function ercpDeleteImage(slot) {
  const page = document.querySelector('.ercp-page');
  if (!page) return;
  const reportId = page.dataset.reportId;
  if (!confirm('Remove this image?')) return;
  try {
    await api(`/ercp/${reportId}/image/${slot}/delete`, { method: 'POST' });
    window.location.reload();
  } catch (err) {
    showAlertPopup(err.message);
  }
}

// --- Prefill booking labs from ward records (optional, never overwrites) ---
document.addEventListener('click', async (e) => {
  if (e.target && e.target.id === 'prefillWardLabsBtn') {
    const btn = e.target;
    const msg = document.getElementById('prefillWardLabsMsg');
    const mrnInput = document.getElementById('bookingMrnInput');
    const form = btn.closest('form');
    const mrn = (mrnInput && mrnInput.value || '').trim();
    if (!mrn) {
      msg.style.display = 'block';
      msg.textContent = 'Enter an MRN first, then try again.';
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Looking up…';
    try {
      const res = await fetch(`/api/patient-labs-lookup?mrn=${encodeURIComponent(mrn)}`);
      const labs = await res.json();
      const keys = Object.keys(labs || {});
      if (!keys.length) {
        msg.style.display = 'block';
        msg.textContent = 'No recent ward lab results found for this MRN.';
      } else {
        let filled = 0;
        keys.forEach((field) => {
          const el = form && form.elements[field];
          // Only fill empty fields — never overwrite something the clinician already typed.
          if (el && !el.value) {
            el.value = labs[field];
            filled += 1;
          }
        });
        msg.style.display = 'block';
        msg.textContent = filled
          ? `Filled ${filled} field(s) from the patient's ward lab history.`
          : 'Found ward labs, but every matching field already had a value — nothing overwritten.';
      }
    } catch (err) {
      msg.style.display = 'block';
      msg.textContent = 'Could not look up ward labs right now.';
    } finally {
      btn.disabled = false;
      btn.textContent = '⤓ Prefill labs from ward records';
    }
  }
});
