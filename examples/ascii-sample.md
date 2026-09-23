# Text chart samples

Sample data. The bars are stdout from `skills/chart-ascii/scripts/render_bars.py`. The sparkline, the stacked bar, and the diverging bar are drawn from the rules in that skill.

## Bars

```bash
python3 skills/chart-ascii/scripts/render_bars.py \
  --title "Sample pipeline, hours" \
  --pairs "Discovery=18;Design=27;Build=41;Launch=180"
```

```text
Sample pipeline, hours

Discovery  ██████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   18
Design     ███████████████████████████░░░░░░░░░░░░░░░░░░░░░░░   27
Build      █████████████████████████████████████████░░░░░░░░░   41
Launch     ██████████████████████████████████████████████████  180  clipped

Clipped to the body of the data: Launch (180).
Scale 0–50 · width 50 · █░
```

Launch is 180 against a body that tops out at 41, so the scale is 0–50 and that bar is full. The printed number is the real one.

## Sparkline

Weekly hours: 0, 40, 55, 48, 70, 22, 92, 88. The top is the nice ceiling, 100.

```text
▁▄▅▄▆▃▇▇
▁ = 0 · █ = 100
```

The first week is zero, so the first glyph is ▁.

## Composition

Discovery 18, Design 27, Build 41, Handoff 14. Total 100. Stage order, 100% bar, width 50.

```text
█████████▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░
█ Discovery 18 (18%) · ▓ Design 27 (27%) · ▒ Build 41 (41%) · ░ Handoff 14 (14%)
100% · width 50 · stage order
```

## Diverging

Negative values stay out of `render_bars.py`. Values −8, 5, 12, −3. Top 20, 25 cells on each side of zero.

```text
Discovery  ░░░░░░░░░░░░░░░██████████│░░░░░░░░░░░░░░░░░░░░░░░░░  −8
Design     ░░░░░░░░░░░░░░░░░░░░░░░░░│██████░░░░░░░░░░░░░░░░░░░   5
Build      ░░░░░░░░░░░░░░░░░░░░░░░░░│███████████████░░░░░░░░░░  12
Handoff    ░░░░░░░░░░░░░░░░░░░░░████│░░░░░░░░░░░░░░░░░░░░░░░░░  −3

Scale −20–20 · width 50 · zero at │
```

## ASCII fallback

```bash
python3 skills/chart-ascii/scripts/render_bars.py \
  --ascii --width 40 \
  --title "Sample pipeline, hours" \
  --pairs "Discovery=18;Design=27;Build=41;Launch=180"
```

```text
Sample pipeline, hours

Discovery  ##############..........................   18
Design     ######################..................   27
Build      #################################.......   41
Launch     ########################################  180  clipped

Clipped to the body of the data: Launch (180).
Scale 0-50 | width 40 | #.
```
