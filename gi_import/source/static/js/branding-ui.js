(function () {
    'use strict';

    function hideSplash() {
        var splash = document.getElementById('gi-splash');
        if (!splash) return;
        splash.classList.add('gi-splash-hidden');
        setTimeout(function () { splash.remove(); }, 400);
    }

    function showLoading() {
        var overlay = document.getElementById('gi-loading-overlay');
        if (overlay) overlay.hidden = false;
    }

    function hideLoading() {
        var overlay = document.getElementById('gi-loading-overlay');
        if (overlay) overlay.hidden = true;
    }

    document.addEventListener('DOMContentLoaded', function () {
        hideSplash();
        hideLoading();

        document.querySelectorAll('form').forEach(function (form) {
            form.addEventListener('submit', function () {
                if (form.dataset.noLoading === 'true') return;
                if (typeof form.checkValidity === 'function' && !form.checkValidity()) return;
                showLoading();
                window.setTimeout(hideLoading, 20000);
            });
        });

        window.addEventListener('pageshow', hideLoading);
    });

    window.GIChartTheme = {
        palette: function () {
            var styles = getComputedStyle(document.documentElement);
            function c(name, fallback) {
                return (styles.getPropertyValue(name) || fallback).trim();
            }
            return {
                primary: c('--gi-color-primary', '#1a5276'),
                secondary: c('--gi-color-secondary', '#2874a6'),
                accent: c('--gi-color-accent', '#3498db'),
                text: c('--gi-color-text', '#1a2332'),
                grid: c('--gi-color-card-border', '#d5dee8'),
                series: [
                    c('--gi-color-primary', '#1a5276'),
                    c('--gi-color-secondary', '#2874a6'),
                    c('--gi-color-accent', '#3498db'),
                ],
            };
        },
        chartJsOptions: function () {
            var p = this.palette();
            return {
                plugins: { legend: { labels: { color: p.text } } },
                scales: {
                    x: { ticks: { color: p.text }, grid: { color: p.grid } },
                    y: { ticks: { color: p.text }, grid: { color: p.grid } },
                },
            };
        },
    };
})();
