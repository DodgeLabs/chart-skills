---
name: chart-brand
description: >
  Turn a brand hex list into a matplotlib and seaborn theme: brand.toml, a
  matplotlibrc, and proof PNGs. Use when the user wants on-brand charts, a
  matplotlib style, a seaborn palette, or colors pulled from a website
  stylesheet or a slide image. Scraped and image palettes stay proposals until
  a person confirms them. Does not build Chart.js, call chart APIs, or use MCP.
license: MIT
compatibility: >
  Python 3.9+. Proof PNGs need matplotlib. Image palettes need Pillow.
  palette_from_css.py uses the network only when given a URL.
metadata:
  author: Dodge Labs
  version: "1.0"
---

# Brand themes for matplotlib

v1 writes files on disk from a hex list. No Chart.js, no hosted chart service, no MCP.

Run the scripts next to this file. Do not reimplement them.

- Hex list, or a theme that already exists: `scripts/write_matplotlibrc.py`
- URL, HTML, or CSS: `scripts/palette_from_css.py`
- Slide or screenshot: `scripts/palette_from_image.py`

Toml shape, load order, and the proof files: `references/matplotlibrc-template.md`

Contrast failures and warnings: `references/contrast.md`

A worked theme: `assets/dodge-demo.toml`

## Hex list

```bash
python3 scripts/write_matplotlibrc.py --name "Name" --hex 14133D 2D8A56 --out chart-theme
```

Those hexes are the series cycle, in that order. The script does not add more series colors. Pass `--background`, `--ink`, `--accent`, `--positive`, `--negative`, `--mark`, or `--font` when you have them. Otherwise the defaults in `scripts/brandio.py` are used and you should look at the proof before trusting them.

The command writes `brand.toml`, `matplotlibrc`, `bars.png`, `lines.png`, and `variance.png` under `--out`. Show the three PNGs. The numbers on them are sample data. They are the review, not a figure to send.

A contrast failure writes nothing and exits 2. Fix the hex or, if the person accepts that specific failure, re-run with `--force`. Do not pass `--force` on your own.

`--no-proofs` only when they asked for the files and not the review images. If matplotlib is missing the text files still land and the exit code is 3. Say so. Do not invent a PNG.

## CSS or an image

Run the extractor and show its stdout, including the contrast lines. Then stop.

`palette_from_css.py` reads static CSS and custom properties. It does not run JavaScript and does not follow `@import`. If the page is a client-rendered app and the proposal is thin, say that.

`palette_from_image.py` needs Pillow. If the import fails, report that. Do not guess hexes off the picture and call them extracted. A labeled guess is allowed only if you say it is a guess, and you still wait.

Both extractors write a toml only when given `--proposal`, and that file is `status = "unconfirmed"`. `write_matplotlibrc.py` refuses it unless `--confirm` is set.

`--confirm` means the person approved this palette. Approval is a later message from them. Do not pass `--confirm` in the turn where you first show the proposal. Do not pass it because the colors look reasonable to you.

When you show a proposal, point at any color that would mean both "series" and "bad" or "look here." Reds do this often. The Dodge Labs demo keeps `#EE4E47` out of the cycle for that reason. See the `note` in `assets/dodge-demo.toml`.

## Drawing with the theme

```python
import matplotlib.pyplot as plt
plt.style.use("chart-theme/matplotlibrc")
```

If seaborn is imported, `sns.set_theme` replaces the cycle. Call it first, then `style.use` the rc file again. The load snippet is in `references/matplotlibrc-template.md`.

Bars of amounts start at zero. Line charts of amounts start at zero. If you zoom, say the axis does not start at zero.

Honor the warnings. One hue, one meaning on a chart. Labels go in the ink color, outside the mark, unless you have checked the pair in `references/contrast.md`. `roles.mark` is a wash. `sequential` is a single-hue ramp, not a set of categories.

## Done

The output directory, the warnings, and the three proof images. Ask which series color is wrong before the theme is used on real data.
