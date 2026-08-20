// Advanced endoscopy report editor (EUS, Capsule, …)

function initAdvancedReport() {
  const page = document.getElementById('advancedReportPage');
  if (!page) return;

  const reportId = page.dataset.reportId;
  const urlPrefix = page.dataset.urlPrefix;
  const locked = page.dataset.locked === 'true';

  function checkedValues(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return [];
    return Array.from(el.querySelectorAll('input[type="checkbox"]:checked')).map(c => c.value);
  }

  function gatherImageCaptions() {
    const caps = {};
    page.querySelectorAll('.img-caption-input').forEach(inp => {
      const slot = inp.dataset.slot;
      const value = (inp.value || '').trim();
      if (slot && value) caps[slot] = value;
    });
    return caps;
  }

  function gatherClinical() {
    const clinical = {};
    page.querySelectorAll('.ercp-checkbox-grid[id^="f_"]').forEach(grid => {
      clinical[grid.id.replace(/^f_/, '')] = checkedValues(grid.id);
    });
    page.querySelectorAll('[id^="f_"]').forEach(el => {
      const key = el.id.replace(/^f_/, '');
      if (['endoscopist_id', 'sedation', 'anesthesiologist', 'technician', 'assistants', 'procedure_note', 'impression', 'clinical_plan'].includes(key)) return;
      if (el.closest('.ercp-checkbox-grid')) return;
      if (el.classList.contains('img-caption-input')) return;
      if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' || el.tagName === 'SELECT') {
        clinical[key] = el.value;
      }
    });
    const captions = gatherImageCaptions();
    if (Object.keys(captions).length) clinical.image_captions = captions;
    return clinical;
  }

  function gatherPayload() {
    return {
      endoscopist_id: document.getElementById('f_endoscopist_id')?.value || null,
      sedation: document.getElementById('f_sedation')?.value || '',
      anesthesiologist: document.getElementById('f_anesthesiologist')?.value ?? undefined,
      technician: document.getElementById('f_technician')?.value || '',
      assistants: document.getElementById('f_assistants')?.value || '',
      procedure_note: document.getElementById('f_procedure_note')?.value || '',
      impression: document.getElementById('f_impression')?.value || '',
      clinical_plan: document.getElementById('f_clinical_plan')?.value || '',
      clinical: gatherClinical(),
    };
  }

  function showNotice(msg) {
    const notice = document.getElementById('advSaveNotice');
    if (!notice) return;
    notice.textContent = msg || 'Draft saved.';
    notice.hidden = false;
    setTimeout(() => { notice.hidden = true; }, 2500);
  }

  async function parseJsonResponse(res) {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch (_) {
      throw new Error('Server returned an unexpected response. Please refresh the page and try again.');
    }
  }

  async function saveDraft(silent) {
    const res = await fetch(`${urlPrefix}/${reportId}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(gatherPayload()),
    });
    const data = await parseJsonResponse(res);
    if (!res.ok) throw new Error(data.error || 'Save failed');
    if (window.markReportSaved) window.markReportSaved();
    if (!silent) showNotice('Draft saved.');
    return true;
  }

  async function saveDraftForAction(silent) {
    try {
      return await saveDraft(silent);
    } catch (err) {
      alert(err.message);
      return false;
    }
  }

  const saveBtn = document.getElementById('advSaveDraftBtn');
  if (saveBtn && !locked) {
    saveBtn.addEventListener('click', () => saveDraftForAction(false));
  }

  const genBtn = document.getElementById('advGenerateNoteBtn');
  if (genBtn && !locked) {
    genBtn.addEventListener('click', async () => {
      try {
        const res = await fetch(`${urlPrefix}/${reportId}/generate-note`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(gatherPayload()),
        });
        const data = await parseJsonResponse(res);
        if (!res.ok) throw new Error(data.error || 'Generate failed');
        const noteEl = document.getElementById('f_procedure_note');
        if (noteEl && data.procedure_note) noteEl.value = data.procedure_note;
        showNotice('Procedure note generated.');
      } catch (err) {
        alert(err.message);
      }
    });
  }

  const finalizeForm = document.getElementById('advFinalizeForm');
  if (finalizeForm && !locked) {
    let finalizeReady = false;
    finalizeForm.addEventListener('submit', async (e) => {
      if (finalizeReady) return;
      e.preventDefault();
      if (!confirm('Finalize this report? It will become read-only.')) return;
      try {
        await saveDraft(true);
        finalizeReady = true;
        finalizeForm.submit();
      } catch (err) {
        alert(err.message);
      }
    });
  }

  page.querySelectorAll('.img-upload-input').forEach(input => {
    input.addEventListener('change', async () => {
      if (!input.files || !input.files[0]) return;
      const slot = input.dataset.slot;
      const fd = new FormData();
      fd.append('image', input.files[0]);
      const res = await fetch(`${urlPrefix}/${reportId}/image/${slot}`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) { alert(data.error || 'Upload failed'); return; }
      location.reload();
    });
  });

  page.querySelectorAll('.img-delete-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Delete this image?')) return;
      const slot = btn.dataset.slot;
      const res = await fetch(`${urlPrefix}/${reportId}/image/${slot}/delete`, { method: 'POST' });
      if (!res.ok) { alert('Delete failed'); return; }
      location.reload();
    });
  });

  if (!locked) initUnsavedChangesGuard('#advFieldset', saveDraftForAction);
  initReportEditorActions({ locked, saveBeforePrint: saveDraftForAction });
}

document.addEventListener('DOMContentLoaded', initAdvancedReport);
