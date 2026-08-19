(function () {
    'use strict';

    var MAX_RECENT = 5;

    function initRecentSearches() {
        document.querySelectorAll('.gi-search-panel').forEach(function (panel) {
            var key = panel.getAttribute('data-search-key') || 'gi_search';
            var form = panel.querySelector('.gi-search-form');
            var input = panel.querySelector('input[name="q"]');
            var list = panel.querySelector('.gi-recent-searches');
            if (!form || !input || !list) return;

            function loadRecent() {
                try {
                    return JSON.parse(localStorage.getItem(key) || '[]');
                } catch (e) {
                    return [];
                }
            }

            function saveRecent(items) {
                localStorage.setItem(key, JSON.stringify(items.slice(0, MAX_RECENT)));
            }

            function renderRecent() {
                var items = loadRecent();
                list.innerHTML = '';
                if (!items.length) {
                    list.hidden = true;
                    return;
                }
                list.hidden = false;
                items.forEach(function (term) {
                    var li = document.createElement('li');
                    var btn = document.createElement('button');
                    btn.type = 'button';
                    btn.textContent = term;
                    btn.addEventListener('click', function () {
                        input.value = term;
                        form.submit();
                    });
                    li.appendChild(btn);
                    list.appendChild(li);
                });
            }

            form.addEventListener('submit', function () {
                var term = (input.value || '').trim();
                if (!term) return;
                var items = loadRecent().filter(function (t) { return t !== term; });
                items.unshift(term);
                saveRecent(items);
            });

            renderRecent();
        });
    }

    function initStickyTableShadow() {
        document.querySelectorAll('.gi-table-wrapper').forEach(function (wrap) {
            var scroll = wrap.querySelector('.table-responsive');
            if (!scroll) return;
            scroll.addEventListener('scroll', function () {
                wrap.classList.toggle('gi-table-scrolled', scroll.scrollLeft > 0);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initRecentSearches();
        initStickyTableShadow();
    });
})();
