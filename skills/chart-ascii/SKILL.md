---
name: chart-ascii
description: >
  Draw plain-text bar charts, sparklines, and stacked composition for chat,
  the terminal, markdown, Slack, or email. Use when the user asks for an ASCII
  chart, unicode bars, a sparkline, a text chart, or any chart that has to stay
  copy-pasteable text. Zero baseline, 40–60 character width, clipped outliers
  called out. Uses scripts/render_bars.py when Python is available.
license: MIT
compatibility: Python 3.9+ to run scripts/render_bars.py. Hand-drawing does not need Python.
metadata:
  author: Dodge Labs
  version: "1.0"
---

# Plain-text charts

Use this when the chart has to survive as text. If they want a PNG, a slide, or brand colors, this is the wrong skill. Use chart-brand when it is installed.

Read these only when you are about to draw that form. Do not load them for a bar chart the script can draw.

- Bars, scale, sparkline, diverging, glyphs: `references/scale-rules.md`
- Parts of a whole: `references/composition-patterns.md`

The script implements the bar section of `scale-rules.md`. When you draw by hand, follow that file. Do not invent a second scale, width, or clip rule.

## Choose the form

- Magnitudes compared across categories: horizontal bars, via the script.
- One series over time, one line: sparkline. Hand-draw it.
- Parts of a whole: stacked composition. Hand-draw it.
- Any negative value: diverging bar. Hand-draw it. The script will refuse the row.

More than 12 bars is a tall message. Ask whether they want the largest 12 and an Other row before you print all of them. Do not drop rows silently.

## Bars

Run the script next to this file. Do not rewrite it into the user's project.

```bash
python3 scripts/render_bars.py --pairs "West=42;East=21;North=8"
```

`--pairs` is `Label=number` separated by `;`. Labels there cannot contain `;` or `=`. For anything else, a file or stdin: tab, `=`, comma, or a trailing number. See `--help`.

`--ascii` only when the destination is pure ASCII or they asked. Default is █ and ░.

Paste stdout unchanged into a `text` fence. Do not swap glyphs, reflow the track, or drop the footer. The footer is the scale.

`--no-clip` when they want a disparity shown rather than a scale that protects the smaller bars. `--max` when they named a top.

If `python3` is missing, say so and hand-draw from `references/scale-rules.md`.

## Sparkline and composition

Follow the matching reference. One chart, then one sentence: the scale, and any clip, fold into Other, or unallocated gap.

Bucket a sparkline that would pass 60 glyphs, and say you bucketed.

## Negatives

Do not pass them to the script. Draw the diverging form in `references/scale-rules.md`. The worked example there is the shape to match.

## Done

A monospace fence and the scale sentence the rules require. No second chart they did not ask for. No image of text.
