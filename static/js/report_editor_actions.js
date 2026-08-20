// Shared report-editor actions. Both top and bottom Print buttons use the
// editor's existing save function; no print route or print layout is changed.
function initReportEditorActions(options) {
  const settings = options || {};
  const locked = !!settings.locked;
  const saveBeforePrint = settings.saveBeforePrint;

  document.querySelectorAll('.js-report-print').forEach((button) => {
    if (button.dataset.reportActionBound === '1') return;
    button.dataset.reportActionBound = '1';

    button.addEventListener('click', async () => {
      const printUrl = button.dataset.printUrl;
      if (!printUrl) return;

      // Open synchronously so browsers do not block the tab while an async
      // save is running. It is navigated only after a successful save.
      const printWindow = window.open('about:blank', '_blank');
      if (!printWindow) {
        alert('Please allow pop-ups for this site to open the report print view.');
        return;
      }

      button.disabled = true;
      try {
        const isDirty = typeof window.hasUnsavedReportChanges === 'function'
          ? window.hasUnsavedReportChanges()
          : true;
        if (!locked && isDirty && typeof saveBeforePrint === 'function') {
          const saved = await saveBeforePrint(true);
          if (!saved) {
            printWindow.close();
            return;
          }
        }
        printWindow.location.replace(printUrl);
      } catch (err) {
        printWindow.close();
        alert(err && err.message ? err.message : 'Could not save the report before printing.');
      } finally {
        button.disabled = false;
      }
    });
  });
}
