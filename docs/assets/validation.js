/* Validation dashboard (Phase 4). Reads data/tests.json, data/test_runs.json,
   data/acceptance_criteria.json, data/reviews.json, data/agreement.json and
   data/policies.json (school names only). Every number is computed at load time. */
(function () {
  "use strict";

  var STATUS = {
    passed: { label: "Passed", icon: "✓" },
    failed: { label: "Failed", icon: "✕" },
    error: { label: "Error", icon: "!" },
    skipped: { label: "Skipped", icon: "–" },
    manual: { label: "Manual review", icon: "◉" },
    uncovered: { label: "No test", icon: "✕" }
  };
  var STATUS_ORDER = ["failed", "error", "passed", "skipped"];
  var FIELD_LABELS = {
    policy_level: "Policy level",
    default_rule: "Default rule",
    stance: "Stance",
    collaboration_framing: "Collaboration framing",
    disclosure_required: "Disclosure",
    se_course_policy: "SE course policy"
  };
  var PHASE_NAMES = {
    0: "Setup and logging", 1: "Data collection", 2: "Coding and analysis", 3: "Findings dashboard",
    4: "Validation", 5: "Contributions timeline", 6: "Token usage", 7: "Publish"
  };

  var T, RUNS, ACS, REV, AG, NAMES = {}, charts = {}, open = {};
  var byId = function (id) { return document.getElementById(id); };
  var css = function (name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); };
  var pct = function (x, digits) { return x === null || x === undefined ? "–" : (100 * x).toFixed(digits || 0) + "%"; };

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function chip(status, label) {
    var s = el("span", { class: "st " + status });
    s.appendChild(el("span", { class: "ic", "aria-hidden": "true" }, STATUS[status].icon));
    s.appendChild(document.createTextNode(label || STATUS[status].label));
    return s;
  }

  function fmtTime(iso) {
    var d = new Date(iso);
    return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }

  /* ---------- coverage (same rule as scripts/run_validation.py coverage()) ---------- */
  function coverage() {
    var cov = {};
    ACS.acs.forEach(function (a) { cov[a.id] = { ac: a, tests: [], reviews: [] }; });
    T.tests.forEach(function (t) { if (cov[t.acceptance_criterion]) cov[t.acceptance_criterion].tests.push(t); });
    REV.forEach(function (r) { (r.acs || []).forEach(function (id) { if (cov[id]) cov[id].reviews.push(r); }); });
    Object.keys(cov).forEach(function (id) {
      var c = cov[id], bad = c.tests.filter(function (t) { return t.status === "failed" || t.status === "error"; }).length;
      c.failed = bad;
      c.passed = c.tests.filter(function (t) { return t.status === "passed"; }).length;
      c.status = c.tests.length ? (bad ? "failed" : "passed") : (c.reviews.length ? "manual" : "uncovered");
    });
    return cov;
  }

  /* ---------- headline + KPIs ---------- */
  function renderHead(cov) {
    var r = T.run, failing = r.failed + r.errors;
    var enforced = ACS.acs.filter(function (a) { return a.enforced; });
    var gaps = enforced.filter(function (a) { return cov[a.id].status === "uncovered"; });
    byId("headline").textContent = (failing ? failing + " of " + r.total + " tests fail" : "All " + r.passed + " tests pass") +
      (gaps.length ? ", and " + gaps.length + " acceptance criteria have no check" :
        ", and every acceptance criterion through Phase " + ACS.enforced_through_phase + " has a test or a review");

    var covered = enforced.length - gaps.length;
    var reviewAcs = REV.filter(function (x) { return (x.acs || []).length; }).length;
    var tiles = [
      { id: "passed", label: "Tests passed", value: String(r.passed), of: "/ " + (r.passed + failing), detail: pct(r.pass_rate, 1) + " of tests that ran" },
      { id: "failed", label: "Failing", value: String(failing), chip: failing ? "failed" : "passed",
        chipText: failing ? "Needs attention" : "None failing", detail: r.skipped + " skipped" },
      { id: "coverage", label: "ACs with a check", value: String(covered), of: "/ " + enforced.length,
        detail: "Phases 0–" + ACS.enforced_through_phase + "; " + (ACS.acs.length - enforced.length) + " planned ACs later" },
      { id: "reviews", label: "Manual reviews", value: String(REV.length), detail: reviewAcs + " stand in for an AC test" },
      { id: "last-run", label: "Last run", value: fmtTime(r.timestamp), small: true,
        detail: Math.round(r.duration) + " s · " + RUNS.length + " runs in history" }
    ];
    var wrap = byId("kpis");
    wrap.textContent = "";
    tiles.forEach(function (k) {
      var d = el("div", { class: "kpi", "data-kpi": k.id });
      d.appendChild(el("p", { class: "label" }, k.label));
      var v = el("p", { class: "value" }, k.value);
      if (k.small) v.style.fontSize = "22px";
      if (k.of) v.appendChild(el("span", { class: "of" }, k.of));
      d.appendChild(v);
      var det = el("p", { class: "detail" });
      if (k.chip) { det.appendChild(chip(k.chip, k.chipText)); det.appendChild(document.createTextNode(" · ")); }
      det.appendChild(document.createTextNode(k.detail));
      d.appendChild(det);
      wrap.appendChild(d);
    });
  }

  /* ---------- charts ---------- */
  function tooltipStyle() {
    return {
      backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: css("--ink-2"),
      borderColor: css("--axis"), borderWidth: 1, padding: 10, cornerRadius: 8,
      titleFont: { size: 15, weight: "600" }, bodyFont: { size: 13 }
    };
  }

  // Vertical crosshair at the hovered run, and a direct label on runs with failures.
  var runMarks = {
    id: "runMarks",
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx, meta = chart.getDatasetMeta(0), area = chart.chartArea;
      ctx.save();
      var active = chart.tooltip && chart.tooltip.getActiveElements();
      if (active && active.length) {
        ctx.strokeStyle = css("--axis"); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(active[0].element.x, area.top); ctx.lineTo(active[0].element.x, area.bottom); ctx.stroke();
      }
      ctx.fillStyle = css("--ink-2");
      ctx.font = "13px system-ui, -apple-system, 'Segoe UI', sans-serif";
      ctx.textBaseline = "top";
      chart.$labels = [];
      RUNS.forEach(function (r, i) {
        var bad = r.failed + r.errors;
        if (!bad) return;
        var p = meta.data[i], text = bad + " failed" + (r.note ? " (" + r.note + ")" : "");
        var w = ctx.measureText(text).width;
        ctx.textAlign = p.x + w / 2 > area.right ? "right" : (p.x - w / 2 < area.left ? "left" : "center");
        ctx.fillText(text, p.x, p.y + 12);
        chart.$labels.push(text);
      });
      ctx.restore();
    }
  };

  function renderRunsChart() {
    var box = byId("chart-runs").parentNode;
    var empty = box.parentNode.querySelector(".runs-empty");
    if (!RUNS.length) {
      if (!empty) box.parentNode.insertBefore(el("p", { class: "runs-empty" }, "No pipeline runs recorded yet. Run python scripts/run_validation.py."), box);
      box.hidden = true;
      return;
    }
    var rates = RUNS.map(function (r) { return r.pass_rate === null ? null : Math.round(r.pass_rate * 10000) / 100; });
    var lo = Math.min.apply(null, rates.filter(function (x) { return x !== null; }).concat([100]));
    var min = Math.max(0, Math.floor((lo - 0.25) * 2) / 2);
    var bad = RUNS.map(function (r) { return r.failed + r.errors > 0; });
    var surface = css("--surface");
    if (charts.runs) charts.runs.destroy();
    charts.runs = new Chart(byId("chart-runs"), {
      type: "line",
      data: {
        labels: RUNS.map(function (r) { return fmtTime(r.timestamp); }),
        datasets: [{
          data: rates, borderColor: css("--accent"), borderWidth: 2, tension: 0, borderCapStyle: "round", borderJoinStyle: "round",
          pointRadius: bad.map(function (b) { return b ? 7 : 5; }), pointHoverRadius: bad.map(function (b) { return b ? 8 : 6; }),
          pointStyle: bad.map(function (b) { return b ? "crossRot" : "circle"; }),
          pointBackgroundColor: bad.map(function (b) { return b ? css("--critical") : css("--accent"); }),
          pointBorderColor: bad.map(function (b) { return b ? css("--critical") : surface; }),
          pointBorderWidth: bad.map(function (b) { return b ? 3 : 2; }),
          pointHitRadius: 12
        }]
      },
      plugins: [runMarks],
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: "index", intersect: false },
        layout: { padding: { top: 8, right: 16, bottom: 4, left: 4 } },
        scales: {
          x: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--ink-2"), maxRotation: 0, autoSkip: true } },
          y: { min: min, max: 100, grid: { color: css("--grid"), drawTicks: false }, border: { display: false },
               ticks: { color: css("--ink-2"), padding: 6, maxTicksLimit: 6, callback: function (v) { return v + "%"; } } }
        },
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(tooltipStyle(), {
            displayColors: false,
            callbacks: {
              title: function (items) { var r = RUNS[items[0].dataIndex]; return pct(r.pass_rate, 2) + " passed"; },
              label: function (item) {
                var r = RUNS[item.dataIndex];
                var lines = [r.passed + " of " + (r.passed + r.failed + r.errors) + " tests, " + r.skipped + " skipped", r.run_id];
                if (r.note) lines.push("Note: " + r.note);
                r.failed_tests.slice(0, 3).forEach(function (f) { lines.push("✕ " + f.split("::").pop()); });
                return lines;
              }
            }
          })
        }
      }
    });
    var key = byId("runs-key");
    key.textContent = "";
    [["passed", "Run with no failures"], ["failed", "Run with failures"]].forEach(function (k) { key.appendChild(el("li")).appendChild(chip(k[0], k[1])); });
    asTable("chart-runs", ["Run", "Time", "Passed", "Failed", "Skipped", "Pass rate", "Note"], RUNS.map(function (r) {
      return [r.run_id, fmtTime(r.timestamp), r.passed, r.failed + r.errors, r.skipped, pct(r.pass_rate, 2), r.note || ""];
    }));
  }

  var tipValues = {
    id: "tipValues",
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx;
      ctx.save();
      ctx.fillStyle = css("--ink-2");
      ctx.font = "11px system-ui, -apple-system, 'Segoe UI', sans-serif";
      ctx.textAlign = "left"; ctx.textBaseline = "middle";
      chart.data.datasets.forEach(function (ds, i) {
        chart.getDatasetMeta(i).data.forEach(function (bar, j) { ctx.fillText(ds.data[j] + "%", bar.x + 4, bar.y); });
      });
      ctx.restore();
    }
  };

  function renderAgreeChart() {
    var h = AG.human_vs_claude, a = AG.ai2_vs_claude;
    var fields = Object.keys(FIELD_LABELS).filter(function (f) { return h.fields[f]; });
    var series = [
      { key: "human", src: h, label: "Adi vs Claude (n=" + h.n_institutions + ")", color: css("--s1") },
      { key: "ai2", src: a, label: "Second AI vs Claude (n=" + a.n_institutions + ")", color: css("--s2") }
    ];
    if (charts.agree) charts.agree.destroy();
    charts.agree = new Chart(byId("chart-agree"), {
      type: "bar",
      plugins: [tipValues],
      data: {
        labels: fields.map(function (f) { return FIELD_LABELS[f]; }),
        datasets: series.map(function (s) {
          return { label: s.label, seriesKey: s.key, data: fields.map(function (f) { return Math.round(s.src.fields[f].percent_agreement * 100); }),
            backgroundColor: s.color, hoverBackgroundColor: s.color, borderRadius: 4, borderSkipped: "start",
            maxBarThickness: 14, categoryPercentage: 0.72, barPercentage: 0.92 };
        })
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false, indexAxis: "y",
        layout: { padding: { right: 34 } },
        scales: {
          x: { min: 0, max: 100, grid: { color: css("--grid"), drawTicks: false }, border: { display: false },
               ticks: { color: css("--ink-2"), padding: 6, stepSize: 25, callback: function (v) { return v + "%"; } } },
          y: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--ink-2"), font: { size: 12 } } }
        },
        plugins: {
          legend: { display: true, position: "top", align: "start",
            labels: { color: css("--ink-2"), boxWidth: 10, boxHeight: 10, useBorderRadius: true, borderRadius: 3, font: { size: 13 } } },
          tooltip: Object.assign(tooltipStyle(), {
            boxWidth: 10, boxHeight: 2,
            callbacks: {
              title: function (items) { return items[0].label; },
              label: function (item) {
                var s = series[item.datasetIndex], f = s.src.fields[fields[item.dataIndex]];
                return s.label + ": " + item.raw + "%, " + kappaText(f);
              }
            }
          })
        }
      }
    });
    asTable("chart-agree", ["Field"].concat(series.map(function (s) { return s.label; })), fields.map(function (f) {
      return [FIELD_LABELS[f]].concat(series.map(function (s) { var x = s.src.fields[f]; return pct(x.percent_agreement) + ", " + kappaText(x); }));
    }));
  }

  function kappaText(f) {
    if (f.weighted_kappa_linear !== undefined) return "weighted κ " + f.weighted_kappa_linear.toFixed(2);
    return f.cohens_kappa === null ? "κ undefined" : "κ " + f.cohens_kappa.toFixed(2);
  }

  function asTable(id, head, rows) {
    var det = document.querySelector('details[data-for="' + id + '"]');
    var old = det.querySelector("table");
    if (old) old.remove();
    var t = el("table"), tr = el("tr"), tb = el("tbody");
    head.forEach(function (h) { tr.appendChild(el("th", { scope: "col" }, h)); });
    t.appendChild(el("thead")).appendChild(tr);
    rows.forEach(function (row) {
      var r = el("tr");
      row.forEach(function (c) { r.appendChild(el("td", null, String(c))); });
      tb.appendChild(r);
    });
    t.appendChild(tb);
    det.appendChild(t);
  }

  /* ---------- coverage matrix ---------- */
  function renderCoverage(cov) {
    var enforced = ACS.acs.filter(function (a) { return a.enforced; });
    byId("cov-sub").textContent = "Each acceptance criterion from specs/phase-*.md, the tests mapped to it (by test name or an ac marker), and any manual review standing in for a test. " +
      "Coverage is enforced for Phases 0–" + ACS.enforced_through_phase + " (" + enforced.length + " ACs); later phases are planned and turn green as they ship. Select an AC to filter the test table.";
    var key = byId("cov-key");
    [["passed", "All tests pass"], ["failed", "A test fails"], ["manual", "Manual review"], ["uncovered", "No test or review"]].forEach(function (k) {
      key.appendChild(el("li")).appendChild(chip(k[0], k[1]));
    });
    var wrap = byId("cov");
    var phases = [];
    ACS.acs.forEach(function (a) { if (phases.indexOf(a.phase) < 0) phases.push(a.phase); });
    phases.forEach(function (p) {
      var list = ACS.acs.filter(function (a) { return a.phase === p; });
      var planned = !list[0].enforced;
      var box = el("div", { class: "phase", "data-phase": String(p) });
      var h = el("h3", null, "Phase " + p + ": " + (PHASE_NAMES[p] || ""));
      var ok = list.filter(function (a) { return cov[a.id].status !== "uncovered"; }).length;
      h.appendChild(el("small", null, planned ? "planned · " + ok + "/" + list.length + " checked" : ok + "/" + list.length + " checked"));
      box.appendChild(h);
      var ul = el("ul");
      list.forEach(function (a) {
        var c = cov[a.id];
        var li = el("li", { class: "ac " + c.status, tabindex: "0", role: "button", "data-ac": a.id, "data-status": c.status });
        li.appendChild(el("span", { class: "id" }, a.id));
        li.appendChild(withCode(el("span", { class: "text" }), a.text));
        var label = c.status === "uncovered" && planned ? "Planned, no test yet" : null;
        li.appendChild(chip(c.status, label));
        var tally = el("span", { class: "tally" });
        if (c.tests.length) {
          tally.appendChild(el("b", null, String(c.tests.length)));
          tally.appendChild(document.createTextNode(c.tests.length === 1 ? " test" : " tests"));
          if (c.failed) tally.appendChild(document.createTextNode(", " + c.failed + " failing"));
        }
        if (c.reviews.length) {
          if (c.tests.length) tally.appendChild(document.createTextNode(" · "));
          tally.appendChild(document.createTextNode("Review " + c.reviews.map(function (r) { return r.id; }).join(", ") + " (" + c.reviews[0].actor + ")"));
        }
        if (!c.tests.length && !c.reviews.length) tally.appendChild(document.createTextNode(planned ? "Phase " + p + " not built yet" : "No test and no manual review"));
        li.appendChild(tally);
        var go = function () {
          if (c.tests.length) {
            setFilters({ ac: a.id });
            byId("h-tests").scrollIntoView({ block: "start" });
          } else if (c.reviews.length) {
            byId("review-" + c.reviews[0].id).scrollIntoView({ block: "center" });
          }
        };
        li.addEventListener("click", go);
        li.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
        ul.appendChild(li);
      });
      box.appendChild(ul);
      wrap.appendChild(box);
    });
  }

  /* ---------- test table ---------- */
  function initFilters() {
    var count = function (pred) { return T.tests.filter(pred).length; };
    var phases = [];
    T.tests.forEach(function (t) { if (t.phase !== null && phases.indexOf(t.phase) < 0) phases.push(t.phase); });
    phases.sort(function (a, b) { return a - b; }).forEach(function (p) {
      byId("f-phase").appendChild(el("option", { value: String(p) }, "Phase " + p + " (" + count(function (t) { return t.phase === p; }) + ")"));
    });
    STATUS_ORDER.forEach(function (s) {
      var n = count(function (t) { return t.status === s; });
      if (n || s === "failed") byId("f-status").appendChild(el("option", { value: s }, STATUS[s].label + " (" + n + ")"));
    });
    var acs = [];
    T.tests.forEach(function (t) { if (t.acceptance_criterion && acs.indexOf(t.acceptance_criterion) < 0) acs.push(t.acceptance_criterion); });
    acs.sort(function (a, b) {
      var x = a.slice(2).split(".").map(Number), y = b.slice(2).split(".").map(Number);
      return x[0] - y[0] || x[1] - y[1];
    }).forEach(function (a) { byId("f-ac").appendChild(el("option", { value: a }, a + " (" + count(function (t) { return t.acceptance_criterion === a; }) + ")")); });
    byId("f-ac").appendChild(el("option", { value: "none" }, "No AC, extra (" + count(function (t) { return !t.acceptance_criterion; }) + ")"));

    ["q", "f-phase", "f-status", "f-ac"].forEach(function (id) {
      byId(id).addEventListener(id === "q" ? "input" : "change", renderRows);
    });
    byId("reset").addEventListener("click", function () { setFilters({}); });
  }

  function setFilters(f) {
    byId("q").value = f.q || "";
    byId("f-phase").value = f.phase || "";
    byId("f-status").value = f.status || "";
    byId("f-ac").value = f.ac || "";
    renderRows();
  }

  function filtered() {
    var q = byId("q").value.trim().toLowerCase(), ph = byId("f-phase").value, st = byId("f-status").value, ac = byId("f-ac").value;
    return T.tests.filter(function (t) {
      if (ph && String(t.phase) !== ph) return false;
      if (st && t.status !== st) return false;
      if (ac === "none" && t.acceptance_criterion) return false;
      if (ac && ac !== "none" && t.acceptance_criterion !== ac) return false;
      if (q && (t.id + " " + t.message).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
  }

  function renderRows() {
    var rows = filtered().slice().sort(function (a, b) {
      return STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status);
    });
    var body = byId("rows");
    body.textContent = "";
    byId("count").textContent = "Showing " + rows.length + " of " + T.tests.length + " tests";
    if (!rows.length) {
      var tr = el("tr"), td = el("td", { colspan: "5", class: "empty" }, "No tests match these filters.");
      tr.appendChild(td); body.appendChild(tr);
      return;
    }
    var frag = document.createDocumentFragment();
    rows.forEach(function (t) {
      var tr = el("tr", { class: "row", tabindex: "0", "data-id": t.id, "data-status": t.status, "aria-expanded": open[t.id] ? "true" : "false" });
      tr.appendChild(el("td", { class: "status" })).appendChild(chip(t.status));
      var name = el("td", { class: "name" });
      name.appendChild(el("code", null, t.name));
      name.appendChild(el("small", null, t.file));
      tr.appendChild(name);
      tr.appendChild(el("td", { class: "phase" }, t.phase === null ? "–" : String(t.phase)));
      tr.appendChild(el("td", { class: "ac-cell" + (t.acceptance_criterion ? "" : " extra") }, t.acceptance_criterion || "extra"));
      tr.appendChild(el("td", { class: "num" }, t.duration < 0.01 ? "<0.01 s" : t.duration.toFixed(2) + " s"));
      var toggle = function () { open[t.id] = !open[t.id]; renderRows(); };
      tr.addEventListener("click", toggle);
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
      frag.appendChild(tr);
      if (open[t.id]) frag.appendChild(detailRow(t));
    });
    body.appendChild(frag);
  }

  function detailRow(t) {
    var tr = el("tr", { class: "detail-row", "data-for": t.id }), td = el("td", { colspan: "5" }), dl = el("dl");
    var add = function (k, v) { dl.appendChild(el("dt", null, k)); var dd = el("dd"); if (typeof v === "string") dd.textContent = v; else dd.appendChild(v); dl.appendChild(dd); };
    add("Source file", el("code", { class: "src" }, t.file));
    add("Test id", t.id);
    add("Acceptance criterion", t.acceptance_criterion ? t.acceptance_criterion + " — " + acText(t.acceptance_criterion) : "None (extra test)");
    add("Run", t.run_id + ", " + fmtTime(t.timestamp));
    add("Message", t.message ? el("pre", { class: "msg" }, t.message) : (t.status === "passed" ? "Passed, no message." : "No message recorded."));
    td.appendChild(dl);
    tr.appendChild(td);
    return tr;
  }

  // Spec text marks file names with backticks; show those parts as code.
  function withCode(node, text) {
    text.split("`").forEach(function (part, i) { if (part) node.appendChild(i % 2 ? el("code", null, part) : document.createTextNode(part)); });
    return node;
  }

  function acText(id) {
    var a = ACS.acs.filter(function (x) { return x.id === id; })[0];
    return a ? a.text : "not in the specs";
  }

  /* ---------- reviews ---------- */
  function renderReviews() {
    var ol = byId("reviews");
    REV.slice().sort(function (a, b) { return a.date < b.date ? -1 : 1; }).forEach(function (r) {
      var li = el("li", { class: "review", id: "review-" + r.id, "data-actor": r.actor });
      var head = el("header");
      head.appendChild(el("span", null, r.id + " · " + fmtTime(r.date) + " ET · Phase " + r.phase));
      head.appendChild(el("span", { class: "who" }, r.actor));
      if ((r.acs || []).length) head.appendChild(el("span", { class: "acs" }, "Covers " + r.acs.join(", ")));
      li.appendChild(head);
      li.appendChild(el("h3", null, r.reviewed));
      var dl = el("dl");
      [["Method", r.method], ["Outcome", r.outcome], ["Notes", r.notes]].forEach(function (p) {
        if (!p[1]) return;
        dl.appendChild(el("dt", null, p[0]));
        dl.appendChild(el("dd", null, p[1]));
      });
      li.appendChild(dl);
      li.appendChild(el("p", { class: "ref" }, "PROGRESS.md: " + r.progress_refs.join("; ")));
      ol.appendChild(li);
    });
  }

  /* ---------- agreement finding ---------- */
  function renderAgreeFinding() {
    var h = AG.human_vs_claude, a = AG.ai2_vs_claude, hf = h.fields, af = a.fields;
    var note = byId("agree-note");
    var p = function (parts) {
      var x = el("p");
      parts.forEach(function (s, i) { x.appendChild(i % 2 ? el("b", null, s) : document.createTextNode(s)); });
      note.appendChild(x);
    };
    p(["Adi blind-coded " + h.n_institutions + " schools. Agreement with Claude was ", pct(hf.stance.percent_agreement) + " on stance",
       " (linear-weighted κ " + hf.stance.weighted_kappa_linear.toFixed(2) + ") and ", pct(hf.disclosure_required.percent_agreement) + " on disclosure",
       " (κ " + hf.disclosure_required.cohens_kappa.toFixed(2) + "), while policy level matched on " + pct(hf.policy_level.percent_agreement) + "."]);
    p(["Claude anchors stance on the neutral \"the instructor decides\" wording most university pages use; Adi read the overall tone of the page. ",
       "Decision (Adi, Nov 9): all codes stay unchanged.",
       " Tone is a subjective judgment, so the split is reported as a finding about the measure, not corrected toward either coder. Read stance on the Findings page as one coder's reading."]);
    p(["The second AI agreed with Claude on " + pct(af.stance.percent_agreement) + " of stance codes (n=" + a.n_institutions + "), but it coded with codebook conventions written from these same schools, so that figure is inflated. ",
       "With n=" + h.n_institutions + ", the human κ values are unstable.", ""]);

    var t = byId("dis");
    t.appendChild(el("caption", null, "Stance and disclosure disagreements"));
    var hr = el("tr");
    ["School", "Field", "Adi", "Claude"].forEach(function (x) { hr.appendChild(el("th", { scope: "col" }, x)); });
    t.appendChild(el("thead")).appendChild(hr);
    var tb = el("tbody");
    var fmt = function (field, v) { return field === "stance" ? (v > 0 ? "+" + v : String(v).replace("-", "−")) : String(v); };
    h.disagreements.filter(function (d) { return d.field === "stance" || d.field === "disclosure_required"; }).forEach(function (d) {
      var tr = el("tr", { "data-slug": d.slug, "data-field": d.field });
      [NAMES[d.slug] || d.slug, FIELD_LABELS[d.field], fmt(d.field, d.rater), fmt(d.field, d.claude)].forEach(function (c) { tr.appendChild(el("td", null, c)); });
      tb.appendChild(tr);
    });
    t.appendChild(tb);
  }

  /* ---------- theme ---------- */
  function currentTheme() {
    var t = document.documentElement.dataset.theme;
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function syncThemeButton() { byId("theme-btn").textContent = currentTheme() === "dark" ? "Light mode" : "Dark mode"; }
  function renderCharts() { renderRunsChart(); renderAgreeChart(); }
  function initTheme() {
    syncThemeButton();
    byId("theme-btn").addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
      syncThemeButton();
      renderCharts();
    });
    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
        if (!document.documentElement.dataset.theme) { syncThemeButton(); renderCharts(); }
      });
    }
  }

  /* ---------- boot ---------- */
  function load(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + " returned HTTP " + r.status);
      return r.json();
    });
  }

  Promise.all(["data/tests.json", "data/test_runs.json", "data/acceptance_criteria.json", "data/reviews.json", "data/agreement.json", "data/policies.json"].map(load)).then(function (res) {
    T = res[0]; RUNS = res[1]; ACS = res[2]; REV = res[3]; AG = res[4];
    res[5].records.forEach(function (r) { NAMES[r.slug] = r.name; });
    var cov = coverage();
    initTheme();
    renderHead(cov);
    renderCharts();
    renderCoverage(cov);
    initFilters();
    renderRows();
    renderReviews();
    renderAgreeFinding();
    document.body.dataset.ready = "true";
  }).catch(function (err) {
    var main = byId("main");
    var p = el("p", { class: "empty", role: "alert" }, "The dashboard data could not be loaded (" + err.message + "). Serve the docs/ folder over HTTP, for example with python3 -m http.server, and reload.");
    main.insertBefore(p, main.firstChild);
    document.body.dataset.ready = "error";
  });
})();
