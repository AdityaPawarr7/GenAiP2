/* Token usage dashboard (Phase 6). Reads data/tokens.json, built by scripts/tokens.py from the
   Claude Code transcripts (main sessions + subagents) and logs/events.jsonl.
   Every number on the page is computed from that file at load time. */
(function () {
  "use strict";

  var ACT = {
    gathering_data: { label: "Gathering data", v: "--act-gather" },
    processing_data: { label: "Processing data", v: "--act-process" },
    writing_code: { label: "Writing code", v: "--act-code" },
    running_validation: { label: "Running validation", v: "--act-valid" },
    planning_docs: { label: "Planning and docs", v: "--act-plan" }
  };
  var PHASE_NAMES = {
    "setup": "Setup", "phase-0": "Phase 0 · Setup and logging", "phase-1": "Phase 1 · Data collection",
    "phase-2": "Phase 2 · Coding and analysis", "phase-3": "Phase 3 · Findings dashboard", "phase-4": "Phase 4 · Validation",
    "phase-5": "Phase 5 · Contributions timeline", "phase-6": "Phase 6 · Token usage", "phase-7": "Phase 7 · Publish",
    "phase-8": "Phase 8 · Evaluation"
  };
  var shortPhase = function (p) { return p === "setup" ? "Setup" : "Phase " + p.split("-")[1]; };

  var D, M = "total", charts = {};
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

  /* ---------- formatting ---------- */
  function tok(n) {
    if (n === null || n === undefined) return "–";
    var a = Math.abs(n);
    if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e8 ? 0 : 1) + "M";
    if (a >= 1e3) return (n / 1e3).toFixed(a >= 1e4 ? 0 : 1) + "k";
    return String(Math.round(n));
  }
  function usd(v) { return "$" + (v >= 100 ? v.toFixed(0) : v >= 1 ? v.toFixed(2) : v.toFixed(3)); }
  function num(n) { return Number(n).toLocaleString("en-US"); }
  function pct(a, b) { return b ? (100 * a / b) : 0; }
  function pctTxt(a, b) { var p = pct(a, b); return (p >= 10 || p === 0 ? p.toFixed(0) : p.toFixed(1)) + "%"; }
  function fm(v) { return M === "total" ? tok(v) : usd(v); }
  function unit() { return M === "total" ? "tokens" : "est. API cost"; }
  function when(ts) {
    return new Date(ts).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
  }
  function hm(ts) { return new Date(ts).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" }); }

  /* ---------- headline + KPIs ---------- */
  function sortedActs(metric) {
    return D.activities.filter(function (a) { return D.by_activity[a]; })
      .sort(function (a, b) { return D.by_activity[b][metric] - D.by_activity[a][metric]; });
  }

  function tile(box, label, value, detail) {
    var t = el("div", { class: "kpi" });
    t.appendChild(el("p", { class: "label" }, label));
    t.appendChild(el("p", { class: "value" }, value));
    if (detail) t.appendChild(el("p", { class: "detail" }, detail));
    box.appendChild(t);
  }

  function renderHead() {
    var T = D.totals, top = sortedActs("total")[0], topV = D.by_activity[top];
    var sub = D.by_thread.subagent || { total: 0, cost_usd: 0 };
    var cs = D.context.summary.clear;
    byId("headline").textContent = ACT[top].label + " used " + pctTxt(topV.total, T.total) + " of all tokens, most of it in Phase 1 subagents";
    byId("dek").textContent = tok(T.total) + " tokens over " + num(D.counts.messages) + " Claude Code API calls (about " + usd(T.cost_usd) +
      " at API list prices). The calls come from the session transcripts, subagents included, through " + when(D.transcripts_through) +
      ". Cache reads are " + pctTxt(T.cache_read_input_tokens, T.total) + " of the tokens: most of the volume is the model re-reading its own context.";

    var k = byId("kpis");
    k.textContent = "";
    tile(k, "Total tokens", tok(T.total), num(D.counts.messages) + " API calls in " + D.counts.sessions + " sessions");
    tile(k, "Estimated API cost", usd(T.cost_usd), "At Opus 5.5 list prices. Not the plan's bill.");
    tile(k, "Cache hit rate", D.cache_hit_pct.toFixed(1) + "%", "of input tokens were read from cache");
    tile(k, "Subagents' share", pctTxt(sub.total, T.total), tok(sub.total) + " tokens from " + D.counts.subagents + " subagents, all in Phase 1");
    tile(k, "/clear", String(D.counts.clears), cs.measured ? "Average context fell from " + tok(cs.avg_before) + " to " + tok(cs.avg_after) : "");

    var ty = byId("types"), P = D.pricing.usd_per_million;
    ty.textContent = "";
    var rows = [
      ["Cache reads", T.cache_read_input_tokens, T.cache_read_input_tokens * P.cache_read / 1e6],
      ["Cache writes", T.cache_creation_input_tokens, null],
      ["Uncached input", T.input_tokens, T.input_tokens * P.input / 1e6],
      ["Output", T.output_tokens, T.output_tokens * P.output / 1e6]
    ];
    var known = rows.reduce(function (s, r) { return s + (r[2] || 0); }, 0);
    rows[1][2] = T.cost_usd - known; // 5-minute and 1-hour writes are priced differently; the rest of the total
    rows.forEach(function (r) {
      tile(ty, r[0], tok(r[1]), pctTxt(r[1], T.total) + " of tokens · " + pctTxt(r[2], T.cost_usd) + " of est. cost (" + usd(r[2]) + ")");
    });
  }

  /* ---------- chart helpers ---------- */
  function tooltipStyle() {
    return {
      backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: css("--ink-2"),
      borderColor: css("--axis"), borderWidth: 1, padding: 10, cornerRadius: 8,
      titleFont: { size: 15, weight: "600" }, bodyFont: { size: 13 }
    };
  }
  function baseScales(horizontal, tickFmt) {
    var cat = { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--ink-2"), font: { size: 13 } } };
    var val = { grid: { color: css("--grid"), drawTicks: false }, border: { display: false }, beginAtZero: true,
                ticks: { color: css("--ink-2"), padding: 6, maxTicksLimit: 6, callback: tickFmt || function (v) { return fm(v); } } };
    return horizontal ? { y: cat, x: val } : { x: cat, y: val };
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
  // Direct labels at the end of horizontal bars (selective: only the charts with a handful of bars).
  var endLabels = {
    id: "endLabels",
    afterDatasetsDraw: function (chart, args, opts) {
      if (!opts || !opts.text) return;
      var ctx = chart.ctx, meta = chart.getDatasetMeta(chart.data.datasets.length - 1);
      ctx.save();
      ctx.font = "13px system-ui, -apple-system, sans-serif";
      ctx.fillStyle = css("--ink-2");
      ctx.textBaseline = "middle";
      meta.data.forEach(function (bar, i) { ctx.fillText(opts.text(i), bar.x + 8, bar.y); });
      ctx.restore();
    }
  };
  function hbar(id, key, labels, values, colors, label, tipLines, opts) {
    if (charts[key]) charts[key].destroy();
    opts = opts || {};
    charts[key] = new Chart(byId(id), {
      type: "bar",
      data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, hoverBackgroundColor: colors,
        borderRadius: 4, borderSkipped: "start", maxBarThickness: 26, categoryPercentage: 0.75, barPercentage: 0.9 }] },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        layout: { padding: { right: opts.padRight === undefined ? 96 : opts.padRight } },
        scales: baseScales(true, opts.tickFmt),
        plugins: {
          legend: { display: false },
          endLabels: { text: label },
          tooltip: Object.assign(tooltipStyle(), { displayColors: false, callbacks: {
            title: function (items) { return opts.title ? opts.title(items[0].dataIndex) : labels[items[0].dataIndex]; },
            label: function (item) { return tipLines(item.dataIndex); }
          } })
        }
      },
      plugins: [endLabels]
    });
  }

  /* ---------- Q1: steps ---------- */
  function renderSteps() {
    var acts = sortedActs(M), T = D.totals;
    var vals = acts.map(function (a) { return D.by_activity[a][M]; });
    var colors = acts.map(function (a) { return css(ACT[a].v); });
    function tip(a) {
      var v = D.by_activity[a];
      return [tok(v.total) + " tokens (" + pctTxt(v.total, T.total) + ")", usd(v.cost_usd) + " est. API cost (" + pctTxt(v.cost_usd, T.cost_usd) + ")",
        num(v.messages) + " calls", "cache reads " + tok(v.cache_read_input_tokens) + " · output " + tok(v.output_tokens)];
    }
    hbar("chart-activity", "activity", acts.map(function (a) { return ACT[a].label; }), vals, colors,
      function (i) { return fm(vals[i]) + " · " + pctTxt(vals[i], T[M]); }, function (i) { return tip(acts[i]); });
    asTable("chart-activity", ["Step", "Tokens", "Share", "Est. cost", "Share of cost", "Calls"], acts.map(function (a) {
      var v = D.by_activity[a];
      return [ACT[a].label, num(v.total), pctTxt(v.total, T.total), usd(v.cost_usd), pctTxt(v.cost_usd, T.cost_usd), v.messages];
    }));

    var per = acts.map(function (a) { var v = D.by_activity[a]; return v[M] / v.messages; });
    var order = acts.map(function (a, i) { return i; }).sort(function (x, y) { return per[y] - per[x]; });
    var pActs = order.map(function (i) { return acts[i]; }), pVals = order.map(function (i) { return per[i]; });
    hbar("chart-percall", "percall", pActs.map(function (a) { return ACT[a].label; }), pVals, pActs.map(function (a) { return css(ACT[a].v); }),
      function (i) { return fm(pVals[i]) + " per call"; },
      function (i) { var v = D.by_activity[pActs[i]]; return [tok(v.total / v.messages) + " tokens per call", usd(v.cost_usd / v.messages) + " est. per call", num(v.messages) + " calls"]; },
      { padRight: 110 });
    asTable("chart-percall", ["Step", "Tokens per call", "Est. cost per call", "Calls"], pActs.map(function (a) {
      var v = D.by_activity[a];
      return [ACT[a].label, num(Math.round(v.total / v.messages)), usd(v.cost_usd / v.messages), v.messages];
    }));

    renderPhaseChart();
    byId("metric-hint").textContent = M === "total" ? "All four token types added up. Cache reads dominate this count." :
      "Each token type priced at its Opus 5.5 API rate, so cache reads weigh far less than output.";
  }

  function renderPhaseChart() {
    var phases = D.phases.filter(function (p) { return D.phase_activity[p]; });
    var acts = D.activities.filter(function (a) { return D.by_activity[a]; });
    var key = byId("act-key");
    key.textContent = "";
    acts.forEach(function (a) {
      var li = el("li");
      li.appendChild(el("span", { class: "sw", style: "background:" + css(ACT[a].v) }));
      li.appendChild(document.createTextNode(ACT[a].label));
      key.appendChild(li);
    });
    byId("phase-box").style.height = Math.max(240, phases.length * 38 + 50) + "px";
    var surface = css("--surface");
    if (charts.phase) charts.phase.destroy();
    var cell = function (p, a) { return (D.phase_activity[p][a] || {})[M] || 0; };
    charts.phase = new Chart(byId("chart-phase"), {
      type: "bar",
      data: {
        labels: phases.map(shortPhase),
        datasets: acts.map(function (a) {
          return { label: ACT[a].label, act: a, data: phases.map(function (p) { return cell(p, a); }),
            backgroundColor: css(ACT[a].v), hoverBackgroundColor: css(ACT[a].v),
            borderColor: surface, borderWidth: { left: 0, right: 2, top: 0, bottom: 0 }, borderSkipped: false,
            borderRadius: 0, maxBarThickness: 24, categoryPercentage: 0.75, barPercentage: 0.95 };
        })
      },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: "nearest", intersect: true },
        scales: (function () {
          var s = baseScales(true), top = Math.max.apply(null, phases.map(function (p) { return D.by_phase[p][M]; }));
          var mag = Math.pow(10, Math.floor(Math.log10(top)));
          s.x.stacked = true; s.y.stacked = true; s.x.max = Math.ceil(top / mag * 10) / 10 * mag;
          return s;
        })(),
        plugins: {
          legend: { display: false },
          tooltip: Object.assign(tooltipStyle(), { callbacks: {
            title: function (items) { return PHASE_NAMES[phases[items[0].dataIndex]]; },
            label: function (item) {
              var p = phases[item.dataIndex], v = D.phase_activity[p][item.dataset.act];
              return item.dataset.label + ": " + fm(item.raw) + " (" + pctTxt(item.raw, D.by_phase[p][M]) + " of the phase)";
            },
            afterLabel: function (item) {
              var v = D.phase_activity[phases[item.dataIndex]][item.dataset.act];
              return M === "total" ? usd(v.cost_usd) + " est. · " + v.messages + " calls" : tok(v.total) + " tokens · " + v.messages + " calls";
            }
          } })
        }
      }
    });
    asTable("chart-phase", ["Phase"].concat(acts.map(function (a) { return ACT[a].label; })).concat(["Total " + unit()]), phases.map(function (p) {
      return [PHASE_NAMES[p]].concat(acts.map(function (a) { return fm(cell(p, a)); })).concat([fm(D.by_phase[p][M])]);
    }));
  }

  /* ---------- Q2: context ---------- */
  function eventIndex(series, ts) {
    var t = Date.parse(ts);
    for (var i = 0; i < series.length; i++) if (Date.parse(series[i].ts) > t) return i - 0.5;
    return series.length - 0.5;
  }

  var markers = {
    id: "markers",
    afterDatasetsDraw: function (chart, args, opts) {
      var ctx = chart.ctx, a = chart.chartArea, x = chart.scales.x;
      ctx.save();
      (opts.events || []).forEach(function (e) {
        var px = x.getPixelForValue(e.x);
        if (px < a.left || px > a.right) return;
        ctx.strokeStyle = e.color; ctx.lineWidth = 2; ctx.setLineDash([5, 4]);
        ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
        ctx.setLineDash([]); ctx.fillStyle = e.color;
        ctx.beginPath(); ctx.moveTo(px - 5, a.top - 8); ctx.lineTo(px + 5, a.top - 8); ctx.lineTo(px, a.top - 1); ctx.closePath(); ctx.fill();
      });
      var act = chart.tooltip && chart.tooltip.getActiveElements && chart.tooltip.getActiveElements();
      if (act && act.length) { // crosshair
        var cx = act[0].element.x;
        ctx.strokeStyle = css("--axis"); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(cx, a.top); ctx.lineTo(cx, a.bottom); ctx.stroke();
      }
      ctx.restore();
    }
  };

  function renderContext() {
    var C = D.context, S = C.series;
    var evs = C.events.map(function (e) {
      return { x: eventIndex(S, e.ts), color: css(e.type === "clear" ? "--clear-mark" : "--compact-mark"), e: e };
    });
    var key = byId("ctx-key");
    key.textContent = "";
    var items = [["line", css("--accent"), "Context size per main-thread call"],
      ["dash", css("--clear-mark"), "/clear (" + D.counts.clears + ")"],
      ["dash", css("--compact-mark"), "/compact (" + D.counts.compacts + (D.counts.compacts ? ")" : ", none yet)")]];
    items.forEach(function (it) {
      var li = el("li"), s = el("span", { class: it[0], style: "border-color:" + it[1] });
      li.appendChild(s); li.appendChild(document.createTextNode(it[2])); key.appendChild(li);
    });
    if (charts.context) charts.context.destroy();
    var accent = css("--accent");
    charts.context = new Chart(byId("chart-context"), {
      type: "line",
      data: { datasets: [{ label: "Context", data: S.map(function (p, i) { return { x: i, y: p.context }; }),
        borderColor: accent, backgroundColor: accent, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5,
        pointHoverBackgroundColor: accent, pointHoverBorderColor: css("--surface"), pointHoverBorderWidth: 2, tension: 0 }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false, parsing: false,
        layout: { padding: { top: 10 } },
        interaction: { mode: "index", intersect: false, axis: "x" },
        scales: {
          x: { type: "linear", min: -0.5, max: S.length - 0.5, grid: { display: false }, border: { color: css("--axis") },
               ticks: { color: css("--ink-2"), maxTicksLimit: 8, maxRotation: 0, callback: function (v) {
                 var i = Math.round(v); if (i !== v || !S[i]) return "";
                 return [hm(S[i].ts), new Date(S[i].ts).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "America/New_York" })];
               } } },
          y: { beginAtZero: true, grid: { color: css("--grid"), drawTicks: false }, border: { display: false },
               ticks: { color: css("--ink-2"), padding: 6, maxTicksLimit: 6, callback: function (v) { return tok(v); } } }
        },
        plugins: {
          legend: { display: false },
          markers: { events: evs },
          tooltip: Object.assign(tooltipStyle(), { displayColors: false, callbacks: {
            title: function (items) { return when(S[items[0].parsed.x].ts); },
            label: function (item) { return "Context: " + num(item.parsed.y) + " tokens"; },
            afterLabel: function (item) { var p = S[item.parsed.x]; return "Session " + p.session + " · " + PHASE_NAMES[p.phase]; }
          } })
        }
      },
      plugins: [markers]
    });
    attachMarkerTips(charts.context, evs);
    asTable("chart-context", ["#", "Time", "Session", "Phase", "Context tokens"], S.map(function (p, i) {
      return [i + 1, when(p.ts), p.session, shortPhase(p.phase), num(p.context)];
    }));

    var cs = C.summary.clear, k = byId("ctx-kpis");
    k.textContent = "";
    tile(k, "Context before a /clear", cs.measured ? tok(cs.avg_before) : "–", "Average of the last 5 calls before each of " + cs.measured + " clears");
    tile(k, "Context after a /clear", cs.measured ? tok(cs.avg_after) : "–", cs.measured ? pctTxt(cs.avg_before - cs.avg_after, cs.avg_before) + " smaller (first 5 calls of the new session)" : "");
    var saved = cs.tokens_saved_est + (C.summary.compact.tokens_saved_est || 0);
    tile(k, "Tokens not re-read (est.)", tok(saved), "about " + usd(saved * D.pricing.usd_per_million.cache_read / 1e6) + " of cache reads at $0.20/M");

    byId("ctx-note").textContent = "Before and after are averages of " + D.rules.context_window_turns + " main-thread calls. “Not re-read” adds, for every call until the next event, how far it sat below the pre-event average: an estimate of what carrying the old context would have cost. " +
      (D.counts.compacts ? "" : "No /compact has run in this project yet; one will appear here, and on the chart, after the next rebuild of tokens.json.");
    renderCtxTable();
  }

  function attachMarkerTips(chart, evs) {
    var tip = byId("tip"), canvas = chart.canvas;
    canvas.onmousemove = function (ev) {
      var r = canvas.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top, a = chart.chartArea;
      var hit = null;
      evs.forEach(function (m) { var px = chart.scales.x.getPixelForValue(m.x); if (Math.abs(px - x) <= 5 && y >= a.top - 10 && y <= a.bottom) hit = m; });
      if (!hit) { tip.hidden = true; return; }
      var e = hit.e;
      tip.textContent = "";
      tip.appendChild(el("strong", null, "/" + e.type + " · " + when(e.ts)));
      tip.appendChild(el("span", null, e.before_avg !== null && e.after_avg !== null
        ? "Context " + tok(e.before_avg) + " → " + tok(e.after_avg) + " (" + (e.change_pct > 0 ? "+" : "") + e.change_pct.toFixed(1) + "%)"
        : "No calls on one side to compare"));
      tip.hidden = false;
      tip.style.left = Math.min(ev.clientX + 14, window.innerWidth - 270) + "px";
      tip.style.top = (ev.clientY + 14) + "px";
    };
    canvas.onmouseleave = function () { tip.hidden = true; };
  }

  function renderCtxTable() {
    var t = byId("ctx-table");
    t.textContent = "";
    var head = [["When", ""], ["Event", ""], ["Phase", ""], ["Before (avg of 5)", "num"], ["After (avg of 5)", "num"], ["Change", "num"],
      ["Calls until next event", "num"], ["Tokens not re-read (est.)", "num"]];
    var tr = el("tr");
    head.forEach(function (h) { tr.appendChild(el("th", { scope: "col", class: h[1] }, h[0])); });
    t.appendChild(el("thead")).appendChild(tr);
    var tb = el("tbody");
    D.context.events.forEach(function (e) {
      var r = el("tr");
      r.appendChild(el("td", null, when(e.ts)));
      var td = el("td"), tag = el("span", { class: "tag " + e.type });
      tag.appendChild(el("span", { class: "ln", "aria-hidden": "true" }));
      tag.appendChild(el("span", { class: "t" }, "/" + e.type));
      td.appendChild(tag); r.appendChild(td);
      r.appendChild(el("td", null, e.phase ? shortPhase(e.phase) : "–"));
      r.appendChild(el("td", { class: "num" }, tok(e.before_avg)));
      r.appendChild(el("td", { class: "num" }, tok(e.after_avg)));
      r.appendChild(el("td", { class: "num down" }, e.change_pct === null ? "–" : (e.change_pct > 0 ? "+" : "") + e.change_pct.toFixed(1) + "%"));
      r.appendChild(el("td", { class: "num" }, String(e.turns_until_next)));
      r.appendChild(el("td", { class: "num" }, e.tokens_saved_est === null ? "–" : tok(e.tokens_saved_est)));
      tb.appendChild(r);
    });
    t.appendChild(tb);
  }

  /* ---------- Q3: subagents ---------- */
  function shortDesc(d) { return d.replace(/^Collect (raw|AI policies):\s*/i, ""); }

  function renderSubagents() {
    var p1 = D.phase_thread["phase-1"] || {}, main = p1.main || { total: 0, cost_usd: 0, messages: 0 }, sub = p1.subagent || { total: 0, cost_usd: 0, messages: 0 };
    var all = main[M] + sub[M], A = D.subagents.filter(function (a) { return a.phase === "phase-1"; });
    byId("sub-sub").textContent = A.length + " subagents did Phase 1's data collection, two institutions each, in " +
      new Set(A.map(function (a) { return a.session; })).size + " batches. They used " + tok(sub.total) + " tokens (" + pctTxt(sub.total, main.total + sub.total) +
      " of Phase 1, " + pctTxt(sub.total, D.totals.total) + " of the whole project) for an estimated " + usd(sub.cost_usd) + " of Phase 1's " + usd(main.cost_usd + sub.cost_usd) + ".";

    var labels = ["Main thread", "Subagents"], vals = [main[M], sub[M]], cols = [css("--main-thread"), css("--accent")];
    hbar("chart-p1", "p1", labels, vals, cols, function (i) { return fm(vals[i]) + " · " + pctTxt(vals[i], all); }, function (i) {
      var v = [main, sub][i];
      return [tok(v.total) + " tokens", usd(v.cost_usd) + " est. API cost", num(v.messages) + " calls"];
    }, { padRight: 104 });
    asTable("chart-p1", ["Thread", "Tokens", "Est. cost", "Calls"], [["Main thread", num(main.total), usd(main.cost_usd), main.messages], ["Subagents", num(sub.total), usd(sub.cost_usd), sub.messages]]);

    var searches = 0, bash = 0, out = 0, reads = 0, calls = 0;
    A.forEach(function (a) { searches += a.tool_calls.WebSearch || 0; bash += a.tool_calls.Bash || 0; out += a.output_tokens; reads += a.cache_read_input_tokens; calls += a.messages; });
    var f = byId("sub-facts");
    f.textContent = "";
    [["Each subagent averaged " + tok(sub.total / A.length) + " tokens", " (about " + usd(sub.cost_usd / A.length) + ")."],
     [num(searches) + " web searches and " + num(bash) + " shell commands", ", mostly downloading and grepping department pages and syllabi."],
     ["Each call re-read about " + tok(reads / calls) + " tokens of cached context", ": every page a subagent read stayed in its context for the rest of its run."],
     ["They wrote only " + tok(out) + " output tokens", " (" + pctTxt(out, sub.total) + " of their total). Reading cost far more than writing."]
    ].forEach(function (x) { var li = el("li"); li.appendChild(document.createTextNode(x[0])); li.appendChild(el("span", null, x[1])); f.appendChild(li); });

    byId("agents-box").style.height = Math.max(240, A.length * 26 + 50) + "px";
    var aVals = A.map(function (a) { return a[M]; });
    hbar("chart-agents", "agents", A.map(function (a) { return shortDesc(a.description); }), aVals, A.map(function () { return css("--accent"); }),
      function (i) { return fm(aVals[i]); }, function (i) {
        var a = A[i], mins = Math.round((Date.parse(a.end) - Date.parse(a.start)) / 60000);
        return [tok(a.total) + " tokens · " + usd(a.cost_usd) + " est.", num(a.messages) + " calls over " + mins + " min",
          (a.tool_calls.WebSearch || 0) + " web searches · " + (a.tool_calls.Bash || 0) + " shell commands", "Launched from session " + a.session + " at " + hm(a.start)];
      }, { padRight: 60, title: function (i) { return A[i].description; } });
    asTable("chart-agents", ["Subagent task", "Session", "Started", "Calls", "Web searches", "Shell commands", "Tokens", "Est. cost"], A.map(function (a) {
      return [a.description, a.session, hm(a.start), a.messages, a.tool_calls.WebSearch || 0, a.tool_calls.Bash || 0, num(a.total), usd(a.cost_usd)];
    }));
  }

  /* ---------- sessions ---------- */
  function renderSessions() {
    var t = byId("sessions");
    t.textContent = "";
    var head = [["Session", ""], ["Started", ""], ["Phases", ""], ["Main calls", "num"], ["Subagent calls", "num"], ["Peak context", "num"],
      ["Tokens", "num"], ["Est. cost", "num"], ["Ended by", ""]];
    var tr = el("tr");
    head.forEach(function (h) { tr.appendChild(el("th", { scope: "col", class: h[1] }, h[0])); });
    t.appendChild(el("thead")).appendChild(tr);
    var tb = el("tbody"), tot = { m: 0, s: 0, t: 0, c: 0 };
    D.sessions.forEach(function (s) {
      var r = el("tr", { "data-session": s.session });
      r.appendChild(el("td", null, s.session));
      r.appendChild(el("td", null, when(s.start)));
      r.appendChild(el("td", null, s.phases.map(shortPhase).join(", ")));
      r.appendChild(el("td", { class: "num" }, num(s.main_messages)));
      r.appendChild(el("td", { class: "num" }, s.subagent_messages ? num(s.subagent_messages) + " (" + s.subagents + " agents)" : "–"));
      r.appendChild(el("td", { class: "num" }, tok(s.peak_context)));
      r.appendChild(el("td", { class: "num" }, tok(s.total)));
      r.appendChild(el("td", { class: "num" }, usd(s.cost_usd)));
      r.appendChild(el("td", null, s.ended_by === "open" ? "still open" : "/" + s.ended_by + (s.compacts ? " · " + s.compacts + " /compact" : "")));
      tot.m += s.main_messages; tot.s += s.subagent_messages; tot.t += s.total; tot.c += s.cost_usd;
      tb.appendChild(r);
    });
    t.appendChild(tb);
    var tf = el("tfoot"), fr = el("tr");
    ["Total", "", "", num(tot.m), num(tot.s), "", tok(tot.t), usd(tot.c), ""].forEach(function (v, i) {
      fr.appendChild(el("td", i >= 3 && i <= 7 ? { class: "num" } : null, v));
    });
    tf.appendChild(fr); t.appendChild(tf);
  }

  /* ---------- insights + method ---------- */
  function renderInsights() {
    var T = D.totals, acts = sortedActs("total"), top = acts[0], tv = D.by_activity[top];
    var topSub = D.messages.reduce(function (s, m) { return s + (m.activity === top && m.thread === "subagent" ? m.total : 0); }, 0);
    var val = D.by_activity.running_validation, valP1 = (D.phase_activity["phase-1"] || {}).running_validation;
    var code = D.by_activity.writing_code || { total: 0, cost_usd: 0 };
    var crCost = T.cache_read_input_tokens * D.pricing.usd_per_million.cache_read / 1e6;
    var outCost = T.output_tokens * D.pricing.usd_per_million.output / 1e6;
    var cs = D.context.summary.clear, saved = cs.tokens_saved_est;
    var p1 = D.phase_thread["phase-1"] || {}, sub = p1.subagent || { total: 0, cost_usd: 0 }, main1 = p1.main || { total: 0 };
    var items = [
      [ACT[top].label + " cost the most.", tok(tv.total) + " tokens (" + pctTxt(tv.total, T.total) + ") and " + usd(tv.cost_usd) + " (" + pctTxt(tv.cost_usd, T.cost_usd) +
        " of est. cost). " + pctTxt(topSub, tv.total) + " of it was subagents searching for and reading policy pages in Phase 1."]
    ];
    if (val) items.push(["Running validation came " + (acts.indexOf("running_validation") + 1 === 2 ? "second" : "#" + (acts.indexOf("running_validation") + 1)) + ".",
      tok(val.total) + " tokens (" + pctTxt(val.total, T.total) + "). " + (valP1 ? pctTxt(valP1.total, val.total) + " of that was in Phase 1, where every excerpt was checked against its source with check_quotes.py; the rest is pytest and Playwright runs in later phases." : "")]);
    var dash = ["phase-3", "phase-4", "phase-5"].filter(function (p) { return D.phase_activity[p]; });
    var testHeavy = dash.length && dash.every(function (p) { var x = D.phase_activity[p]; return (x.running_validation || { total: 0 }).total > (x.writing_code || { total: 0 }).total; });
    items.push(["Writing code was cheap by comparison.", tok(code.total) + " tokens (" + pctTxt(code.total, T.total) + ", " + usd(code.cost_usd) + ")." +
      (testHeavy ? " Each dashboard phase (" + dash.map(shortPhase).join(", ") + ") spent more on running tests and checks than on writing code." : "")]);
    items.push(["The volume is re-reading, not writing.", "Cache reads are " + pctTxt(T.cache_read_input_tokens, T.total) + " of tokens but " + pctTxt(crCost, T.cost_usd) +
      " of est. cost. Output is " + pctTxt(T.output_tokens, T.total) + " of tokens and " + pctTxt(outCost, T.cost_usd) + " of est. cost."]);
    if (cs.measured) items.push(["/clear reset the context every time.", "Across " + cs.measured + " clears the context fell from about " + tok(cs.avg_before) + " to " + tok(cs.avg_after) +
      " per call (" + pctTxt(cs.avg_before - cs.avg_after, cs.avg_before) + " smaller). By our estimate that kept " + tok(saved) + " tokens out of the calls that followed."]);
    items.push(["Subagents were most of Phase 1.", tok(sub.total) + " of Phase 1's " + tok(sub.total + main1.total) + " tokens (" + pctTxt(sub.total, sub.total + main1.total) + "), " + usd(sub.cost_usd) +
      " est. Running them in parallel kept the main session's context small: the main thread only read their short hand-backs."]);
    var c = D.context.summary.compact;
    items.push(c.measured ? ["/compact shrank the context too.", "Across " + c.measured + " compacts the context went from about " + tok(c.avg_before) + " to " + tok(c.avg_after) + "."]
      : ["No /compact yet.", "Every reset in this project was a /clear between phases, guided by the “prepare to clear” handoff in PROGRESS.md."]);
    var ul = byId("insights");
    ul.textContent = "";
    items.forEach(function (it) { var li = el("li"); li.appendChild(el("strong", null, it[0])); li.appendChild(document.createTextNode(it[1])); ul.appendChild(li); });

    var m = byId("method");
    m.textContent = "";
    [D.pricing.note,
     "Each API message is written as several transcript lines that share one message id. It is counted once, using the usage on its last line.",
     "Steps come from tool calls: web search and fetch and page downloads count as gathering; writes to data/ and the analysis scripts as processing; writes to .py/.html/.css/.js files as writing code; pytest, Playwright, check_quotes.py and live-site checks as validation; PROGRESS.md, specs, git and planning as planning and docs. The full rules are in scripts/tokens.py.",
     "Phases come from the same hook-event timeline as the contributions timeline. A subagent's calls count toward the phase that was running when it ran."]
      .concat(D.not_measured).forEach(function (t) { m.appendChild(el("li", null, t)); });
  }

  /* ---------- metric toggle + theme ---------- */
  function initMetric() {
    var btns = byId("metric").querySelectorAll("button");
    Array.prototype.forEach.call(btns, function (b) {
      b.addEventListener("click", function () {
        M = b.dataset.metric;
        Array.prototype.forEach.call(btns, function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        renderSteps();
        renderSubagents();
      });
    });
  }
  function renderCharts() { renderSteps(); renderContext(); renderSubagents(); }

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
  fetch("data/tokens.json").then(function (r) {
    if (!r.ok) throw new Error("data/tokens.json returned HTTP " + r.status);
    return r.json();
  }).then(function (data) {
    D = data;
    initTheme();
    renderHead();
    renderCharts();
    initMetric();
    renderSessions();
    renderInsights();
    document.body.dataset.ready = "true";
  }).catch(function (err) {
    var main = byId("main");
    var p = el("p", { class: "empty", role: "alert" }, "The token data could not be loaded (" + err.message + "). Serve the docs/ folder over HTTP, for example with python3 -m http.server, and reload.");
    main.insertBefore(p, main.firstChild);
    document.body.dataset.ready = "error";
  });
})();
