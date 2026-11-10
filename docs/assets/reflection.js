/* Reflection page: theme toggle, and fills the side-note numbers from the dashboards' data files.
   The HTML carries static fallbacks (2026-11-10 build), so the page still reads correctly if a fetch fails. */
(function () {
  "use strict";
  var byId = function (id) { return document.getElementById(id); };
  var set = function (id, v) { var el = byId(id); if (el) el.textContent = v; };
  var load = function (url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url); return r.json(); }); };
  var pct = function (part, whole) { return Math.round(100 * part / whole) + "%"; };

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
    load("data/tokens.json").then(function (K) {
      var tot = K.totals.total;
      set("f-tokens", Math.round(tot / 1e6) + "M");
      set("f-cost", "$" + Math.round(K.totals.cost_usd));
      set("f-p1", pct(K.by_phase["phase-1"].total, tot));
      set("f-subagents", K.counts.subagents);
      set("f-sessions", K.counts.sessions);
      set("f-clears", K.counts.clears);
      set("f-val", pct(K.by_activity.running_validation.total, tot));
    }),
    load("data/tests.json").then(function (T) {
      set("f-tests", T.run.total);
      set("f-passed", T.run.passed);
      set("f-failed", T.run.failed + T.run.errors);
      set("f-extra", T.tests.filter(function (t) { return !t.acceptance_criterion; }).length);
    }),
    load("data/timeline.json").then(function (D) {
      set("f-prompts", D.entries.filter(function (e) { return e.actor === "Adi" && e.type === "prompt"; }).length);
    }),
    load("data/findings.json").then(function (F) {
      var d = F.distributions.default_rule;
      set("f-dept", F.dept_statement_finding.count + " of " + F.n);
      set("f-instr", d.instructor_discretion + " of " + F.n);
      set("f-ban", d.banned);
      set("f-enc", d.allowed_encouraged);
    })
  ]).catch(function () { /* keep the static fallbacks */ }).then(function () {
    document.body.dataset.ready = "true";
  });
})();
