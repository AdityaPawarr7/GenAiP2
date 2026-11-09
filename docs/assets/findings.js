/* Findings dashboard (Phase 3). Reads only data/findings.json and data/policies.json.
   Every number on the page is computed from those files at load time. */
(function () {
  "use strict";

  var LABELS = {
    type: { private_r1: "Private R1", public_r1: "Public R1", other: "Other" },
    default_rule: {
      banned: "Banned by default",
      instructor_discretion: "Instructor decides",
      allowed_with_disclosure: "Allowed with disclosure",
      allowed_encouraged: "Encouraged",
      unclear: "Unclear"
    },
    se: { banned: "Banned", limited: "Limited", allowed: "Allowed", integrated: "Integrated", not_found: "No policy found" },
    stance: { "-2": "−2 Hostile", "-1": "−1 Wary", "0": "0 Neutral", "1": "+1 Supportive", "2": "+2 Enthusiastic" },
    theme: {
      academic_integrity: "Academic integrity",
      learning_outcomes: "Learning outcomes",
      career_readiness: "Career readiness",
      specific_tools: "Names specific tools",
      equity_access: "Equity and access",
      privacy_security: "Privacy and security",
      assessment_redesign: "Assessment redesign",
      ai_literacy: "AI literacy"
    },
    field: {
      default_rule: "Default rule",
      stance: "Stance",
      collaboration_framing: "Collaboration framing",
      disclosure_required: "Disclosure",
      se_course_policy: "SE course policy"
    },
    section: {
      dept_statement: "Department statement",
      university_guidance: "University guidance",
      intro_course: "Intro course",
      se_course: "SE course"
    }
  };
  var RULE_ORDER = ["banned", "instructor_discretion", "allowed_with_disclosure", "allowed_encouraged", "unclear"];
  var SE_ORDER = ["banned", "limited", "allowed", "integrated", "not_found"];
  var STANCE_ORDER = ["-2", "-1", "0", "1", "2"];
  var TYPE_ORDER = ["private_r1", "public_r1", "other"];

  var F, P, charts = {};
  var byId = function (id) { return document.getElementById(id); };
  var css = function (name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); };
  var pct = function (n, d) { return d ? Math.round((100 * n) / d) + "%" : "–"; };
  var sum = function (arr) { return arr.reduce(function (a, b) { return a + b; }, 0); };

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "style") node.setAttribute("style", attrs[k]);
      else node.setAttribute(k, attrs[k]);
    });
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  /* ---------- shared tooltip for HTML marks ---------- */
  var tip = byId("tip");
  function showTip(target, strong, rest) {
    tip.textContent = "";
    tip.appendChild(el("strong", null, strong));
    tip.appendChild(el("span", null, rest));
    tip.hidden = false;
    var r = target.getBoundingClientRect();
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    var y = r.top - h - 8;
    if (y < 8) y = r.bottom + 8;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }
  function hideTip() { tip.hidden = true; }
  function bindTip(node, strong, rest) {
    node.addEventListener("pointerenter", function () { showTip(node, strong, rest); });
    node.addEventListener("pointerleave", hideTip);
    node.addEventListener("focus", function () { showTip(node, strong, rest); });
    node.addEventListener("blur", hideTip);
  }

  /* ---------- hero + KPIs ---------- */
  function renderHero() {
    var d = F.dept_statement_finding, n = F.n;
    var rules = F.distributions.default_rule;
    byId("headline").textContent = "Only " + d.count + " of " + n + " CS departments publish their own generative AI statement";
    byId("dek").textContent = "The other " + (n - d.count) + " defer to university guidance or to individual syllabi. " +
      "We read the official AI language of " + n + " US computer science departments, their universities, and their intro and " +
      "software engineering courses. Every code on this page cites a quoted source.";

    var fig = byId("dept-figure");
    fig.textContent = d.count;
    fig.appendChild(el("small", null, "/ " + n));
    byId("dept-note").textContent = pct(d.count, n) + " of schools. Each square is one school; select one to see its evidence.";

    var names = {};
    P.records.forEach(function (r) { names[r.slug] = r.name; });
    var on = d.slugs.slice();
    var order = on.concat(P.records.map(function (r) { return r.slug; }).filter(function (s) { return on.indexOf(s) < 0; }));
    var grid = byId("unit-grid");
    order.forEach(function (slug) {
      var lit = on.indexOf(slug) >= 0;
      var b = el("button", { type: "button", class: "unit" + (lit ? " on" : ""), role: "listitem",
        "aria-label": names[slug] + (lit ? ": has its own department statement" : ": no department statement"), "data-slug": slug });
      bindTip(b, names[slug], lit ? "Has its own department AI statement" : "Defers to university or syllabus");
      b.addEventListener("click", function () { openSchool(slug); });
      grid.appendChild(b);
    });
    var bu = d.records.filter(function (r) { return r.slug === "bu"; })[0];
    byId("dept-foot").textContent = "Lit: " + d.records.map(function (r) { return r.name; }).join(", ") + "." +
      (bu ? " Boston University's statement comes from its Faculty of Computing & Data Sciences, counted as BU's school of computing; BU's CS department itself sits in Arts & Sciences." : "");

    var instr = rules.instructor_discretion;
    var f2 = byId("instr-figure");
    f2.textContent = instr;
    f2.appendChild(el("small", null, "/ " + n + " (" + pct(instr, n) + ")"));
    byId("instr-note").textContent = "These schools set no default rule. Whether a student may use AI depends on each course's syllabus.";
    byId("instr-rest").textContent = "Of the rest, " + rules.banned + " ban AI unless an instructor allows it, " +
      rules.allowed_with_disclosure + " allow it with disclosure, and " + (rules.allowed_encouraged === 0 ? "none" : rules.allowed_encouraged) + " encourage it.";

    var seg = byId("rule-seg"), key = byId("rule-seg-key");
    var segColors = { banned: "--neg1", instructor_discretion: "--accent", allowed_with_disclosure: "--s3", allowed_encouraged: "--pos2", unclear: "--zero" };
    var parts = RULE_ORDER.filter(function (k) { return rules[k] > 0; });
    seg.setAttribute("aria-label", parts.map(function (k) { return LABELS.default_rule[k] + " " + rules[k]; }).join(", "));
    parts.forEach(function (k) {
      var s = el("span", { style: "flex:" + rules[k] + ";background:var(" + segColors[k] + ")", tabindex: "0", "data-rule": k });
      bindTip(s, rules[k] + " schools (" + pct(rules[k], n) + ")", LABELS.default_rule[k]);
      seg.appendChild(s);
      var li = el("li");
      li.appendChild(el("span", { class: "sw", style: "background:var(" + segColors[k] + ")" }));
      li.appendChild(document.createTextNode(LABELS.default_rule[k]));
      key.appendChild(li);
    });
  }

  function renderKpis() {
    var n = F.n, rules = F.distributions.default_rule, t = F.n_by_type;
    var tiles = [
      { id: "institutions", label: "Institutions", value: String(n),
        detail: t.private_r1 + " private R1, " + t.public_r1 + " public R1, " + t.other + " other" },
      { id: "dept_policy", label: "Department-level policy", value: pct(F.dept_statement_finding.count, n),
        detail: F.dept_statement_finding.count + " of " + n + " schools" },
      { id: "encourage", label: "Encourage AI use", value: pct(rules.allowed_encouraged, n),
        detail: rules.allowed_encouraged + " of " + n + "; " + rules.allowed_with_disclosure + " allow it with disclosure" },
      { id: "collaboration", label: "Frame AI as a collaborator", value: pct(F.collaboration_framing.count, n),
        detail: F.collaboration_framing.count + " of " + n + " call it a tutor, partner or pair programmer" }
    ];
    var wrap = byId("kpis");
    tiles.forEach(function (k) {
      var d = el("div", { class: "kpi", "data-kpi": k.id });
      d.appendChild(el("p", { class: "label" }, k.label));
      d.appendChild(el("p", { class: "value" }, k.value));
      d.appendChild(el("p", { class: "detail" }, k.detail));
      wrap.appendChild(d);
    });
  }

  /* ---------- charts ---------- */
  var tipLabels = {
    id: "tipLabels",
    afterDatasetsDraw: function (chart, args, opts) {
      // show: print each bar's value; counts: print the dataset's school count (n) instead, skipping empty bars.
      if (!opts || !(opts.show || opts.counts)) return;
      var ctx = chart.ctx, horizontal = chart.options.indexAxis === "y";
      chart.$tipLabels = [];
      ctx.save();
      ctx.fillStyle = css("--ink-2");
      ctx.font = (opts.counts && window.innerWidth < 520 ? "11px" : "13px") + " system-ui, -apple-system, 'Segoe UI', sans-serif";
      chart.data.datasets.forEach(function (ds, i) {
        chart.getDatasetMeta(i).data.forEach(function (bar, j) {
          var v = opts.counts ? ds.counts[j] : ds.data[j];
          if (v === null || v === undefined || (opts.counts && v === 0)) return;
          var text = String(v);
          chart.$tipLabels.push({ dataset: i, index: j, text: text });
          if (horizontal) {
            ctx.textAlign = "left"; ctx.textBaseline = "middle";
            ctx.fillText(text, bar.x + 6, bar.y);
          } else {
            ctx.textAlign = "center"; ctx.textBaseline = "bottom";
            ctx.fillText(text, bar.x, bar.y - 4);
          }
        });
      });
      ctx.restore();
    }
  };

  function baseOptions(opts) {
    var ink2 = css("--ink-2"), grid = css("--grid"), axis = css("--axis");
    var horizontal = opts.horizontal;
    var valueAxis = {
      beginAtZero: true,
      grid: { color: grid, drawTicks: false },
      border: { display: false },
      ticks: { color: ink2, precision: 0, padding: 6, callback: opts.percent ? function (v) { return v + "%"; } : undefined },
      suggestedMax: opts.suggestedMax
    };
    var catAxis = {
      grid: { display: false },
      border: { color: axis },
      ticks: { color: ink2, autoSkip: false, maxRotation: 0, font: { size: 12 } }
    };
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      indexAxis: horizontal ? "y" : "x",
      layout: { padding: { top: horizontal ? 0 : 18, right: horizontal ? 28 : 4 } },
      scales: horizontal ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis },
      plugins: {
        legend: opts.legend ? {
          display: true, position: "top", align: "start",
          labels: { color: ink2, boxWidth: 10, boxHeight: 10, useBorderRadius: true, borderRadius: 3, font: { size: 13 } }
        } : { display: false },
        tipLabels: { show: !opts.legend, counts: !!opts.countLabels },
        tooltip: {
          backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: ink2,
          borderColor: css("--axis"), borderWidth: 1, padding: 10, cornerRadius: 8,
          titleFont: { size: 15, weight: "600" }, bodyFont: { size: 13 }, displayColors: !!opts.legend,
          boxWidth: 10, boxHeight: 2,
          callbacks: opts.tooltip
        }
      }
    };
  }

  function barDataset(data, colors, extra) {
    var ds = { data: data, backgroundColor: colors, hoverBackgroundColor: colors, borderRadius: 4, borderSkipped: "start", maxBarThickness: 24, categoryPercentage: 0.7, barPercentage: 0.9 };
    if (extra) Object.keys(extra).forEach(function (k) { ds[k] = extra[k]; });
    return ds;
  }

  function countTooltip(labels, total) {
    return {
      title: function (items) { var v = items[0].raw; return v + (v === 1 ? " school" : " schools") + " (" + pct(v, total) + ")"; },
      label: function (item) { return labels[item.dataIndex]; }
    };
  }

  function makeChart(id, config, table) {
    if (charts[id]) charts[id].destroy();
    config.plugins = [tipLabels];
    charts[id] = new Chart(byId(id), config);
    var det = document.querySelector('details[data-for="' + id + '"]');
    if (det && !det.querySelector("table")) {
      var t = el("table"), thead = el("thead"), tr = el("tr");
      table.head.forEach(function (h) { tr.appendChild(el("th", { scope: "col" }, h)); });
      thead.appendChild(tr); t.appendChild(thead);
      var tb = el("tbody");
      table.rows.forEach(function (row) {
        var r = el("tr");
        row.forEach(function (c) { r.appendChild(el("td", null, c)); });
        tb.appendChild(r);
      });
      t.appendChild(tb); det.appendChild(t);
    }
  }

  function renderCharts() {
    var n = F.n;
    // Default rule: one series, slot 1.
    var dr = F.distributions.default_rule;
    var drKeys = RULE_ORDER.filter(function (k) { return k !== "unclear" || dr[k] > 0; });
    var drLabels = drKeys.map(function (k) { return LABELS.default_rule[k]; });
    var drData = drKeys.map(function (k) { return dr[k]; });
    makeChart("chart-default-rule", {
      type: "bar",
      data: { labels: drLabels.map(wrapLabel), datasets: [barDataset(drData, css("--accent"), { keys: drKeys })] },
      options: baseOptions({ tooltip: countTooltip(drLabels, n) })
    }, { head: ["Default rule", "Schools"], rows: drKeys.map(function (k, i) { return [drLabels[i], String(drData[i])]; }) });

    // Stance: diverging (red arm, gray midpoint, blue arm).
    var st = F.distributions.stance;
    var stColors = [css("--neg2"), css("--neg1"), css("--zero"), css("--pos1"), css("--pos2")];
    var stLabels = STANCE_ORDER.map(function (k) { return LABELS.stance[k]; });
    var stData = STANCE_ORDER.map(function (k) { return st[k]; });
    makeChart("chart-stance", {
      type: "bar",
      data: { labels: stLabels.map(stanceTick), datasets: [barDataset(stData, stColors, { keys: STANCE_ORDER })] },
      options: baseOptions({ tooltip: countTooltip(stLabels, n) })
    }, { head: ["Stance", "Schools"], rows: STANCE_ORDER.map(function (k, i) { return [stLabels[i], String(stData[i])]; }) });

    // Stance by type: grouped bars, share within type; counts kept on the dataset.
    var cross = F.crosstabs_by_type.stance, nt = F.n_by_type;
    var typeColors = [css("--s1"), css("--s2"), css("--s3")];
    var groupDs = TYPE_ORDER.map(function (t, i) {
      var counts = STANCE_ORDER.map(function (k) { return cross[t][k]; });
      return barDataset(counts.map(function (c) { return Math.round((1000 * c) / nt[t]) / 10; }), typeColors[i],
        { label: LABELS.type[t] + " (n=" + nt[t] + ")", counts: counts, typeKey: t, keys: STANCE_ORDER, maxBarThickness: 20, categoryPercentage: 0.75, barPercentage: 0.92 });
    });
    makeChart("chart-stance-type", {
      type: "bar",
      data: { labels: stLabels.map(stanceTick), datasets: groupDs },
      options: baseOptions({
        legend: true, percent: true, countLabels: true,
        tooltip: {
          title: function (items) {
            var ds = items[0].dataset, c = ds.counts[items[0].dataIndex];
            return items[0].raw + "% (" + c + " of " + nt[ds.typeKey] + ")";
          },
          label: function (item) { return LABELS.type[item.dataset.typeKey] + ", stance " + stLabels[item.dataIndex]; }
        }
      })
    }, {
      head: ["Stance"].concat(TYPE_ORDER.map(function (t) { return LABELS.type[t] + " (n=" + nt[t] + ")"; })),
      rows: STANCE_ORDER.map(function (k, i) {
        return [stLabels[i]].concat(TYPE_ORDER.map(function (t) { return cross[t][k] + " (" + pct(cross[t][k], nt[t]) + ")"; }));
      })
    });

    var small = TYPE_ORDER.filter(function (t) { return nt[t] < 10; });
    byId("stance-type-note").textContent = small.length ? small.map(function (t) { return LABELS.type[t] + " (n=" + nt[t] + ")"; }).join(", ") +
      " is too small to compare: one school moves its bars by " + Math.round(100 / nt[small[0]]) + " percentage points." : "";

    // SE course policy: slot 1 for coded policies, recessive gray for "no policy found".
    var se = F.se_course.distribution;
    var seLabels = SE_ORDER.map(function (k) { return LABELS.se[k]; });
    var seData = SE_ORDER.map(function (k) { return se[k]; });
    var seColors = SE_ORDER.map(function (k) { return k === "not_found" ? css("--none") : css("--accent"); });
    makeChart("chart-se", {
      type: "bar",
      data: { labels: seLabels.map(wrapLabel), datasets: [barDataset(seData, seColors, { keys: SE_ORDER })] },
      options: baseOptions({ tooltip: countTooltip(seLabels, n) })
    }, { head: ["SE course policy", "Schools"], rows: SE_ORDER.map(function (k, i) { return [seLabels[i], String(seData[i])]; }) });

    // Themes: horizontal, sorted descending, one series.
    var th = F.themes.overall;
    var thKeys = Object.keys(th).sort(function (a, b) { return th[b] - th[a]; });
    var thLabels = thKeys.map(function (k) { return LABELS.theme[k] || k; });
    var thData = thKeys.map(function (k) { return th[k]; });
    makeChart("chart-themes", {
      type: "bar",
      data: { labels: thLabels, datasets: [barDataset(thData, css("--accent"), { keys: thKeys, categoryPercentage: 0.8 })] },
      options: baseOptions({ horizontal: true, tooltip: countTooltip(thLabels, n) })
    }, { head: ["Theme", "Schools"], rows: thKeys.map(function (k, i) { return [thLabels[i], String(thData[i])]; }) });
  }

  function stanceTick(s) {
    // On narrow screens the stance axis shows only the score; the chart subtitle names the scale.
    return window.innerWidth < 520 ? s.split(" ")[0] : wrapLabel(s);
  }

  function wrapLabel(s) {
    // Long category labels go on two lines, or one word per line on narrow screens, so they never collide.
    if (s.length <= 12) return s;
    var words = s.split(" ");
    if (window.innerWidth < 520) return words;
    var half = Math.ceil(words.length / 2);
    return [words.slice(0, half).join(" "), words.slice(half).join(" ")];
  }

  function renderSe() {
    var s = F.se_course;
    byId("se-sub").textContent = "We found a public AI policy for a software engineering course at " + s.n_with_policy + " of " + F.n +
      " schools. Of those, " + s.distribution.integrated + " build AI into the coursework and " + s.distribution.banned + " ban it.";
    var list = byId("integrated-list");
    var bySlug = {};
    P.records.forEach(function (r) { bySlug[r.slug] = r; });
    s.courses.filter(function (c) { return c.policy === "integrated"; }).forEach(function (c) {
      var rec = bySlug[c.slug], ev = rec && rec.evidence_sources.filter(function (e) { return e.key === "se_course_policy"; })[0];
      var li = el("li", { "data-slug": c.slug });
      var who = el("span", { class: "who" }, c.name);
      li.appendChild(who);
      if (ev && ev.course) li.appendChild(document.createTextNode(", " + ev.course));
      li.appendChild(el("br"));
      li.appendChild(el("q", null, c.quote));
      if (ev && ev.url) {
        li.appendChild(document.createTextNode(" "));
        li.appendChild(el("a", { href: ev.url, target: "_blank", rel: "noopener" }, "Source"));
      }
      list.appendChild(li);
    });
  }

  /* ---------- explorer ---------- */
  var state = { q: "", type: "", rule: "", se: "", sort: "name", dir: 1, open: null };

  function fillSelect(id, labels, order, counts) {
    var s = byId(id);
    order.forEach(function (k) {
      if (counts && !counts[k]) return;
      s.appendChild(el("option", { value: k }, labels[k]));
    });
  }

  function stanceColor(v) { return css(["--neg2", "--neg1", "--zero", "--pos1", "--pos2"][v + 2]); }

  function matches(r) {
    var q = state.q.trim().toLowerCase();
    if (q && (r.name + " " + r.slug).toLowerCase().indexOf(q) < 0) return false;
    if (state.type && r.type !== state.type) return false;
    if (state.rule && r.default_rule !== state.rule) return false;
    if (state.se && r.se_course_policy !== state.se) return false;
    return true;
  }

  function sortValue(r, key) {
    if (key === "default_rule") return RULE_ORDER.indexOf(r.default_rule);
    if (key === "se_course_policy") return SE_ORDER.indexOf(r.se_course_policy);
    if (key === "type") return TYPE_ORDER.indexOf(r.type);
    if (key === "stance") return r.stance;
    return r.name.toLowerCase();
  }

  function renderRows() {
    var body = byId("rows");
    body.textContent = "";
    var deptSlugs = F.dept_statement_finding.slugs;
    var rows = P.records.filter(matches).sort(function (a, b) {
      var x = sortValue(a, state.sort), y = sortValue(b, state.sort);
      if (x < y) return -state.dir;
      if (x > y) return state.dir;
      return a.name < b.name ? -1 : 1;
    });
    rows.forEach(function (r) {
      var open = state.open === r.slug;
      var tr = el("tr", { class: "row", tabindex: "0", "data-slug": r.slug, "aria-expanded": open ? "true" : "false" });
      var tdName = el("td", { class: "name" });
      tdName.appendChild(document.createTextNode(r.name));
      if (deptSlugs.indexOf(r.slug) >= 0) tdName.appendChild(el("span", { class: "dept-tag" }, "dept statement"));
      tr.appendChild(tdName);
      tr.appendChild(el("td", { class: "type" }, LABELS.type[r.type]));
      tr.appendChild(el("td", { class: "rule" }, LABELS.default_rule[r.default_rule]));
      var tdS = el("td", { class: "num stance" });
      tdS.appendChild(el("span", { class: "stance-chip", style: "background:" + stanceColor(r.stance), "aria-hidden": "true" }));
      tdS.appendChild(document.createTextNode((r.stance > 0 ? "+" : r.stance < 0 ? "−" : "") + Math.abs(r.stance)));
      tr.appendChild(tdS);
      tr.appendChild(el("td", { class: "se" }, LABELS.se[r.se_course_policy]));
      tr.addEventListener("click", function () { toggle(r.slug); });
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(r.slug); } });
      body.appendChild(tr);
      if (open) body.appendChild(detailRow(r));
    });
    if (!rows.length) {
      var tr0 = el("tr"), td0 = el("td", { colspan: "5", class: "empty" }, "No schools match. Clear the search or a filter to see more.");
      tr0.appendChild(td0); body.appendChild(tr0);
    }
    byId("count").textContent = "Showing " + rows.length + " of " + P.records.length + " schools";
    document.querySelectorAll("#schools th").forEach(function (th) {
      th.setAttribute("aria-sort", th.dataset.key === state.sort ? (state.dir > 0 ? "ascending" : "descending") : "none");
    });
  }

  function highlighted(quote, evidence) {
    var frag = document.createDocumentFragment();
    var i = quote ? quote.indexOf(evidence) : -1;
    if (i < 0) { frag.appendChild(document.createTextNode(quote || evidence)); return frag; }
    frag.appendChild(document.createTextNode(quote.slice(0, i)));
    frag.appendChild(el("mark", null, evidence));
    frag.appendChild(document.createTextNode(quote.slice(i + evidence.length)));
    return frag;
  }

  function fieldLabel(key) {
    if (key.indexOf("themes:") === 0) return "Theme: " + (LABELS.theme[key.slice(7)] || key.slice(7));
    return LABELS.field[key] || key;
  }

  function sourceDateText(v) {
    if (!v) return null;
    if (v === "undated") return "undated";
    var m = /^(\d{4})/.exec(v);
    return m ? m[1] : v;
  }

  function detailRow(r) {
    var tr = el("tr", { class: "detail-row", "data-detail": r.slug });
    var td = el("td", { colspan: "5" });
    var d = el("div", { class: "detail" });
    var codes = el("p", { class: "codes" });
    [["Collaboration framing", r.collaboration_framing ? "yes" : "no"],
     ["Disclosure required", r.disclosure_required],
     ["Policy level", r.policy_level.replace("_", " ")],
     ["Confidence", r.confidence],
     ["Themes", r.themes.map(function (t) { return LABELS.theme[t] || t; }).join(", ") || "none"]].forEach(function (c) {
      var s = el("span");
      s.appendChild(document.createTextNode(c[0] + ": "));
      s.appendChild(el("b", null, c[1]));
      codes.appendChild(s);
    });
    d.appendChild(codes);
    var ul = el("ul", { class: "ev" });
    r.evidence_sources.forEach(function (e) {
      var li = el("li", { "data-evidence": e.key });
      li.appendChild(el("p", { class: "field" }, fieldLabel(e.key)));
      var bq = el("blockquote");
      bq.appendChild(highlighted(e.quote, e.evidence));
      li.appendChild(bq);
      var src = el("p", { class: "src" });
      var bits = [LABELS.section[e.section] || e.section];
      if (e.course) bits.push(e.course);
      var sd = sourceDateText(e.source_date);
      if (sd) bits.push(sd === "undated" ? "undated" : "dated " + sd);
      src.appendChild(document.createTextNode(bits.join(", ") + ". "));
      if (e.url) src.appendChild(el("a", { href: e.url, target: "_blank", rel: "noopener" }, hostOf(e.url)));
      li.appendChild(src);
      ul.appendChild(li);
    });
    d.appendChild(ul);
    if (r.notes) d.appendChild(el("p", { class: "notes" }, "Coder notes: " + r.notes));
    td.appendChild(d);
    tr.appendChild(td);
    return tr;
  }

  function hostOf(url) {
    try { var u = new URL(url); return u.hostname.replace(/^www\./, "") + (u.pathname.length > 1 ? u.pathname.replace(/\/$/, "") : ""); }
    catch (e) { return url; }
  }

  function toggle(slug) {
    state.open = state.open === slug ? null : slug;
    renderRows();
    var row = document.querySelector('#rows tr.row[data-slug="' + slug + '"]');
    if (row) row.focus({ preventScroll: true });
  }

  function openSchool(slug) {
    state.q = ""; state.type = ""; state.rule = ""; state.se = "";
    byId("q").value = ""; byId("f-type").value = ""; byId("f-rule").value = ""; byId("f-se").value = "";
    state.open = slug;
    renderRows();
    var row = document.querySelector('#rows tr.row[data-slug="' + slug + '"]');
    if (row) { row.scrollIntoView({ block: "center" }); row.focus({ preventScroll: true }); }
  }

  function renderExplorer() {
    fillSelect("f-type", LABELS.type, TYPE_ORDER);
    fillSelect("f-rule", LABELS.default_rule, RULE_ORDER, F.distributions.default_rule);
    fillSelect("f-se", LABELS.se, SE_ORDER, F.se_course.distribution);
    byId("q").addEventListener("input", function (e) { state.q = e.target.value; renderRows(); });
    byId("f-type").addEventListener("change", function (e) { state.type = e.target.value; renderRows(); });
    byId("f-rule").addEventListener("change", function (e) { state.rule = e.target.value; renderRows(); });
    byId("f-se").addEventListener("change", function (e) { state.se = e.target.value; renderRows(); });
    document.querySelectorAll("#schools th button").forEach(function (b) {
      b.addEventListener("click", function () {
        var key = b.parentNode.dataset.key;
        if (state.sort === key) state.dir = -state.dir; else { state.sort = key; state.dir = 1; }
        renderRows();
      });
    });
    renderRows();
  }

  /* ---------- method ---------- */
  function renderMethod() {
    var left = byId("method-left"), right = byId("method-right");
    var ret = P.retrieved, cov = F.source_coverage;
    var paras = [
      ["Sample. ", F.n + " US computer science departments (" + F.n_by_type.private_r1 + " private R1, " + F.n_by_type.public_r1 +
        " public R1, " + F.n_by_type.other + " other). For each we collected the department statement, university guidance, an intro course and a software engineering course. Sources retrieved " +
        (ret ? (ret.min === ret.max ? ret.min : ret.min + " to " + ret.max) : "on the dates in data/raw") + "."],
      ["Coding. ", "Claude coded every school against a fixed codebook (default rule, stance, collaboration framing, disclosure, SE course policy, eight themes). Every code cites a verbatim quote from a page saved with its URL; the quotes were re-checked against the live pages. A keyword cross-check flagged codes that disagreed with the text for review."],
      ["Coverage. ", "Department statement found for " + cov.dept_statement.count + " schools, university guidance for " + cov.university_guidance.count +
        ", intro course for " + cov.intro_course.count + ", SE course for " + cov.se_course.count + ". Pages behind a login or returning errors to scripts were recorded as blocked, not guessed."]
    ];
    paras.forEach(function (p) {
      var el_ = el("p"); el_.appendChild(el("b", null, p[0])); el_.appendChild(document.createTextNode(p[1])); left.appendChild(el_);
    });

    right.appendChild(el("h3", null, "Agreement with independent coders"));
    var ag = P.agreement || {}, h = ag.human_vs_claude, a2 = ag.ai2_vs_claude;
    if (h && h.status === "complete") {
      var t = el("table", { class: "agree" }), thead = el("thead"), hr = el("tr");
      ["Field", "Human vs Claude (n=" + h.n_institutions + ")", "Second AI vs Claude (n=" + (a2 ? a2.n_institutions : "–") + ")"].forEach(function (x) { hr.appendChild(el("th", { scope: "col" }, x)); });
      thead.appendChild(hr); t.appendChild(thead);
      var tb = el("tbody");
      Object.keys(h.fields).forEach(function (f) {
        var tr = el("tr");
        tr.appendChild(el("td", null, LABELS.field[f] || f.replace("_", " ")));
        tr.appendChild(el("td", null, fmtAgree(h.fields[f])));
        tr.appendChild(el("td", null, a2 && a2.fields[f] ? fmtAgree(a2.fields[f]) : "–"));
        tb.appendChild(tr);
      });
      t.appendChild(tb);
      right.appendChild(t);
    }
    right.appendChild(el("p", { class: "sub" }, "Cells show percent agreement and Cohen's κ (linear-weighted κ for stance)."));
    var ul = el("ul");
    [
      "The human sample is only " + (h ? h.n_institutions : "a few") + " schools, so its κ values are unstable; read them as a rough check, not a reliability estimate.",
      "The second AI used the codebook's conventions section, which was written while coding these same schools, so AI-to-AI agreement is likely inflated.",
      "One coder (Claude) produced every code; stance in particular is a judgment call and disagreed most with the human coder.",
      "Only " + cov.dept_statement.count + " department statements exist, and Boston University's is from its Faculty of Computing & Data Sciences rather than the CS department.",
      "Policies change each term. Many sources are from 2026, but some university guidance dates from 2023 or is undated.",
      "Public pages only: course policies behind a learning management system are missing, which is why " + (F.n - cov.se_course.count) + " schools have no SE course policy."
    ].forEach(function (x) { ul.appendChild(el("li", null, x)); });
    left.appendChild(el("h3", { style: "margin-top:24px" }, "Limitations"));
    left.appendChild(ul);
  }

  function fmtAgree(f) {
    var k = f.weighted_kappa_linear !== undefined ? f.weighted_kappa_linear : f.cohens_kappa;
    return Math.round(f.percent_agreement * 100) + "%, κ " + (k === null || k === undefined ? "n/a" : k.toFixed(2));
  }

  /* ---------- theme ---------- */
  function currentTheme() {
    var t = document.documentElement.dataset.theme;
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function syncThemeButton() {
    var btn = byId("theme-btn");
    btn.textContent = currentTheme() === "dark" ? "Light mode" : "Dark mode";
  }
  function initTheme() {
    syncThemeButton();
    byId("theme-btn").addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
      syncThemeButton();
      renderCharts();
      renderRows();
    });
    var narrow = window.innerWidth < 520;
    window.addEventListener("resize", function () {
      if ((window.innerWidth < 520) !== narrow) { narrow = !narrow; renderCharts(); }
    });
    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
        if (!document.documentElement.dataset.theme) { syncThemeButton(); renderCharts(); renderRows(); }
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

  Promise.all([load("data/findings.json"), load("data/policies.json")]).then(function (res) {
    F = res[0]; P = res[1];
    initTheme();
    renderHero();
    renderKpis();
    renderCharts();
    renderSe();
    renderExplorer();
    renderMethod();
    document.body.dataset.ready = "true";
  }).catch(function (err) {
    var main = byId("main");
    var p = el("p", { class: "empty", role: "alert" }, "The dashboard data could not be loaded (" + err.message + "). Serve the docs/ folder over HTTP, for example with python3 -m http.server, and reload.");
    main.insertBefore(p, main.firstChild);
    document.body.dataset.ready = "error";
  });
})();
