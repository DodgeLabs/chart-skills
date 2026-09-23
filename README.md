# chart-skills

Two Agent Skills from Dodge Labs for charts that stay honest.

**chart-ascii** draws bars, sparklines, and stacked composition as text. Chat, a terminal, markdown, email.

**chart-brand** turns your colors into a matplotlib and seaborn theme: `brand.toml`, a `matplotlibrc`, and three proof figures.

Ask an agent to install them, then paste one of the prompts below. The commands further down run the same scripts by hand.

GitHub: [DodgeLabs/chart-skills](https://github.com/DodgeLabs/chart-skills).

## Install

You can point your agent at https://github.com/DodgeLabs/chart-skills and ask it to install these skills into the skills directory it loads. Copy `skills/chart-ascii` and `skills/chart-brand` whole. Saving only `SKILL.md` is not an install. The agent reads `SKILL.md` and runs the scripts beside it.

```text
Install chart-ascii and chart-brand from https://github.com/DodgeLabs/chart-skills. Copy skills/chart-ascii and skills/chart-brand whole into the skills directory you load. Saving only SKILL.md is not an install.
```

Claude Code loads `~/.claude/skills` for every project and `.claude/skills` for the current one. Cursor loads `~/.cursor/skills` and `.cursor/skills` the same way.

By hand, from a checkout of this repo:

```bash
mkdir -p ~/.claude/skills ~/.cursor/skills
ln -sfn "$PWD/skills/chart-ascii" ~/.claude/skills/chart-ascii
ln -sfn "$PWD/skills/chart-ascii" ~/.cursor/skills/chart-ascii
ln -sfn "$PWD/skills/chart-brand" ~/.claude/skills/chart-brand
ln -sfn "$PWD/skills/chart-brand" ~/.cursor/skills/chart-brand
```

To vendor the skills into another project, use the same links under that project's `.claude/skills/` and `.cursor/skills/`. From `.claude/skills/chart-ascii`, the relative target is `../../skills/chart-ascii`.

## Text charts

Paste a table, or name a file the agent can already open. Each row is a label and an amount.

```text
Using chart-ascii, chart this. Title: Sample pipeline, hours.

Discovery 18
Design 27
Build 41
Launch 180
```

You get text you can paste into chat, a doc, or an email. Amounts start at zero. A value far above the rest is clipped and named, so the other bars stay readable.

```text
Sample pipeline, hours

Discovery  ██████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   18
Design     ███████████████████████████░░░░░░░░░░░░░░░░░░░░░░░   27
Build      █████████████████████████████████████████░░░░░░░░░   41
Launch     ██████████████████████████████████████████████████  180  clipped

Clipped to the body of the data: Launch (180).
Scale 0–50 · width 50 · █░
```

A sparkline is one series over time. Parts of a whole are a stacked bar. Any negative amount is a diverging bar. Say which of those you want. Worked samples are in [examples/ascii-sample.md](examples/ascii-sample.md).

The same bars from the command line:

```bash
python3 skills/chart-ascii/scripts/render_bars.py \
  --title "Sample pipeline, hours" \
  --pairs "Discovery=18;Design=27;Build=41;Launch=180"
```

## Your colors

With chart-brand installed, paste one of these.

Hexes you already have:

```text
Make a matplotlib theme named Acme. Series colors #14133D #2D8A56. Background #F7F5F3, text #1F1F1F. Show the proof charts.
```

A website:

```text
Read the colors from https://example.com and propose a chart palette. Wait until I confirm it before you write the theme.
```

A slide or a screenshot:

```text
Read the colors in this image and propose a chart palette. Wait until I confirm it before you write the theme.
```

A website or a picture comes back as a proposal. Confirm it in a later message. The agent then writes `brand.toml`, `matplotlibrc`, and three proof PNGs. The numbers on those PNGs are sample data, so you can see the colors. Attach your table in that confirmation and ask for the chart in those colors.

The stylesheet reader does not run JavaScript. A page that sets its colors only in script may come back thin. Say so if it does, and use a screenshot instead.

### Dodge Labs demo

The Dodge Labs demo uses the [dodgelabs.com](https://dodgelabs.com/) tokens. Navy and green are series colors. Red is the accent and the down color. The highlight yellow is a wash. Three further series colors are chart extensions so a multi-series figure has something other than navy and green. The `note` in [`skills/chart-brand/assets/dodge-demo.toml`](skills/chart-brand/assets/dodge-demo.toml) names which hex is which.

```bash
python3 skills/chart-brand/scripts/write_matplotlibrc.py \
  --theme skills/chart-brand/assets/dodge-demo.toml \
  --out examples/brand-hex-sample
```

That command warns three times on this palette. Green is both a series and the up color. Red is both the accent and the down color. The yellow wash fails as a bar fill. One meaning per hue on a given chart.

![Sample bars in the Dodge Labs theme](examples/brand-hex-sample/bars.png)

![Sample lines in the Dodge Labs theme](examples/brand-hex-sample/lines.png)

![Sample variance in the Dodge Labs theme](examples/brand-hex-sample/variance.png)

A hex list you type takes the same path. The hexes are the series cycle, in the order you pass them.

```bash
python3 skills/chart-brand/scripts/write_matplotlibrc.py \
  --name "Acme" \
  --hex 14133D 2D8A56 \
  --out chart-theme
```

Colors taken from a stylesheet or a slide stay a proposal until a person confirms them. `palette_from_css.py` and `palette_from_image.py` print that proposal. `write_matplotlibrc.py` will refuse an unconfirmed file until you pass `--confirm`.

## Requirements

Python 3.9 or newer. Text charts and theme files use the standard library.

Proof PNGs need matplotlib. `palette_from_image.py` needs Pillow. Apply the theme with matplotlib. If you also use seaborn, load the `matplotlibrc` after `sns.set_theme`, because `set_theme` replaces the color cycle.

## v1 boundary

v1 writes files on disk: text charts, plus matplotlib and seaborn. Chart.js, hosted chart APIs, and MCP are outside this version. CSS extraction reads static stylesheets. It does not run JavaScript.

## License

MIT. Copyright Dodge Labs LLC. See [LICENSE](LICENSE).
