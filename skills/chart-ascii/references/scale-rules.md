# Scale rules

Authority for plain-text charts. `scripts/render_bars.py` implements the bar section. Sparkline, diverging, and the shared rounding rule are here. Stacked composition uses these widths and this clip rule, and its own glyph rules in `composition-patterns.md`.

## Rounding

Halves round away from zero (half up for positive numbers): floor(x + 0.5).

A positive value never disappears. If rounding would draw nothing, draw the smallest mark the mode has.

## Glyphs

Unicode bars:

| Fill | Empty track | Partials, 1/8 through 7/8 |
| --- | --- | --- |
| █ | ░ | ▏ ▎ ▍ ▌ ▋ ▊ ▉ |

The partial replaces one empty cell. It grows from the left, which is correct when the bar grows to the right.

ASCII bars: `#` filled, `.` empty. No partials. Round to the nearest cell, then apply the never-disappear rule.

Sparkline, zero through the top, eight steps: ▁ ▂ ▃ ▄ ▅ ▆ ▇ █

ASCII sparkline, same eight steps: `. : - ~ = + * #`

Diverging bars use full cells only, in both modes. Unicode's partial blocks grow from the left. On the negative side that opens a gap at zero, and there is no matching right-growing set. Round each side to whole cells instead.

## Width

The bar track is 40–60 characters. Default 50. The track is the glyphs only. Labels sit to the left, the number to the right.

Use 40 in a narrow chat column. Use 50 in markdown and a normal terminal. Do not go past 60.

Labels are at most 24 characters. Truncate with `…` (ASCII mode: `...` and a 22-character stem, so the visible label is still 24). Pad with spaces to the widest label in the chart. Padding uses Python `len`. Wide East-Asian characters will misalign. Prefer short labels.

A sparkline is one glyph per observation and stays at or under 60 glyphs. Above that, bucket into 48 bins by mean and say you bucketed.

## Zero baseline

The left edge of a bar is zero. Do not start the axis at the data minimum.

A zero value is a row of empty track, and the row is still printed.

Sparkline: ▁ means 0 and █ means the stated top. Do not rescale so the minimum sits on ▁. If every point is far from zero, the line sits high and looks flat. Keep it, and say the movement is small relative to the level. Draw a second, zoomed line only if the person asks to see the change.

## Scale top

Nice steps are 1, 2, 2.5, 5, and 10 times a power of ten.

The top is the smallest nice number greater than or equal to the largest value that is not clipped. If that largest value is 0, the top is 1.

Do not apply a nice top when a maximum was chosen explicitly (`--max` in the script, or a top the person asked for).

## Bars

Layout, monospace:

```text
{title}

{label}  {track}  {value}{optional "  clipped"}

{clip sentence, only if something was clipped}
Scale 0–{top} · width {n} · █░
```

ASCII footer uses `|` and `#.` instead of `·` and `█░`, and a hyphen instead of an en dash: `Scale 0-{top} | width {n} | #.`

Keep the person's order. Sort only if they asked for a ranking or alphabetical order.

Value text uses thousands separators, at most two decimal places, trailing zeros removed.

## Clipping outliers

Clip only when all of these hold:

- At least three values.
- The highest value is at least 3× the next lower distinct value.
- The rows sitting on that highest value are a minority: fewer than half the rows.
- At least one row remains unclipped.

Repeat on what remains, so two separated spikes can both clip. Equal values at the top are one run. Do not clip them just because they match each other.

The scale top is computed from the unclipped body. A clipped row is a full track. Its printed number is the true value, followed by `  clipped`. Under the chart:

```text
Clipped to the body of the data: Launch (180).
```

Do not clip when the person wants the disparity shown ("how much bigger is launch?"). In the script, that is `--no-clip`. The other bars will be short. Leave them short.

A value above an explicit maximum is clipped the same way, even if the 3× rule would not have fired.

## Sparkline

1. Top = nice ceil of the unclipped maximum, using the clip rule above. Name clipped points in a sentence. Draw each clipped point as █.
2. For every other point, level = round half up of `value / top * 7`, clamped to 0–7.
3. Glyph = the level-th character of ▁▂▃▄▅▆▇█ (level 0 is ▁).
4. Caption on its own line: `▁ = 0 · █ = {top}`. ASCII: `. = 0 | # = {top}`.

A zero observation is ▁, not a missing glyph.

## Diverging bars

Use this when any value is negative. Do not send those rows to `render_bars.py`.

1. Top = nice ceil of the largest absolute value. The scale is −top to +top. Say so.
2. Track width is even, 40–60, default 50. Each side is width/2 cells. A one-character zero marker sits between them: `│` in Unicode, `|` in ASCII. The marker is not part of the 40–60.
3. A positive value fills rightward from the marker. A negative value fills leftward toward the marker. Empty cells are ░ or `.`.
4. Cells on a side = round half up of `abs(value) / top * (width / 2)`, with the never-disappear rule. Whole cells only.
5. Footer: `Scale −{top}–{top} · width {width} · zero at │`

Worked Unicode example. Values −8, 5, 12, −3. Largest absolute value 12, top 20, width 50, 25 cells a side.

```text
Discovery  ░░░░░░░░░░░░░░░██████████│░░░░░░░░░░░░░░░░░░░░░░░░░  −8
Design     ░░░░░░░░░░░░░░░░░░░░░░░░░│██████░░░░░░░░░░░░░░░░░░░   5
Build      ░░░░░░░░░░░░░░░░░░░░░░░░░│███████████████░░░░░░░░░░  12
Handoff    ░░░░░░░░░░░░░░░░░░░░░████│░░░░░░░░░░░░░░░░░░░░░░░░░  −3

Scale −20–20 · width 50 · zero at │
```

−8 → 10 cells, 5 → 6 cells, 12 → 15 cells, −3 → 4 cells.
