(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute("content");
    var input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : "";
  }

  function postAction(url) {
    return fetch(url, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken(),
      },
      credentials: "same-origin",
    }).then(function (response) {
      if (!response.ok) throw new Error("Request failed");
      return response.json();
    });
  }

  function markRow(row, status) {
    row.classList.remove("gi-suggestion-pending", "gi-suggestion-accepted", "gi-suggestion-dismissed");
    row.classList.add(status === "accepted" ? "gi-suggestion-accepted" : "gi-suggestion-dismissed");
    var cell = row.querySelector(".gi-suggestion-actions");
    if (!cell) return;
    if (status === "accepted") {
      cell.innerHTML = '<span class="badge bg-success gi-suggestion-badge">✓ Accepted</span>';
    } else {
      cell.innerHTML = '<span class="badge bg-secondary gi-suggestion-badge">Dismissed</span>';
    }
  }

  function bindSuggestionTable(table) {
    var sessionId = table.getAttribute("data-session-id");
    if (!sessionId) return;

    table.addEventListener("click", function (event) {
      var btn = event.target.closest("[data-suggestion-action]");
      if (!btn) return;
      event.preventDefault();
      var row = btn.closest("tr");
      var code = btn.getAttribute("data-investigation-code");
      var action = btn.getAttribute("data-suggestion-action");
      if (!row || !code || !action) return;

      btn.disabled = true;
      var url =
        "/clinical-history/sessions/" +
        sessionId +
        "/suggestions/" +
        encodeURIComponent(code) +
        "/" +
        action;

      postAction(url)
        .then(function (data) {
          if (data.ok) {
            markRow(row, action === "accept" ? "accepted" : "dismissed");
          }
        })
        .catch(function () {
          btn.disabled = false;
        });
    });

    var acceptAll = document.getElementById("giAcceptAllSuggestions");
    if (acceptAll) {
      acceptAll.addEventListener("click", function (event) {
        event.preventDefault();
        acceptAll.disabled = true;
        postAction("/clinical-history/sessions/" + sessionId + "/suggestions/accept-all")
          .then(function (data) {
            if (!data.results) return;
            data.results.forEach(function (result) {
              var row = table.querySelector(
                'tr[data-investigation-code="' + result.code + '"]'
              );
              if (row && result.accepted) markRow(row, "accepted");
            });
          })
          .finally(function () {
            acceptAll.disabled = false;
          });
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".gi-suggestion-table").forEach(bindSuggestionTable);
  });
})();
