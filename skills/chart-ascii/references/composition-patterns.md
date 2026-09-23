# Composition patterns

Stacked bars for parts of a whole. Width, nice tops, rounding, and outlier clipping come from `scale-rules.md`. This file only adds how a bar is split.

## Which form

- One whole: one stacked bar.
- Several wholes (quarters, regions): one bar per row, same part order, same scale.
- Mix only: 100% bars. Every bar is the full track.
- Size and mix: absolute bars. Length is `total / top × width`. The top is the nice ceil of the largest total, after the clip rule in `scale-rules.md`.

Say which form you drew. Do not mix 100% and absolute in one chart.

Keep stage, age, or time order when the parts have one. Otherwise largest to smallest, with Other last.

## Glyphs

At most four shades, largest or first part first:

1. █
2. ▓
3. ▒
4. ░

In this chart ░ is a part, not empty track. The unused scale in absolute mode, and any gap inside a total, is `·` (middle dot). ASCII fallback, in the same roles: `#` `=` `+` `-` for parts, `.` for the gap and the unused scale.

The legend uses the same order as the bar:

```text
█ Discovery 18 (18%) · ▓ Design 27 (27%) · ▒ Build 41 (41%) · ░ Handoff 14 (14%)
```

Put the legend on the next line when it does not fit after the bar.

## How many parts

Four shades, then stop. Keep the three largest parts that are not forced into a canonical order, and fold the rest into Other. Other is last.

Also fold a part whose raw block count (below) is under 0.5, unless the person named that part and asked to see it. If folding would leave nothing, keep the largest part.

When a canonical order exists, keep that order and fold only the parts that would be under 0.5 blocks or past the fourth shade. Those folded parts still become one Other at the end, and the sentence under the chart names what went into it.

## Allocation

Let the bar have B cells. For a 100% bar, B is the track width. For an absolute bar, B is the rounded cell count of that row's total, and the cells after B are `·`.

1. Drop folded parts into Other. Recompute shares against the stated total, not against the sum of the survivors.
2. If the parts sum to less than the stated total, the gap is a `·` segment labeled `unallocated`. Do not stretch the other parts to hide it.
3. If the parts sum to more than the stated total, do not draw. Say the parts exceed the total and ask which number is wrong.
4. `raw[i] = share[i] × B`. `base[i] = floor(raw[i])`. Give the leftover cells (`B − sum(base)`) one at a time to the largest fractional parts. Ties go to the larger share, then to the earlier part in display order.
5. A zero share gets nothing. The never-disappear rule from `scale-rules.md` does not override a folded slice.

Worked 100% bar. Discovery 18, Design 27, Build 41, Handoff 14. Total 100, width 50, stage order. Raw cells 9, 13.5, 20.5, 7. Bases 9, 13, 20, 7 (49). One leftover. The 0.5 fractional parts tie; Build has the larger share, so Build gets the extra cell.

```text
█████████▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░
█ Discovery 18 (18%) · ▓ Design 27 (27%) · ▒ Build 41 (41%) · ░ Handoff 14 (14%)
100% · width 50 · stage order
```

## Footer

100%:

```text
100% · width {n} · {stage order | size order}
```

Absolute:

```text
Scale 0–{top} · width {n} · absolute
```

If a total was clipped, the clip sentence from `scale-rules.md` goes above the footer. The clipped row is a full track, and the true total is in the sentence.

## Concentration

If one part is 80% or more, draw it and say so in one sentence. Do not drop the other parts to make the bar look balanced.
