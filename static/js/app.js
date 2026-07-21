// ------------------------------------------------------------------
// JPMC Gastro & Endoscopy Booking — shared frontend logic
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

function canManage(appt) {
  if (!ME) return false;
  return appt.booked_by_username === ME.username || ME.can_override;
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
  const canEdit = manage && !(ME && isSchedulerLikeRole(ME.role) && locked);
  const canDelete = manage && !(ME && ME.role !== 'admin' && locked);

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
  const actions = manageButtons.join(' · ');

  return `
    <div class="appt-card ${a.is_bleeding ? 'is-bleeding' : ''} ${a.no_show ? 'is-no-show' : ''}" data-id="${a.id}">
      <div class="appt-card-top">
        <span class="appt-name">${escapeHtml(a.patient_name)}</span>
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
  if (!canErcp && ercpOpt) ercpOpt.remove();
  if (!canSpecial) { if (dilOpt) dilOpt.remove(); if (polOpt) polOpt.remove(); }
  if (canOverride) overrideRow.hidden = false;

  function isErcpEligible(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    const day = d.getDay(); // 0=Sun ... 2=Tue ... 6=Sat
    return day === 2 || day === 6;
  }

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

  // ---- Cholangiogram Findings: structured payload + "Normal" exclusivity ----
  function gatherCholangioPayload() {
    const simple = {};
    document.querySelectorAll('.ch-simple:checked').forEach(el => {
      const cat = el.dataset.category;
      if (!simple[cat]) simple[cat] = [];
      simple[cat].push(el.value);
    });
    return {
      normal: document.getElementById('ch_normal').checked,
      dilatation: {
        cbd_mm: document.getElementById('ch_dil_cbd').value,
        chd_mm: document.getElementById('ch_dil_chd').value,
        rhd_mm: document.getElementById('ch_dil_rhd').value,
        lhd_mm: document.getElementById('ch_dil_lhd').value,
      },
      filling_defects: {
        checks: Array.from(document.querySelectorAll('.ch-fd-check:checked')).map(el => el.value),
        stone_count: document.getElementById('ch_fd_count').value,
        stone_size_mm: document.getElementById('ch_fd_size').value,
      },
      strictures: {
        locations: Array.from(document.querySelectorAll('.ch-stx-loc:checked')).map(el => el.value),
        character: document.getElementById('ch_stx_character').value,
        length_mm: document.getElementById('ch_stx_length').value,
      },
      tumours: Array.from(document.querySelectorAll('.ch-tumour:checked')).map(el => el.value),
      sclerosing: {
        subtype: document.getElementById('ch_scl_subtype').value,
        features: Array.from(document.querySelectorAll('.ch-scl-feat:checked')).map(el => el.value),
      },
      simple: simple,
    };
  }

  function initCholangioNormalExclusivity() {
    const chNormal = document.getElementById('ch_normal');
    if (!chNormal) return;
    const abnormalCheckboxes = document.querySelectorAll('.ch-fd-check, .ch-stx-loc, .ch-tumour, .ch-scl-feat, .ch-simple');
    const abnormalFieldIds = ['ch_dil_cbd', 'ch_dil_chd', 'ch_dil_rhd', 'ch_dil_lhd', 'ch_fd_count', 'ch_fd_size', 'ch_stx_length'];
    const abnormalSelectIds = ['ch_stx_character', 'ch_scl_subtype'];

    chNormal.addEventListener('change', () => {
      if (!chNormal.checked) return;
      abnormalCheckboxes.forEach(el => { el.checked = false; });
      abnormalFieldIds.concat(abnormalSelectIds).forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
    });
    abnormalCheckboxes.forEach(el => {
      el.addEventListener('change', () => {
        // "No X" negative findings (e.g. "No obstruction") aren't abnormal on their own
        if (el.checked && !el.value.startsWith('No ')) chNormal.checked = false;
      });
    });
    abnormalFieldIds.concat(abnormalSelectIds).forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      const handler = () => { if (el.value) chNormal.checked = false; };
      el.addEventListener('input', handler);
      el.addEventListener('change', handler);
    });
  }

  // ---- Biliary Stent Placement: structured payload + inserted-toggle ----
  function gatherStentPayload() {
    return {
      inserted: document.getElementById('stent_inserted').value === 'yes',
      stent_type: document.getElementById('stent_type').value,
      diameter: document.getElementById('stent_diameter').value,
      length: document.getElementById('stent_length').value,
      count: document.getElementById('stent_count').value,
      deployment: document.getElementById('stent_deployment').value,
      position: document.getElementById('stent_position').value,
      drainage: document.getElementById('stent_drainage').value,
    };
  }

  function initStentInsertedToggle() {
    const sel = document.getElementById('stent_inserted');
    const fields = document.getElementById('stentDetailFields');
    if (!sel || !fields) return;
    sel.addEventListener('change', () => {
      fields.hidden = sel.value !== 'yes';
    });
  }

  initCholangioNormalExclusivity();
  initStentInsertedToggle();

  function gatherPayload() {
    return {
      endoscopist_id: document.getElementById('f_endoscopist_id').value || null,
      sedation: document.getElementById('f_sedation').value,
      anesthesiologist: document.getElementById('f_anesthesiologist').value,
      assistants: document.getElementById('f_assistants').value,
      technician: document.getElementById('f_technician').value,
      indication: document.getElementById('f_indication').value,
      papilla: document.getElementById('f_papilla').value,
      cannulation: document.getElementById('f_cannulation').value,
      cholangio: gatherCholangioPayload(),
      therapeutic_procedures: checkedValues('f_therapeutic_procedures'),
      stent: gatherStentPayload(),
      biopsy: document.getElementById('f_biopsy').value,
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
      research: {
        fluoro_time_sec: document.getElementById('r_fluoro_time_sec').value,
        contrast_volume_ml: document.getElementById('r_contrast_volume_ml').value,
        cbd_diameter_mm: document.getElementById('r_cbd_diameter_mm').value,
        stone_size_mm: document.getElementById('r_stone_size_mm').value,
        stone_count: document.getElementById('r_stone_count').value,
        stone_clearance: document.getElementById('r_stone_clearance').value,
        pd_findings: document.getElementById('r_pd_findings').value,
        pd_intervention: document.getElementById('r_pd_intervention').value,
        device_details: document.getElementById('r_device_details').value,
        procedure_duration_min: document.getElementById('r_procedure_duration_min').value,
        asa_class: document.getElementById('r_asa_class').value,
        complication_severity: document.getElementById('r_complication_severity').value,
        disposition: document.getElementById('r_disposition').value,
        followup_plan: document.getElementById('r_followup_plan').value,
      },
    };
  }

  async function saveReport(silent) {
    try {
      await api(`/ercp/${reportId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gatherPayload()),
      });
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
  }
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
