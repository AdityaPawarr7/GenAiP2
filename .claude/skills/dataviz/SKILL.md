---
name: dataviz
description: Use before creating ANY chart, graph, dashboard, stat tile or data visualization (HTML/SVG/Chart.js). Gives a procedure for form choice, colorblind-safe palettes (validated by script), mark specs, hover tooltips, dark mode and accessibility.
---

# Data Visualization

A chart is **read by people and executed by you**. This skill turns "make it look good" into a procedure with checks, so the result is right by construction rather than by taste.

The method is design-system-agnostic. A **validated default palette** is the reference instance in `references/palette.md`.

> The single most important habit: **the color part is computable, so compute it.** Never eyeball whether a palette is colorblind-safe. Run `scripts/validate_palette.js`.

## The procedure: do these in order (color comes LAST)

1. **Pick the form.** What is the data's job: magnitude, identity, polarity, a single headline, or change over time? The job picks the chart type. Sometimes the answer is *not a chart* but a stat tile. See `references/choosing-a-form.md`.
2. **Assign color by the job it does:** categorical (identity), sequential (magnitude), diverging (polarity), or status (state). Assign categorical hues in fixed order, never cycled. See `references/color-formula.md`.
3. **VALIDATE the palette:** `node .claude/skills/dataviz/scripts/validate_palette.js "<hex,hex,...>" --mode light`, then again with `--mode dark`. Fix every FAIL.
4. **Apply mark specs and spacers.** Thin marks, 4px rounded data-ends, 2px lines, ≥8px markers, 2px surface gaps between fills, selective direct labels. See `references/marks-and-anatomy.md`.
5. **Add the hover layer by default:** a tooltip on every bar, dot or cell, and a crosshair on lines. Filters go in one row above the charts. See `references/interaction.md`.
6. **Do an accessibility pass.** With 2 or more series, always show a legend. A table view exists. Dark mode gets its own steps, validated, not an automatic inversion. Texture is available for colorblind readers and print.
7. **Render it and look at it.** Take a screenshot with Playwright and check for label collisions and overflow.

Then check against `references/anti-patterns.md`.

## Non-negotiables
- Categorical hues come in fixed order. A 9th series folds into "Other".
- **One axis.** Never a dual-axis chart.
- Color follows the entity, never its rank. Filters must not repaint the series that remain.
- Sequential = one hue, light→dark. Diverging = two hues + a neutral gray midpoint. No rainbows.
- Run the validator before shipping a palette. Target a CVD ΔE ≥ 8.
- Thin marks; recessive grid and axes; no number on every point.
- Text uses text colors, never the series color.
- Status colors (good/warning/serious/critical) are reserved and always come with an icon + label.

## Reference files
| File | What it answers |
|---|---|
| references/choosing-a-form.md | Which chart type, or whether to chart at all? |
| references/color-formula.md | The four color jobs and the six checks |
| references/marks-and-anatomy.md | Mark specs, labels, hero numbers |
| references/interaction.md | Tooltips, hover, filters |
| references/components.md | Chart building blocks in plain HTML |
| references/anti-patterns.md | What goes wrong. Check every chart against this |
| references/palette.md | The reference palette |
| scripts/validate_palette.js | Runnable validator |
