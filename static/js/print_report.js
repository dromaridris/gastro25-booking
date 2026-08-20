// Shared print helpers — A4 print modes, pagination, and image layout.

(function () {
  var MM_TO_PX = 96 / 25.4;
  var PAGE_MARGIN_SIDE_MM = 10;
  var PAGE_MARGIN_BOTTOM_MM = 0;
  var LETTERHEAD_TOP_MM = 63;
  var LETTERHEAD_BOTTOM_MM = 0;
  var FOOTER_MM = 50;
  var COMPACT_OVERFLOW_MM = 25;
  var CONTINUATION_SAFETY_MM = 3;
  var IMAGE_GAP_PX = 7;
  var MIN_SLOT_PX = 72;
  var MAX_RAIL_WIDTH_PX = 280;

  function pageBudgetPx() {
    var pageHeightMm = 297;
    // The 63 mm header remains in normal document flow (also when visually
    // hidden for pre-printed letterhead). Reserve only the fixed 50 mm footer
    // here so report content can never push the signature/QR to a blank page.
    return (pageHeightMm - FOOTER_MM) * MM_TO_PX;
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

  function contentBottomPx(page) {
    var pageTop = page.getBoundingClientRect().top;
    var bottom = 0;
    Array.prototype.forEach.call(page.children, function (el) {
      if (el.hidden) return;
      if (el.matches('.ercp-print-footer, .print-fixed-footer, .print-secondary-footer')) return;
      var rect = el.getBoundingClientRect();
      bottom = Math.max(bottom, rect.bottom - pageTop);
    });
    return bottom;
  }


  function markFooterOverlap(page) {
    if (!page || page.hidden) return false;
    var footer = page.querySelector('.ercp-print-footer, .print-fixed-footer, .print-secondary-footer');
    if (!footer) return false;
    var footerTop = footer.getBoundingClientRect().top;
    var overlaps = false;
    Array.prototype.forEach.call(page.children, function (el) {
      if (el === footer || el.hidden || el.matches('.ercp-print-footer, .print-fixed-footer, .print-secondary-footer')) return;
      if (el.getBoundingClientRect().bottom > footerTop - 1) overlaps = true;
    });
    page.classList.toggle('print-footer-overlap', overlaps);
    return overlaps;
  }

  function footerSafeBottomPx(page) {
    var footer = page && page.querySelector('.ercp-print-footer, .print-fixed-footer, .print-secondary-footer');
    if (!page || !footer) return pageBudgetPx();
    return footer.getBoundingClientRect().top - page.getBoundingClientRect().top;
  }

  function overflowPx(page) {
    if (!page) return 0;
    return Math.max(0, contentBottomPx(page) - footerSafeBottomPx(page));
  }

  function clearCompactMode(page) {
    if (page) page.classList.remove('print-compact-fit');
  }

  function tryCompactFit(page) {
    if (!page) return false;
    clearCompactMode(page);
    var excess = overflowPx(page);
    if (excess <= 0) return true;
    if (excess > COMPACT_OVERFLOW_MM * MM_TO_PX) return false;
    page.classList.add('print-compact-fit');
    return overflowPx(page) <= 0;
  }

  function removeGeneratedContinuationPages() {
    document.querySelectorAll('.print-report-continuation[data-generated-continuation="1"]').forEach(function (page) {
      while (page.__movedNodes && page.__movedNodes.length) {
        var rec = page.__movedNodes.shift();
        if (rec.placeholder && rec.placeholder.parentNode) {
          rec.placeholder.parentNode.insertBefore(rec.node, rec.placeholder);
          rec.placeholder.remove();
        }
      }
      page.remove();
    });
  }

  function cloneContinuationShell(page1, imagePage) {
    var page = document.createElement('div');
    page.className = 'print-report-continuation';
    page.setAttribute('data-generated-continuation', '1');
    page.setAttribute('data-print-page', 'continuation');
    page.__movedNodes = [];

    var header = page1.querySelector('.ercp-print-header, .print-fixed-header, .print-secondary-header');
    if (header) page.appendChild(header.cloneNode(true));

    var number = page1.querySelector('.ercp-report-number');
    if (number) {
      var numberClone = number.cloneNode(true);
      var badge = numberClone.querySelector('[data-page-num]') || numberClone.querySelector('span:last-child');
      if (badge) badge.setAttribute('data-page-num', '');
      page.appendChild(numberClone);
    }

    var footer = page1.querySelector('.ercp-print-footer, .print-fixed-footer, .print-secondary-footer');
    if (footer) {
      var footerClone = footer.cloneNode(true);
      footerClone.removeAttribute('id');
      page.appendChild(footerClone);
    }

    var parent = imagePage && imagePage.parentNode ? imagePage.parentNode : page1.parentNode;
    if (imagePage && imagePage.parentNode) parent.insertBefore(page, imagePage);
    else parent.insertBefore(page, page1.nextSibling);
    return page;
  }

  function isProtectedReportNode(el) {
    if (!el || el.nodeType !== 1) return true;
    return el.matches('.ercp-print-header, .print-fixed-header, .print-secondary-header, .ercp-report-number, .ercp-print-footer, .print-fixed-footer, .print-secondary-footer');
  }

  function movableReportNodes(page) {
    return Array.prototype.slice.call(page.children).filter(function (el) {
      if (isProtectedReportNode(el)) return false;
      if (el.tagName === 'SPAN' && /Anchor$/.test(el.id || '')) return false;
      return !el.hidden;
    });
  }

  function createContinuationPagesIfNeeded(page1, imagePage) {
    if (!page1) return [];
    removeGeneratedContinuationPages();
    clearCompactMode(page1);

    if (overflowPx(page1) <= 0) return [];
    if (tryCompactFit(page1)) return [];
    clearCompactMode(page1);

    var generated = [];
    var current = null;
    var candidates = movableReportNodes(page1);

    // Move complete trailing sections only. This is intentionally conservative:
    // it avoids splitting Impression/Recommendations across pages and preserves
    // the dedicated image page.
    for (var i = candidates.length - 1; i >= 0 && overflowPx(page1) > 0; i--) {
      var node = candidates[i];
      var placeholder = document.createComment('print-continuation-placeholder');
      node.parentNode.insertBefore(placeholder, node);
      if (!current) {
        current = cloneContinuationShell(page1, imagePage);
        generated.unshift(current);
      }
      var firstContent = Array.prototype.slice.call(current.children).find(function (el) {
        return !isProtectedReportNode(el);
      });
      if (firstContent) current.insertBefore(node, firstContent);
      else {
        var footer = current.querySelector('.ercp-print-footer, .print-fixed-footer, .print-secondary-footer');
        current.insertBefore(node, footer || null);
      }
      current.__movedNodes.unshift({node: node, placeholder: placeholder});

      // If the continuation itself becomes too full, start another continuation
      // for earlier sections. In normal use this is rarely needed, but it keeps
      // long reports from overlapping the footer.
      if (overflowPx(current) > CONTINUATION_SAFETY_MM * MM_TO_PX && i > 0) {
        current = cloneContinuationShell(page1, imagePage);
        generated.unshift(current);
      }
    }

    generated.forEach(function (page) {
      if (overflowPx(page) > 0) tryCompactFit(page);
    });
    return generated;
  }

  function markLastVisiblePrintPage() {
    var pages = Array.prototype.slice.call(document.querySelectorAll('[data-print-page]'))
      .filter(function (el) { return !el.hidden; });
    document.querySelectorAll('[data-print-page]').forEach(function (el) {
      el.classList.remove('print-last-page');
    });
    if (pages.length) pages[pages.length - 1].classList.add('print-last-page');
  }

  function fitImageGridsAboveFooter() {
    var maxHeightPx = 180 * MM_TO_PX;
    var safetyPx = 3 * MM_TO_PX;
    document.querySelectorAll('.ercp-print-image-grid').forEach(function (grid) {
      if (grid.hidden) return;
      grid.style.height = '';
      grid.style.maxHeight = '';
      var page = grid.closest('[data-print-page]');
      if (!page || page.hidden) return;
      var footer = page.querySelector('.ercp-print-footer, .print-fixed-footer, .print-secondary-footer');
      if (!footer) return;
      var gridRect = grid.getBoundingClientRect();
      var footerRect = footer.getBoundingClientRect();
      if (!gridRect.height && !gridRect.top) return;
      var available = footerRect.top - gridRect.top - safetyPx;
      if (available > 0) {
        grid.style.height = Math.floor(Math.min(maxHeightPx, available)) + 'px';
        grid.style.maxHeight = Math.floor(Math.min(maxHeightPx, available)) + 'px';
      }
    });
  }

  function prepareAdaptiveImageGrids() {
    document.querySelectorAll('.ercp-print-image-grid').forEach(function (grid) {
      var cells = Array.prototype.slice.call(grid.querySelectorAll('.ercp-print-image-cell'));
      var imageCount = 0;
      cells.forEach(function (cell) {
        var hasImage = !!cell.querySelector('img');
        cell.hidden = !hasImage;
        if (hasImage) imageCount += 1;
      });
      grid.dataset.imageCount = String(Math.min(imageCount, 9));
      grid.hidden = imageCount === 0;
    });
    fitImageGridsAboveFooter();
  }

  window.prepareAdaptiveImageGrids = prepareAdaptiveImageGrids;

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
    prepareAdaptiveImageGrids();
    opts = opts || {};
    var page1 = document.getElementById(opts.page1Id || 'printPage1Content');
    var overflowSlot = document.getElementById(opts.overflowSlotId || 'page2OverflowSlot');
    var page2 = document.getElementById(opts.page2Id || 'printPage2');
    var moveOrder = opts.moveOrder || [];
    if (!page1) return;

    resetMovableSections(moveOrder);
    if (overflowSlot) overflowSlot.innerHTML = '';
    removeGeneratedContinuationPages();
    clearCompactMode(page1);

    // First try a very small print-only compaction for short overflows. If the
    // report still crosses the footer-safe boundary, create one or more text
    // continuation pages before the dedicated image page.
    createContinuationPagesIfNeeded(page1, page2);
    if (typeof opts.syncPage2 === 'function') {
      opts.syncPage2();
    } else if (page2) {
      var hasImages = !!page2.querySelector('.ercp-print-image-grid img');
      page2.hidden = !hasImages;
    }

    /* Report text and image pages are independent. Never let moved report
       content consume the image page or push images into the fixed footer. */
    prepareAdaptiveImageGrids();
    fitImageGridsAboveFooter();
    document.querySelectorAll('[data-print-page]').forEach(markFooterOverlap);
    markLastVisiblePrintPage();
    window.syncPrintPageNumbers && window.syncPrintPageNumbers();
  };

  window.syncPrintPageNumbers = function () {
    var pages = Array.prototype.slice.call(document.querySelectorAll('[data-print-page]'))
      .filter(function (el) { return !el.hidden; });
    var total = pages.length || 1;
    pages.forEach(function (el, idx) {
      var badge = el.querySelector('[data-page-num]');
      if (!badge) {
        var numberRow = el.querySelector('.ercp-report-number');
        if (numberRow) badge = numberRow.querySelector('span:last-child');
      }
      if (badge) badge.textContent = 'Page ' + (idx + 1) + ' of ' + total;
    });
    var footer = document.querySelector('.print-page-footer-num');
    if (footer && total <= 1) footer.textContent = '';
    else if (footer) footer.textContent = '';
    markLastVisiblePrintPage();
  };

  window.printWithoutHeader = function () {
    document.body.classList.add('letterhead-mode');
    var styleEl = document.getElementById('letterheadPageStyle');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'letterheadPageStyle';
      document.head.appendChild(styleEl);
    }
    styleEl.textContent = '@page { size: A4; margin: 0; }';
    if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
    var reportPage = document.getElementById('ercpPage1Content') || document.getElementById('printPage1Content');
    var imagePage = document.getElementById('ercpPage2') || document.getElementById('printPage2');
    if (reportPage) createContinuationPagesIfNeeded(reportPage, imagePage);
    window.syncPrintPageNumbers && window.syncPrintPageNumbers();
    markLastVisiblePrintPage();
    window.print();
    setTimeout(function () {
      document.body.classList.remove('letterhead-mode');
      styleEl.textContent = '';
      if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
      markLastVisiblePrintPage();
    }, 500);
  };

  window.addEventListener('load', function () {
    prepareAdaptiveImageGrids();
    if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
    var reportPage = document.getElementById('ercpPage1Content') || document.getElementById('printPage1Content');
    var imagePage = document.getElementById('ercpPage2') || document.getElementById('printPage2');
    if (reportPage) createContinuationPagesIfNeeded(reportPage, imagePage);
    window.syncPrintPageNumbers && window.syncPrintPageNumbers();
    markLastVisiblePrintPage();
  });
  window.addEventListener('beforeprint', function () {
    prepareAdaptiveImageGrids();
    if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
    var reportPage = document.getElementById('ercpPage1Content') || document.getElementById('printPage1Content');
    var imagePage = document.getElementById('ercpPage2') || document.getElementById('printPage2');
    if (reportPage) createContinuationPagesIfNeeded(reportPage, imagePage);
    window.syncPrintPageNumbers && window.syncPrintPageNumbers();
    document.querySelectorAll('[data-print-page]').forEach(markFooterOverlap);
    markLastVisiblePrintPage();
    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(function () {
        prepareAdaptiveImageGrids();
        if (typeof window.onBeforePrintFit === 'function') window.onBeforePrintFit();
        var reportPage2 = document.getElementById('ercpPage1Content') || document.getElementById('printPage1Content');
        var imagePage2 = document.getElementById('ercpPage2') || document.getElementById('printPage2');
        if (reportPage2) createContinuationPagesIfNeeded(reportPage2, imagePage2);
        window.syncPrintPageNumbers && window.syncPrintPageNumbers();
        document.querySelectorAll('[data-print-page]').forEach(markFooterOverlap);
        markLastVisiblePrintPage();
      });
    }
  });
})();
