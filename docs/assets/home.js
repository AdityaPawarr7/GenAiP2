/* Landing page: fills each card's headline number from the dashboards' data files.
   The HTML carries static fallbacks, so the page still reads correctly if a fetch fails. */
(function () {
  "use strict";
  var byId = function (id) { return document.getElementById(id); };
  var load = function (url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url); return r.json(); }); };

  function currentTheme() {
    var t = document.documentElement.dataset.theme;
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function syncThemeButton() { byId("theme-btn").textContent = currentTheme() === "dark" ? "Light mode" : "Dark mode"; }
  syncThemeButton();
  byId("theme-btn").addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
    syncThemeButton();
  });

  Promise.all([
    load("data/findings.json").then(function (F) {
      byId("findings-figure").textContent = F.dept_statement_finding.count + " of " + F.n;
    }),
    load("data/tests.json").then(function (T) {
      var r = T.run, failing = r.failed + r.errors;
      byId("validation-figure").textContent = failing ? failing + " of " + r.total + " tests fail" : r.passed + " of " + (r.passed + failing) + " tests pass";
    }),
    load("data/timeline.json").then(function (D) {
      var prompts = D.entries.filter(function (e) { return e.type === "prompt"; }).length;
      byId("timeline-figure").textContent = prompts + " prompts";
    }),
    load("data/tokens.json").then(function (K) {
      var t = K.totals.total;
      byId("tokens-figure").textContent = (t >= 1e6 ? (t / 1e6).toFixed(0) + "M" : Math.round(t / 1e3) + "k") + " tokens";
    })
  ]).catch(function () { /* keep the static fallbacks */ }).then(function () {
    document.body.dataset.ready = "true";
  });
})();
