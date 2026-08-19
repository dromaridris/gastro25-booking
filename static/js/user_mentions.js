// Site-wide @username autocomplete on text fields and textareas.

(function () {
  function mentionDropdown() {
    let el = document.getElementById('userMentionDropdown');
    if (!el) {
      el = document.createElement('div');
      el.id = 'userMentionDropdown';
      el.className = 'user-mention-dropdown no-print';
      el.hidden = true;
      document.body.appendChild(el);
    }
    return el;
  }

  let activeInput = null;
  let mentionStart = -1;

  function isMentionEligible(input) {
    if (!input || input.disabled || input.readOnly) return false;
    if (input.classList.contains('no-mentions')) return false;
    if (input.classList.contains('user-mention-input')) return true;
    const tag = input.tagName;
    if (tag === 'TEXTAREA') return true;
    if (tag === 'INPUT') {
      const t = (input.type || 'text').toLowerCase();
      return t === 'text' || t === 'search' || t === '';
    }
    return false;
  }

  async function fetchUsers(q) {
    try {
      const res = await fetch('/api/users/mentions?q=' + encodeURIComponent(q || ''));
      if (!res.ok) return [];
      return res.json();
    } catch (_) {
      return [];
    }
  }

  function insertMention(input, username) {
    const val = input.value;
    const before = val.slice(0, mentionStart);
    const after = val.slice(input.selectionStart);
    if (mentionStart === 0 || before.endsWith('@')) {
      input.value = before.replace(/@?$/, '') + '@' + username + after;
    } else {
      const insertion = (before && !before.endsWith(',') && !before.endsWith(' ') ? ',@' : '@') + username;
      input.value = before + insertion + after;
    }
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus();
    mentionDropdown().hidden = true;
  }

  function showDropdown(input, items) {
    const dd = mentionDropdown();
    if (!items.length) {
      dd.hidden = true;
      return;
    }
    dd.innerHTML = items.map(u =>
      `<button type="button" class="user-mention-option" data-user="${u.username}">${u.full_name} <span class="muted">@${u.username}</span></button>`
    ).join('');
    const rect = input.getBoundingClientRect();
    dd.style.top = (window.scrollY + rect.bottom + 4) + 'px';
    dd.style.left = (window.scrollX + rect.left) + 'px';
    dd.style.minWidth = Math.max(rect.width, 220) + 'px';
    dd.hidden = false;
    dd.querySelectorAll('.user-mention-option').forEach(btn => {
      btn.addEventListener('mousedown', e => {
        e.preventDefault();
        insertMention(input, btn.dataset.user);
      });
    });
  }

  function onInput(e) {
    const input = e.target;
    if (!isMentionEligible(input)) return;
    activeInput = input;
    const pos = input.selectionStart;
    const text = input.value.slice(0, pos);
    const at = text.lastIndexOf('@');
    if (at < 0) {
      mentionDropdown().hidden = true;
      return;
    }
    const fragment = text.slice(at + 1);
    if (/[\s,]/.test(fragment)) {
      mentionDropdown().hidden = true;
      return;
    }
    mentionStart = at;
    fetchUsers(fragment).then(users => showDropdown(input, users));
  }

  document.addEventListener('input', onInput);
  document.addEventListener('click', e => {
    const dd = document.getElementById('userMentionDropdown');
    if (dd && !dd.contains(e.target) && e.target !== activeInput) dd.hidden = true;
  });
})();
