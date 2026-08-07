/* Auto-attach CSRF token to forms and fetch() mutations. */
(function () {
  var meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta) return;
  var token = meta.getAttribute('content') || '';
  if (!token) return;

  function ensureFormToken(form) {
    if (!form || !form.tagName || form.tagName.toUpperCase() !== 'FORM') return;
    var method = (form.getAttribute('method') || 'GET').toUpperCase();
    if (method !== 'POST' && method !== 'PUT' && method !== 'PATCH' && method !== 'DELETE') return;
    var existing = form.querySelector('input[name="csrf_token"]');
    if (existing) {
      existing.value = token;
      return;
    }
    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrf_token';
    input.value = token;
    form.appendChild(input);
  }

  document.querySelectorAll('form').forEach(ensureFormToken);
  document.addEventListener('submit', function (ev) {
    ensureFormToken(ev.target);
  }, true);

  if (typeof window.fetch === 'function') {
    var originalFetch = window.fetch;
    window.fetch = function (input, init) {
      init = init || {};
      var method = (init.method || 'GET').toUpperCase();
      if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS' && method !== 'TRACE') {
        var headers = new Headers(init.headers || {});
        if (!headers.has('X-CSRFToken') && !headers.has('X-CSRF-Token')) {
          headers.set('X-CSRFToken', token);
        }
        init.headers = headers;
      }
      return originalFetch(input, init);
    };
  }
})();
