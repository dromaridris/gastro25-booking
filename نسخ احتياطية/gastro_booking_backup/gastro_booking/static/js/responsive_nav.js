/**
 * Responsive top navigation — desktop hover/click dropdowns + mobile flyout panel.
 * Breakpoint must match style.css (@media max-width: 760px).
 */
(function () {
  'use strict';

  var MOBILE_MQ = window.matchMedia('(max-width: 760px)');

  function initResponsiveNav() {
    var toggle = document.getElementById('navToggleBtn');
    var nav = document.getElementById('mainNav');
    var topbar = document.querySelector('.topbar');
    if (!toggle || !nav) return;

    var dropdowns = Array.prototype.slice.call(document.querySelectorAll('.nav-dropdown'));
    var brandHome = document.querySelector('.brand-home');

    function isMobile() {
      return MOBILE_MQ.matches;
    }

    function closeAllDropdowns() {
      dropdowns.forEach(function (dropdown) {
        var menu = dropdown.querySelector('.nav-dropdown-menu');
        var btn = dropdown.querySelector('.nav-dropdown-trigger');
        if (menu) menu.classList.remove('nav-dropdown-open');
        if (btn) btn.setAttribute('aria-expanded', 'false');
      });
    }

    function syncNavPanelHeight() {
      if (!isMobile() || !topbar) {
        nav.style.maxHeight = '';
        return;
      }
      var top = topbar.getBoundingClientRect().bottom;
      nav.style.maxHeight = 'calc(100dvh - ' + Math.ceil(top) + 'px)';
    }

    function setMobileNavOpen(isOpen) {
      nav.classList.toggle('nav-open', isOpen);
      toggle.textContent = isOpen ? '✕' : '☰';
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      document.body.classList.toggle('nav-scroll-lock', isOpen);
      if (isOpen) {
        syncNavPanelHeight();
      } else {
        nav.style.maxHeight = '';
        closeAllDropdowns();
      }
    }

    function closeMobileNav() {
      if (!isMobile()) return;
      setMobileNavOpen(false);
    }

    function closeOtherDropdowns(activeDropdown) {
      dropdowns.forEach(function (other) {
        if (other === activeDropdown) return;
        var otherMenu = other.querySelector('.nav-dropdown-menu');
        var otherBtn = other.querySelector('.nav-dropdown-trigger');
        if (otherMenu) otherMenu.classList.remove('nav-dropdown-open');
        if (otherBtn) otherBtn.setAttribute('aria-expanded', 'false');
      });
    }

    /* ---- Mobile hamburger ---- */
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      if (!isMobile()) return;
      setMobileNavOpen(!nav.classList.contains('nav-open'));
    });

    /* ---- Dropdowns: mobile accordion vs desktop click fallback ---- */
    dropdowns.forEach(function (dropdown) {
      var btn = dropdown.querySelector('.nav-dropdown-trigger');
      var menu = dropdown.querySelector('.nav-dropdown-menu');
      if (!btn || !menu) return;

      menu.addEventListener('click', function (e) {
        e.stopPropagation();
      });
      menu.addEventListener('wheel', function (e) {
        e.stopPropagation();
      }, { passive: true });

      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        e.preventDefault();
        var isOpen = menu.classList.toggle('nav-dropdown-open');
        btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        if (isOpen) closeOtherDropdowns(dropdown);
        if (isMobile() && isOpen) {
          syncNavPanelHeight();
          requestAnimationFrame(function () {
            menu.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          });
        }
      });

      /* Desktop: sync aria-expanded with hover (CSS opens menu) */
      dropdown.addEventListener('mouseenter', function () {
        if (isMobile()) return;
        btn.setAttribute('aria-expanded', 'true');
      });
      dropdown.addEventListener('mouseleave', function () {
        if (isMobile()) return;
        if (!menu.classList.contains('nav-dropdown-open')) {
          btn.setAttribute('aria-expanded', 'false');
        }
      });
      dropdown.addEventListener('focusin', function () {
        if (isMobile()) return;
        btn.setAttribute('aria-expanded', 'true');
      });
      dropdown.addEventListener('focusout', function () {
        if (isMobile()) return;
        if (!dropdown.contains(document.activeElement) && !menu.classList.contains('nav-dropdown-open')) {
          btn.setAttribute('aria-expanded', 'false');
        }
      });
    });

    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        closeAllDropdowns();
        closeMobileNav();
      });
    });

    if (brandHome) {
      brandHome.addEventListener('click', closeMobileNav);
    }

    document.addEventListener('click', function (e) {
      if (isMobile()) {
        if (!nav.contains(e.target) && !toggle.contains(e.target)) {
          closeMobileNav();
        }
        return;
      }
      if (!nav.contains(e.target)) {
        closeAllDropdowns();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeAllDropdowns();
        closeMobileNav();
      }
    });

    function onViewportChange() {
      if (!isMobile()) {
        setMobileNavOpen(false);
        nav.classList.remove('nav-open');
        toggle.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('nav-scroll-lock');
        nav.style.maxHeight = '';
      }
      closeAllDropdowns();
      syncNavPanelHeight();
    }

    if (typeof MOBILE_MQ.addEventListener === 'function') {
      MOBILE_MQ.addEventListener('change', onViewportChange);
    } else if (typeof MOBILE_MQ.addListener === 'function') {
      MOBILE_MQ.addListener(onViewportChange);
    }
    window.addEventListener('resize', syncNavPanelHeight);
    window.addEventListener('orientationchange', syncNavPanelHeight);
  }

  function initNavSearch() {
    var searchToggle = document.getElementById('searchToggleBtn');
    var searchForm = document.getElementById('navSearchForm');
    var searchInput = document.getElementById('navSearchInput');
    if (!searchToggle || !searchForm) return;

    searchToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = !searchForm.hidden;
      searchForm.hidden = isOpen;
      searchToggle.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
      if (!isOpen && searchInput) searchInput.focus();
    });

    document.addEventListener('click', function (e) {
      if (MOBILE_MQ.matches) return;
      if (!searchForm.contains(e.target) && !searchToggle.contains(e.target) && !searchForm.hidden && searchInput && !searchInput.value) {
        searchForm.hidden = true;
        searchToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function init() {
    initResponsiveNav();
    initNavSearch();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
