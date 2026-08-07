(function () {
  "use strict";

  var FAV_KEY = "gi_favorites";
  var RECENT_KEY = "gi_recent_pages";
  var SYNC_URL = "/api/productivity/sync";
  var GET_URL = "/api/productivity";

  function load(key) {
    try { return JSON.parse(localStorage.getItem(key) || "[]"); } catch (e) { return []; }
  }

  function save(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
  }

  function pushRecent(page) {
    if (!page || !page.url) return;
    var recent = load(RECENT_KEY).filter(function (r) { return r.url !== page.url; });
    recent.unshift({ url: page.url, label: page.label || page.url, ts: Date.now() });
    save(RECENT_KEY, recent.slice(0, 15));
    syncServer();
  }

  function toggleFavorite(page) {
    var favs = load(FAV_KEY);
    var idx = favs.findIndex(function (f) { return f.url === page.url; });
    if (idx >= 0) favs.splice(idx, 1);
    else favs.unshift({ url: page.url, label: page.label || page.url });
    save(FAV_KEY, favs.slice(0, 20));
    syncServer();
    return favs;
  }

  function syncServer() {
    if (!window.fetch) return;
    fetch(SYNC_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ favorites: load(FAV_KEY), recent_pages: load(RECENT_KEY) }),
      credentials: "same-origin"
    }).catch(function () {});
  }

  function pullServer() {
    if (!window.fetch) return;
    fetch(GET_URL, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.favorites && data.favorites.length) save(FAV_KEY, data.favorites);
        if (data.recent_pages && data.recent_pages.length) save(RECENT_KEY, data.recent_pages);
      })
      .catch(function () {});
  }

  function initFab() {
    var fab = document.getElementById("giFab");
    if (!fab) return;
    var toggle = fab.querySelector(".gi-fab-toggle");
    var menu = fab.querySelector(".gi-fab-menu");
    if (!toggle || !menu) return;
    toggle.addEventListener("click", function (event) {
      event.stopPropagation();
      var open = menu.hasAttribute("hidden");
      if (open) { menu.removeAttribute("hidden"); toggle.setAttribute("aria-expanded", "true"); }
      else { menu.setAttribute("hidden", ""); toggle.setAttribute("aria-expanded", "false"); }
    });
    document.addEventListener("click", function (event) {
      if (!fab.contains(event.target)) {
        menu.setAttribute("hidden", "");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFab();
    pullServer();
    var path = window.location.pathname;
    var title = document.title || path;
    if (path && path !== "/auth/login") {
      pushRecent({ url: path, label: title.split("—")[0].trim() });
    }
  });

  window.GIProductivity = { toggleFavorite: toggleFavorite, loadFavorites: function () { return load(FAV_KEY); }, loadRecent: function () { return load(RECENT_KEY); } };
})();
