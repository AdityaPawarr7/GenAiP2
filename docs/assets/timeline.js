/* Contributions timeline (Phase 5). Reads data/timeline.json, built by
   scripts/build_timeline.py from logs/events.jsonl, PROGRESS.md and git log.
   Every number is computed from the entries at load time. */
(function () {
  "use strict";

  var ACTOR_VAR = { "Adi": "--a-adi", "Claude": "--a-claude", "Subagent": "--a-subagent", "Claude-Cowork": "--a-cowork", "System": "--a-system" };
  var TYPE_LABELS = {
    prompt: "Prompt", response: "Response", handback: "Subagent hand-back", notification: "Notification",
    decision: "Decision", review: "Review", progress: "Progress log", commit: "Commit", clear: "/clear", compact: "/compact"
  };
  var ROLE_INFO = {
    decision: { label: "Decisions", one: "Decision", what: "Choices that set scope, method or data: plan approvals, coding rules, publish options." },
    correction: { label: "Corrections", one: "Correction", what: "Times Adi caught a problem in Claude's work and had it fixed." },
    review: { label: "Reviews", one: "Review", what: "Adi checked finished work: batch reviews, phase approvals, the quote spot check." },
    data_work: { label: "Manual data work", one: "Data work", what: "Work done by hand outside Claude: browser checks of blocked pages, pasted sources, blind coding." },
    direction: { label: "Direction", one: "Direction", what: "" }
  };
  var PANEL_ROLES = ["decision", "correction", "review", "data_work"];
  var PHASE_NAMES = {
    "setup": "Setup", "phase-0": "Phase 0 · Setup and logging", "phase-1": "Phase 1 · Data collection",
    "phase-2": "Phase 2 · Coding and analysis", "phase-3": "Phase 3 · Findings dashboard", "phase-4": "Phase 4 · Validation",
    "phase-5": "Phase 5 · Contributions timeline", "phase-6": "Phase 6 · Token usage", "phase-7": "Phase 7 · Publish",
    "phase-8": "Phase 8 · Evaluation"
  };
  var shortPhase = function (p) { return p === "setup" ? "Setup" : "Phase " + p.split("-")[1]; };

  var D, E = {}, charts = {};
  var byId = function (id) { return document.getElementById(id); };
  var css = function (name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); };

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function who(actor) {
    var s = el("span", { class: "who" });
    s.appendChild(el("span", { class: "dot " + actor, "aria-hidden": "true" }));
    s.appendChild(document.createTextNode(actor));
    return s;
  }

  function fmtTime(e) {
    if (e.time_precision === "date") return e.ts.slice(11, 16) === "00:00" ? "no time" : "~" + new Date(e.ts).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
    var d = new Date(e.ts);
    return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
  }

  function activePhases() {
    return D.phases.filter(function (p) {
      var a = D.summary[p].actors;
      return Object.keys(a).some(function (k) { return a[k] > 0; });
    });
  }
  function count(pred) { return D.entries.filter(pred).length; }

  /* ---------- headline + KPIs ---------- */
  function renderHead() {
    var prompts = count(function (e) { return e.type === "prompt"; });
    var byRole = {};
    PANEL_ROLES.forEach(function (r) { byRole[r] = count(function (e) { return e.actor === "Adi" && (e.roles || []).indexOf(r) >= 0; }); });
    var roleItems = count(function (e) { return e.actor === "Adi" && (e.roles || []).some(function (r) { return PANEL_ROLES.indexOf(r) >= 0; }); });
    var responses = count(function (e) { return e.type === "response"; });
    var handbacks = count(function (e) { return e.type === "handback"; });
    var commits = D.entries.filter(function (e) { return e.type === "commit"; });
    var adiCommits = commits.filter(function (e) { return e.actor === "Adi"; }).length;

    byId("headline").textContent = "Adi steered with " + prompts + " prompts and " + roleItems + " logged calls; Claude did the building";
    var clears = count(function (e) { return e.type === "clear"; });
    byId("dek").textContent = "Adi's " + roleItems + " calls are the decisions, corrections, reviews and manual data work logged in PROGRESS.md. Claude answered with " + responses + " responses and delegated work to subagents that sent back " + handbacks +
      " hand-backs. Adi cleared the context " + clears + " times between phases and made " + adiCommits + " of the " + commits.length +
      " commits. Times come from the logging hooks; PROGRESS.md times are hand-written and are used only where no hook event records the moment.";

    var tiles = [
      { id: "prompts", label: "Prompts by Adi", value: prompts, detail: handbacks + " subagent hand-backs not counted" },
      { id: "decision", label: "Decisions", value: byRole.decision, detail: "plan approvals, coding rules, publish choices" },
      { id: "correction", label: "Corrections", value: byRole.correction, detail: "problems Adi caught in Claude's work" },
      { id: "review", label: "Reviews", value: byRole.review, detail: "incl. the 5-quote browser spot check" },
      { id: "data_work", label: "Manual data work", value: byRole.data_work, detail: "browser checks, pasted sources, blind coding" }
    ];
    var wrap = byId("kpis");
    wrap.textContent = "";
    tiles.forEach(function (k) {
      var d = el("div", { class: "kpi", "data-kpi": k.id });
      d.appendChild(el("p", { class: "label" }, k.label));
      d.appendChild(el("p", { class: "value" }, String(k.value)));
      d.appendChild(el("p", { class: "detail" }, k.detail));
      wrap.appendChild(d);
    });
  }

  /* ---------- Adi's role panel ---------- */
  function renderRoles() {
    var wrap = byId("roles");
    PANEL_ROLES.forEach(function (r) {
      var items = D.entries.filter(function (e) { return e.actor === "Adi" && (e.roles || []).indexOf(r) >= 0; });
      var box = el("div", { class: "role", "data-role": r });
      var h = el("h3", null, ROLE_INFO[r].label);
      h.appendChild(el("small", null, items.length + (items.length === 1 ? " item" : " items")));
      box.appendChild(h);
      box.appendChild(el("p", { class: "what" }, ROLE_INFO[r].what));
      var ul = el("ul");
      if (!items.length) ul.appendChild(el("li", { class: "empty-role" }, "None logged."));
      items.forEach(function (e) {
        var li = el("li", { "data-id": e.id });
        li.appendChild(el("p", { class: "when" }, fmtTime(e) + " · " + shortPhase(e.phase)));
        li.appendChild(el("p", { class: "txt" }, e.summary));
        if (e.role_note && r === "correction") li.appendChild(el("p", { class: "why" }, "Correction: " + e.role_note));
        var b = el("button", { type: "button", class: "linkish", "data-goto": e.id }, "Show in timeline");
        b.addEventListener("click", function () { gotoEntry(e.id); });
        li.appendChild(b);
        ul.appendChild(li);
      });
      box.appendChild(ul);
      wrap.appendChild(box);
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

  function baseScales(horizontal) {
    var cat = { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--ink-2"), font: { size: 13 } } };
    var val = { grid: { color: css("--grid"), drawTicks: false }, border: { display: false }, beginAtZero: true,
                ticks: { color: css("--ink-2"), padding: 6, maxTicksLimit: 6, precision: 0 } };
    return horizontal ? { y: cat, x: val } : { x: cat, y: val };
  }

  function typeBreakdown(phase, actor) {
    var c = {};
    D.entries.forEach(function (e) { if (e.phase === phase && e.actor === actor) c[e.type] = (c[e.type] || 0) + 1; });
    return Object.keys(c).sort(function (a, b) { return c[b] - c[a]; }).map(function (t) { return c[t] + " " + TYPE_LABELS[t].toLowerCase() + (c[t] === 1 ? "" : "s"); });
  }

  function renderActorsChart(phases) {
    var actors = D.actors.filter(function (a) { return phases.some(function (p) { return D.summary[p].actors[a]; }); });
    var surface = css("--surface");
    var key = byId("actor-key");
    key.textContent = "";
    actors.forEach(function (a) {
      var li = el("li");
      li.appendChild(el("span", { class: "sw", style: "background:" + css(ACTOR_VAR[a]) }));
      li.appendChild(document.createTextNode(a));
      key.appendChild(li);
    });
    byId("actors-box").style.height = Math.max(220, phases.length * 40 + 40) + "px";
    if (charts.actors) charts.actors.destroy();
    charts.actors = new Chart(byId("chart-actors"), {
      type: "bar",
      data: {
        labels: phases.map(shortPhase),
        datasets: actors.map(function (a) {
          return {
            label: a, data: phases.map(function (p) { return D.summary[p].actors[a] || 0; }),
            backgroundColor: css(ACTOR_VAR[a]), hoverBackgroundColor: css(ACTOR_VAR[a]),
            borderColor: surface, borderWidth: { left: 0, right: 2, top: 0, bottom: 0 }, borderSkipped: false,
            borderRadius: 0, maxBarThickness: 24, categoryPercentage: 0.75, barPercentage: 0.95
          };
        })
      },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: "nearest", intersect: true },
        scales: (function () { var s = baseScales(true); s.x.stacked = true; s.y.stacked = true; return s; })(),
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(tooltipStyle(), {
            callbacks: {
              title: function (items) { return PHASE_NAMES[phases[items[0].dataIndex]]; },
              label: function (item) { return item.dataset.label + ": " + item.raw + " events"; },
              afterLabel: function (item) { return typeBreakdown(phases[item.dataIndex], item.dataset.label); }
            }
          })
        }
      }
    });
    asTable("chart-actors", ["Phase"].concat(actors), phases.map(function (p) {
      return [PHASE_NAMES[p]].concat(actors.map(function (a) { return D.summary[p].actors[a] || 0; }));
    }));
  }

  function simpleBar(id, key, phases, values, color, tip) {
    if (charts[key]) charts[key].destroy();
    charts[key] = new Chart(byId(id), {
      type: "bar",
      data: { labels: phases.map(shortPhase), datasets: [{ data: values, backgroundColor: color, hoverBackgroundColor: color,
        borderRadius: 4, borderSkipped: "start", maxBarThickness: 28, categoryPercentage: 0.7, barPercentage: 0.9 }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: baseScales(false),
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(tooltipStyle(), { displayColors: false, callbacks: {
            title: function (items) { return PHASE_NAMES[phases[items[0].dataIndex]]; },
            label: function (item) { return tip(phases[item.dataIndex], item.raw); }
          } })
        }
      }
    });
  }

  function loc(p, kind) { var l = D.summary[p].loc; return (l[kind + "_added"] || 0) + (l[kind + "_deleted"] || 0); }

  function renderPromptChart(phases) {
    var vals = phases.map(function (p) { return D.entries.filter(function (e) { return e.phase === p && e.type === "prompt"; }).length; });
    simpleBar("chart-prompts", "prompts", phases, vals, css("--a-adi"), function (p, v) { return v + " prompts by Adi"; });
    asTable("chart-prompts", ["Phase", "Adi's prompts"], phases.map(function (p, i) { return [PHASE_NAMES[p], vals[i]]; }));
  }

  function renderLocChart(phases) {
    var vals = phases.map(function (p) { return loc(p, "code") + loc(p, "docs"); });
    simpleBar("chart-loc", "loc", phases, vals, css("--zero"), function (p, v) {
      var l = D.summary[p].loc, s = D.summary[p].commits;
      return [v.toLocaleString("en-US") + " lines in code and docs", "code +" + (l.code_added || 0) + " −" + (l.code_deleted || 0) +
        ", docs +" + (l.docs_added || 0) + " −" + (l.docs_deleted || 0),
        "data +" + (l.data_added || 0) + " −" + (l.data_deleted || 0) + ", logs +" + (l.logs_added || 0),
        s + (s === 1 ? " commit" : " commits")];
    });
    asTable("chart-loc", ["Phase", "Commits", "Code +/−", "Docs +/−", "Data +/−", "Logs +/−"], phases.map(function (p) {
      var l = D.summary[p].loc, pm = function (k) { return "+" + (l[k + "_added"] || 0) + " / −" + (l[k + "_deleted"] || 0); };
      return [PHASE_NAMES[p], D.summary[p].commits, pm("code"), pm("docs"), pm("data"), pm("logs")];
    }));
  }

  function renderSummary(phases) {
    var cols = [
      ["Adi", "Prompts", function (p) { return cnt(p, "Adi", "prompt"); }],
      ["Adi", "Decisions", function (p) { return role(p, "decision"); }],
      ["Adi", "Corrections", function (p) { return role(p, "correction"); }],
      ["Adi", "Reviews", function (p) { return role(p, "review"); }],
      ["Adi", "Data work", function (p) { return role(p, "data_work"); }],
      ["Adi", "/clear", function (p) { return cnt(p, "Adi", "clear"); }],
      ["Claude", "Responses", function (p) { return cnt(p, "Claude", "response"); }],
      ["Claude", "Progress log", function (p) { return cnt(p, "Claude", "progress"); }],
      ["Subagents", "Hand-backs", function (p) { return cnt(p, "Subagent", "handback"); }],
      ["Claude-Cowork", "Entries", function (p) { return cnt(p, "Claude-Cowork", null); }],
      ["Git", "Commits", function (p) { return D.summary[p].commits; }],
      ["Git", "Lines (code + docs)", function (p) { return loc(p, "code") + loc(p, "docs"); }]
    ];
    function cnt(p, a, t) { return D.entries.filter(function (e) { return e.phase === p && e.actor === a && (!t || e.type === t); }).length; }
    function role(p, r) { return D.entries.filter(function (e) { return e.phase === p && e.actor === "Adi" && (e.roles || []).indexOf(r) >= 0; }).length; }

    var t = byId("summary");
    t.textContent = "";
    var thead = el("thead"), g = el("tr", { class: "grp" }), h = el("tr");
    g.appendChild(el("th"));
    var groups = [];
    cols.forEach(function (c) { if (!groups.length || groups[groups.length - 1][0] !== c[0]) groups.push([c[0], 0]); groups[groups.length - 1][1]++; });
    groups.forEach(function (gr) { g.appendChild(el("th", { colspan: gr[1], scope: "colgroup" }, gr[0])); });
    h.appendChild(el("th", { scope: "col" }, "Phase"));
    cols.forEach(function (c) { h.appendChild(el("th", { scope: "col" }, c[1])); });
    thead.appendChild(g); thead.appendChild(h); t.appendChild(thead);
    var tb = el("tbody"), totals = cols.map(function () { return 0; });
    phases.forEach(function (p) {
      var tr = el("tr", { "data-phase": p });
      tr.appendChild(el("td", null, PHASE_NAMES[p]));
      cols.forEach(function (c, i) {
        var v = c[2](p);
        totals[i] += v;
        tr.appendChild(el("td", c[0] === "Adi" ? { class: "adi" } : null, v.toLocaleString("en-US")));
      });
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    var tf = el("tfoot"), tr = el("tr");
    tr.appendChild(el("td", null, "Total"));
    totals.forEach(function (v, i) { tr.appendChild(el("td", cols[i][0] === "Adi" ? { class: "adi" } : null, v.toLocaleString("en-US"))); });
    tf.appendChild(tr);
    t.appendChild(tf);
  }

  function renderCharts() {
    var phases = activePhases();
    renderActorsChart(phases);
    renderPromptChart(phases);
    renderLocChart(phases);
  }

  /* ---------- timeline ---------- */
  var F = { q: "", actor: "", phase: "", type: "", role: "" };

  function fillSelect(id, values, label) {
    var s = byId(id);
    values.forEach(function (v) { s.appendChild(el("option", { value: v }, label(v))); });
  }

  function matches(e) {
    if (F.actor && e.actor !== F.actor) return false;
    if (F.phase && e.phase !== F.phase) return false;
    if (F.type && e.type !== F.type) return false;
    if (F.role && (e.roles || []).indexOf(F.role) < 0) return false;
    if (F.q) {
      var hay = (e.summary + " " + (e.detail || "")).toLowerCase();
      if (F.q.toLowerCase().split(/\s+/).some(function (w) { return w && hay.indexOf(w) < 0; })) return false;
    }
    return true;
  }

  function sourceText(e) {
    var parts = ["Source: " + e.source];
    if (e.ts_source === "hook (matched prompt)") parts.push("ordered by the hook time of the prompt it records (" + e.prompt_ref + "); written " + e.written);
    else if (e.time_precision === "date") parts.push("PROGRESS.md gives only a date (" + e.written + "); placed after the entry above it in the file");
    else if (e.ts_source === "progress") parts.push("time as written in PROGRESS.md (" + e.written + ")");
    if (e.relabeled_from) parts.push("the hook logged this as actor " + e.relabeled_from + "; relabeled as a subagent hand-back");
    if (e.actor_evidence) parts.push("actor: " + e.actor_evidence);
    if (e.role_note) parts.push("role note: " + e.role_note);
    return parts.join(" · ");
  }

  function entryNode(e) {
    var li = el("li", { class: "ev" + (e.actor === "Adi" ? " mine" : ""), id: e.id, "data-actor": e.actor, "data-phase": e.phase, "data-type": e.type });
    li.appendChild(el("span", { class: "t" }, fmtTime(e)));
    var rail = el("span", { class: "rail", "aria-hidden": "true" });
    rail.appendChild(el("span", { class: "dot " + e.actor }));
    li.appendChild(rail);
    var body = el("div", { class: "body" });
    var meta = el("p", { class: "meta" });
    meta.appendChild(el("span", { class: "tm" }, fmtTime(e)));
    meta.appendChild(who(e.actor));
    meta.appendChild(el("span", null, TYPE_LABELS[e.type]));
    (e.roles || []).forEach(function (r) { meta.appendChild(el("span", { class: "pill role", "data-role": r }, ROLE_INFO[r].one)); });
    if (e.ts_source === "progress" && e.time_precision !== "date") meta.appendChild(el("span", { class: "pill", title: "Hand-written time from PROGRESS.md" }, "written time"));
    body.appendChild(meta);
    body.appendChild(el("p", { class: "sum" }, e.summary));
    var det = el("details");
    det.appendChild(el("summary", null, e.detail && e.detail !== e.summary ? "Full text and source" : "Source"));
    if (e.detail && e.detail !== e.summary) det.appendChild(el("pre", { class: "full" }, e.detail));
    det.appendChild(el("p", { class: "src" }, sourceText(e)));
    body.appendChild(det);
    li.appendChild(body);
    return li;
  }

  function renderTimeline() {
    var ol = byId("tl");
    ol.textContent = "";
    var shown = D.entries.filter(matches), last = null;
    shown.forEach(function (e) {
      if (e.phase !== last) {
        ol.appendChild(el("li", { class: "divider", "data-phase": e.phase }, PHASE_NAMES[e.phase]));
        last = e.phase;
      }
      ol.appendChild(entryNode(e));
    });
    if (!shown.length) ol.appendChild(el("li", { class: "empty" }, "No entries match these filters."));
    byId("count").textContent = "Showing " + shown.length + " of " + D.entries.length + " entries";
  }

  function initFilters() {
    fillSelect("f-actor", D.actors.filter(function (a) { return D.entries.some(function (e) { return e.actor === a; }); }), function (v) { return v; });
    fillSelect("f-phase", activePhases(), function (v) { return PHASE_NAMES[v]; });
    fillSelect("f-type", D.types.filter(function (t) { return D.entries.some(function (e) { return e.type === t; }); }), function (v) { return TYPE_LABELS[v]; });
    fillSelect("f-role", D.roles, function (v) { return "Adi: " + ROLE_INFO[v].one; });
    var bind = function (id, k, ev) { byId(id).addEventListener(ev || "change", function () { F[k] = byId(id).value; renderTimeline(); }); };
    bind("q", "q", "input"); bind("f-actor", "actor"); bind("f-phase", "phase"); bind("f-type", "type"); bind("f-role", "role");
    byId("reset").addEventListener("click", resetFilters);
  }

  function resetFilters() {
    F = { q: "", actor: "", phase: "", type: "", role: "" };
    ["q", "f-actor", "f-phase", "f-type", "f-role"].forEach(function (id) { byId(id).value = ""; });
    renderTimeline();
  }

  function gotoEntry(id) {
    resetFilters();
    var li = byId(id);
    if (!li) return;
    li.querySelector("details").open = true;
    var list = byId("tl");
    list.scrollTop = li.offsetTop - list.offsetTop - 48;
    byId("h-timeline").scrollIntoView({ block: "start" });
    li.classList.add("flash");
    setTimeout(function () { li.classList.remove("flash"); }, 2400);
  }

  /* ---------- Q&A ---------- */
  var QA = { q: "", phase: "" };

  function turnNode(e, isQ) {
    var d = el("div", { class: "turn" + (isQ ? " q" : ""), "data-actor": e.actor });
    d.appendChild(who(e.actor));
    d.appendChild(el("p", { class: "txt" }, e.summary));
    if (e.detail && e.detail !== e.summary) {
      var det = el("details");
      det.appendChild(el("summary", null, "Full text"));
      det.appendChild(el("pre", { class: "full" }, e.detail));
      d.appendChild(det);
    }
    return d;
  }

  function renderQA() {
    var ol = byId("qa");
    ol.textContent = "";
    var words = QA.q.toLowerCase().split(/\s+/).filter(Boolean);
    var shown = D.qa.filter(function (pair) {
      if (QA.phase && pair.phase !== QA.phase) return false;
      if (!words.length) return true;
      var hay = [pair.prompt].concat(pair.turns).map(function (id) { return E[id].detail || E[id].summary; }).join(" ").toLowerCase();
      return words.every(function (w) { return hay.indexOf(w) >= 0; });
    });
    shown.forEach(function (pair) {
      var p = E[pair.prompt], li = el("li", { class: "qa-item", "data-prompt": pair.prompt, "data-phase": pair.phase });
      var turns = pair.turns.map(function (id) { return E[id]; });
      var hb = turns.filter(function (t) { return t.type === "handback"; }).length;
      var head = el("header");
      head.appendChild(el("span", null, fmtTime(p) + " ET"));
      head.appendChild(el("span", null, PHASE_NAMES[pair.phase]));
      head.appendChild(el("span", null, turns.length + (turns.length === 1 ? " reply" : " replies") + (hb ? ", incl. " + hb + " subagent hand-back" + (hb === 1 ? "" : "s") : "")));
      li.appendChild(head);
      li.appendChild(turnNode(p, true));
      if (turns.length) li.appendChild(turnNode(turns[0], false));
      if (turns.length > 1) {
        var more = el("details", { class: "more" });
        more.appendChild(el("summary", null, "Show " + (turns.length - 1) + " more " + (turns.length === 2 ? "turn" : "turns")));
        turns.slice(1).forEach(function (t) { more.appendChild(turnNode(t, false)); });
        li.appendChild(more);
      }
      if (!turns.length) li.appendChild(el("p", { class: "note" }, "No response logged yet."));
      ol.appendChild(li);
    });
    if (!shown.length) ol.appendChild(el("li", { class: "empty" }, "No prompts match."));
    byId("qa-count").textContent = "Showing " + shown.length + " of " + D.qa.length + " prompts";
  }

  function initQA() {
    fillSelect("qa-phase", activePhases().filter(function (p) { return D.qa.some(function (q) { return q.phase === p; }); }), function (v) { return PHASE_NAMES[v]; });
    byId("qa-q").addEventListener("input", function () { QA.q = byId("qa-q").value; renderQA(); });
    byId("qa-phase").addEventListener("change", function () { QA.phase = byId("qa-phase").value; renderQA(); });
  }

  /* ---------- theme ---------- */
  function currentTheme() {
    var t = document.documentElement.dataset.theme;
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function syncThemeButton() { byId("theme-btn").textContent = currentTheme() === "dark" ? "Light mode" : "Dark mode"; }
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
  fetch("data/timeline.json").then(function (r) {
    if (!r.ok) throw new Error("data/timeline.json returned HTTP " + r.status);
    return r.json();
  }).then(function (data) {
    D = data;
    D.entries.forEach(function (e) { E[e.id] = e; });
    initTheme();
    renderHead();
    renderRoles();
    renderCharts();
    renderSummary(activePhases());
    initFilters();
    renderTimeline();
    initQA();
    renderQA();
    document.body.dataset.ready = "true";
  }).catch(function (err) {
    var main = byId("main");
    var p = el("p", { class: "empty", role: "alert" }, "The timeline data could not be loaded (" + err.message + "). Serve the docs/ folder over HTTP, for example with python3 -m http.server, and reload.");
    main.insertBefore(p, main.firstChild);
    document.body.dataset.ready = "error";
  });
})();
