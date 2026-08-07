// Shared print helpers — letterhead mode + compact page numbers (all procedure reports).

(function () {
  var MM_TO_PX = 96 / 25.4;
  var PAGE_MARGIN_SIDE_MM = 14;
  var PAGE_MARGIN_BOTTOM_MM = 14;
  var LETTERHEAD_TOP_MM = 30;
  var LETTERHEAD_BOTTOM_MM = 10;
  var IMAGE_GAP_PX = 7;
  var MIN_SLOT_PX = 72;
  var MAX_RAIL_WIDTH_PX = 280;

  function pageBudgetPx() {
    var isLetterhead = document.body.classList.contains('letterhead-mode');
    var pageHeightMm = 297;
    var topMm = isLetterhead ? LETTERHEAD_TOP_MM : PAGE_MARGIN_SIDE_MM;
    var bottomMm = isLetterhead ? LETTERHEAD_BOTTOM_MM : PAGE_MARGIN_BOTTOM_MM;
    return (pageHeightMm - topMm - bottomMm) * MM_TO_PX;
  }

  function resetMovableSections(ids) {
    ids.forEach(function (id) {
      var block = document.getElementById(id);
      var anchor = document.getElementById(id + 'Anchor');
      if (block && anchor) {
        anchor.parentNode.insertBefore(block, anchor.nextSibling);
      }
    });
  }

  /**
   * Size page-1 image rail to fill space above footer without exceeding page 1.
   * Slots 1–4 only; slots 5+ are rendered on page 2 by the server.
   */
  window.fitEndoscopyPrintLayout = function () {
    if (!document.body.classList.contains('print-sidebar-layout')) return;

    var page1 = document.getElementById('printPage1Content');
    var columns = document.querySelector('.print-endoscopy-columns');
    var footer = document.querySelector('.print-endoscopy-footer');
    var imagesEl = document.querySelector('.print-sidebar-images');
    if (!page1 || !columns || !imagesEl) return;

    var imgCount = parseInt(imagesEl.getAttribute('data-image-count') || '0', 10);
    if (imgCount <= 0) return;

    var budget = pageBudgetPx();
    var columnsRect = columns.getBoundingClientRect();
    var page1Rect = page1.getBoundingClientRect();
    var columnsTop = columnsRect.top - page1Rect.top;
    var footerHeight = footer ? footer.offsetHeight : 90;
    var footerMargin = 18;
    var available = budget - columnsTop - footerHeight - footerMargin - 12;

    if (available < imgCount * MIN_SLOT_PX) {
      available = imgCount * MIN_SLOT_PX;
    }

    var slotH = Math.floor((available - (imgCount - 1) * IMAGE_GAP_PX) / imgCount);
    slotH = Math.max(MIN_SLOT_PX, slotH);

    var captionEls = imagesEl.querySelectorAll('figcaption');
    if (captionEls.length) {
      slotH = Math.max(MIN_SLOT_PX, slotH - 10);
    }

    var railWidth = Math.round(Math.min(MAX_RAIL_WIDTH_PX, Math.max(200, slotH * 4 / 3)));

    document.documentElement.style.setProperty('--print-image-slot-h', slotH + 'px');
    document.documentElement.style.setProperty('--print-rail-width', railWidth + 'px');
    document.documentElement.style.setProperty('--print-rail-max-h', available + 'px');
  };

  window.printReportFit = function (opts) {
    opts = opts || {};
    var page1 = document.getElementById(opts.page1Id || 'printPage1Content');
    var overflowSlot = document.getElementById(opts.overflowSlotId || 'page2OverflowSlot');
    var page2 = document.getElementById(opts.page2Id || 'printPage2');
    var moveOrder = opts.moveOrder || [];
    if (!page1) return;

    resetMovableSections(moveOrder);
    if (overflowSlot) overflowSlot.innerHTML = '';

    if (moveOrder.length) {
      var budget = pageBudgetPx();
      for (var i = 0; i < moveOrder.length; i++) {
        if (page1.scrollHeight <= budget) break;
        var block = document.getElementById(moveOrder[i]);
        if (block && overflowSlot) overflowSlot.appendChild(block);
      }
    }

    if (typeof opts.syncPage2 === 'function') {
      opts.syncPage2();
    } else if (page2) {
      var hasImages = !!page2.querySelector('.ercp-print-image-grid img');
      var hasOverflow = !!(overflowSlot && overflowSlot.children.length);
      page2.hidden = !(hasImages || hasOverflow);
    }

    window.syncPrintPageNumbers && window.syncPrintPageNumbers();
  };

  window.syncPrintPageNumbers = function () {
    var pages = Array.prototype.slice.call(document.querySelectorAll('[data-print-page]'))
      .filter(function (el) { return !el.hidden; });
    var total = pages.length || 1;
    pages.forEach(function (el, idx) {
      var badge = el.querySelector('[data-page-num]');
      if (badge) badge.textContent = 'Page ' + (idx + 1) + ' of ' + total;
    });
    var footer = document.querySelector('.print-page-footer-num');
    if (footer && total <= 1) footer.textContent = '';
    else if (footer) footer.textContent = '';
  };

  window.printWithoutHeader = function () {
    document.body.classList.add('letterhead-mode');
    var styleEl = document.getElementById('letterheadPageStyle');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'letterheadPageStyle';
      document.head.appendChild(styleEl);
    }
    styleEl.textContent = '@page { size: A4; margin: ' + LETTERHEAD_TOP_MM + 'mm ' + PAGE_MARGIN_SIDE_MM + 'mm ' + LETTERHEAD_BOTTOM_MM + 'mm ' + PAGE_MARGIN_SIDE_MM + 'mm; }';
    if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
    window.print();
    setTimeout(function () {
      document.body.classList.remove('letterhead-mode');
      styleEl.textContent = '';
      if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
    }, 500);
  };

  window.addEventListener('load', function () {
    if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
  });
  window.addEventListener('beforeprint', function () {
    if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
  });
})();
