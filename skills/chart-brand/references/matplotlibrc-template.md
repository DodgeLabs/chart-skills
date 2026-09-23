# Theme files

`scripts/write_matplotlibrc.py` writes both files. `scripts/brandio.py` is the reader and the writer. Hand-written toml has to stay inside the shape below or the reader rejects it.

## brand.toml

```toml
schema = 1
name = "Name"
status = "confirmed"          # confirmed, or unconfirmed for a proposal
source = "where the hexes came from"
note = "optional"

categorical = [               # series cycle, in order. Not extended.
  "#RRGGBB",
]

sequential = []               # optional. Five steps, light to dark, if you leave it empty.

[roles]
primary = "#RRGGBB"           # single-series charts. Defaults to categorical[0]
accent = "#RRGGBB"            # callout. Not added to the cycle
ink = "#RRGGBB"
background = "#RRGGBB"
positive = "#RRGGBB"
negative = "#RRGGBB"
mark = "#RRGGBB"              # optional wash
grid = "#RRGGBB"              # optional. Derived if omitted

[type]
sans = "DejaVu Sans"          # listed first. DejaVu Sans, Arial, Helvetica follow
size = 11                     # integer 8–24
```

If a role is omitted, the writer fills background `#FFFFFF`, ink `#1C1C1C`, positive `#2D8A56`, negative `#B23A3A`, and accent from the first series color. Sans defaults to DejaVu Sans at size 11. Those defaults are the constants at the top of `scripts/brandio.py`.

Hex is 3 or 6 digits, with or without `#`. The writer stores uppercase `#RRGGBB`.

`status = "unconfirmed"` is a proposal from `palette_from_css.py` or `palette_from_image.py`. The writer refuses it until `--confirm`.

Deleting `sequential` or `roles.grid` and running the writer again fills them. Sequential is a linear-light mix from background to primary at 18%, 38%, 58%, 78%, and 100%. Grid is background mixed 18% toward ink.

A worked file is `assets/dodge-demo.toml`. Site tokens and chart extensions are distinguished in its `note`.

## matplotlibrc

The writer emits the rc file. Read the generated file for the key list. Hex colors are double-quoted. In a matplotlibrc file an unquoted `#` starts a comment, so `#F7F5F3` would be dropped and the color would not apply.

What that file is doing:

- Figure, axes, and savefig background come from `roles.background`. Text, ticks, and spines come from `roles.ink`.
- `axes.prop_cycle` is `categorical`, in order.
- Top and right spines are off. Gridlines are horizontal, in `roles.grid`, drawn under the data.
- Bar edges are off (`patch.linewidth: 0`).
- PDF and PostScript fonts stay editable (`pdf.fonttype` and `ps.fonttype` are 42).
- Base size is `type.size`. Titles are 14 and left-aligned.

The rc file does not set a zero baseline. When you plot amounts, set the axis to start at zero.

## Load

```python
import matplotlib.pyplot as plt
plt.style.use("chart-theme/matplotlibrc")
```

Seaborn's `set_theme` replaces the color cycle. Call it first, then `style.use` the rc file again so the brand cycle wins.

```python
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style="whitegrid")
plt.style.use("chart-theme/matplotlibrc")
```

## Proofs

The writer also saves three PNGs next to the rc file, unless `--no-proofs`:

| File | What it is checking |
| --- | --- |
| `bars.png` | Chrome and `roles.primary` on one series |
| `lines.png` | The categorical cycle, one line per color |
| `variance.png` | `roles.positive` and `roles.negative` |

The numbers are sample data. A line proof shows at most six series.
