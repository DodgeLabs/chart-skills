#!/usr/bin/env python3
# Copyright (c) 2026 Dodge Labs LLC. MIT License.
"""Deterministic horizontal bars for chat and terminals.

Implements the bar rules in references/scale-rules.md. Sparklines, stacked
composition, and diverging bars are drawn by hand from that file and from
references/composition-patterns.md. This script refuses negative values.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

# Keep in sync with references/scale-rules.md.
WIDTH_MIN = 40
WIDTH_MAX = 60
WIDTH_DEFAULT = 50
LABEL_MAX = 24
CLIP_RATIO = 3.0
NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0)

FULL = "█"
EMPTY = "░"
EIGHTHS = ("", "▏", "▎", "▍", "▌", "▋", "▊", "▉")
ASCII_FULL = "#"
ASCII_EMPTY = "."

NUMBER_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def round_half_up(value: float) -> int:
    """Half rounds away from zero for the positive values this script draws."""
    return int(math.floor(value + 0.5))


def nice_ceil(value: float) -> float:
    """Smallest 1, 2, 2.5, 5, 10 × 10^k that is >= value. Zero maps to 1."""
    if value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    power = 10.0 ** exponent
    # log10 can land just below an integer on exact powers of ten.
    if value / power > 10 - 1e-9:
        exponent += 1
        power *= 10
    fraction = value / power
    for step in NICE_STEPS:
        if fraction <= step + 1e-9:
            return step * power
    return 10 * power


def fmt_number(value: float) -> str:
    if abs(value - round(value)) < 1e-8:
        return f"{int(round(value)):,}"
    text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return text


def clip_label(label: str, *, ascii_mode: bool = False) -> str:
    label = " ".join(label.split())
    if not label:
        raise ValueError("a row has an empty label")
    if len(label) <= LABEL_MAX:
        return label
    if ascii_mode:
        return label[: LABEL_MAX - 3] + "..."
    return label[: LABEL_MAX - 1] + "…"


def parse_number(raw: str) -> float:
    text = raw.strip().replace("_", "").replace(",", "")
    if not NUMBER_RE.fullmatch(text):
        raise ValueError(f"not a number: {raw.strip()!r}")
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"not a finite number: {raw.strip()!r}")
    return value


def parse_line(line: str, line_no: int) -> tuple[str, float] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "\t" in line:
        label, raw_value = line.split("\t", 1)
    elif "=" in stripped and _rhs_is_number(stripped.split("=", 1)[1]):
        label, raw_value = stripped.split("=", 1)
    elif "," in stripped and _rhs_is_number(stripped.rsplit(",", 1)[1]):
        label, raw_value = stripped.rsplit(",", 1)
    else:
        parts = stripped.rsplit(None, 1)
        if len(parts) != 2:
            raise ValueError(f"line {line_no}: expected a label and a number")
        label, raw_value = parts
    label = label.strip().strip('"').strip("'")
    try:
        value = parse_number(raw_value)
    except ValueError as exc:
        raise ValueError(f"line {line_no}: {exc}") from exc
    return label, value


def _rhs_is_number(raw: str) -> bool:
    try:
        parse_number(raw.strip().strip('"').strip("'"))
    except ValueError:
        return False
    return True


def parse_pairs(text: str) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    parts = text.split(";")
    if not any(part.strip() for part in parts):
        raise ValueError("--pairs was empty")
    for index, part in enumerate(parts, start=1):
        piece = part.strip()
        if not piece:
            raise ValueError(f"--pairs entry {index} is empty")
        if "=" not in piece:
            raise ValueError(
                f"--pairs entry {index} needs label=number "
                "(use a file if the label contains '=')"
            )
        label, raw_value = piece.split("=", 1)
        try:
            value = parse_number(raw_value)
        except ValueError as exc:
            raise ValueError(f"--pairs entry {index}: {exc}") from exc
        rows.append((label.strip(), value))
    return rows


def load_rows(args: argparse.Namespace) -> list[tuple[str, float]]:
    if args.pairs is not None and args.file:
        raise ValueError("pass --pairs or --file, not both")
    if args.pairs is not None:
        return parse_pairs(args.pairs)
    if args.file:
        path = Path(args.file)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"could not read {path}: {exc}") from exc
        source = text.splitlines()
    elif not sys.stdin.isatty():
        source = sys.stdin.read().splitlines()
    else:
        raise ValueError("no data. Pass --pairs, --file, or pipe rows on stdin")
    rows: list[tuple[str, float]] = []
    for line_no, line in enumerate(source, start=1):
        parsed = parse_line(line, line_no)
        if parsed is not None:
            rows.append(parsed)
    if not rows:
        raise ValueError("no data rows")
    return rows


def clipped_indexes(values: list[float]) -> set[int]:
    """Clip a short leading run that is >= 3× the next lower value.

    A run is clipped only when it is shorter than half the rows and at least
    one row remains. Ties at the top are one run, not a pile of outliers.
    """
    if len(values) < 3:
        return set()
    clipped: set[int] = set()
    remaining = set(range(len(values)))
    while len(remaining) >= 2:
        levels = sorted({values[i] for i in remaining}, reverse=True)
        if len(levels) < 2:
            break
        top_value, next_value = levels[0], levels[1]
        run = {i for i in remaining if values[i] == top_value}
        if len(run) >= len(values) / 2:
            break
        if top_value + 1e-9 < CLIP_RATIO * next_value:
            break
        if next_value <= 0 and top_value <= 0:
            break
        clipped |= run
        remaining -= run
    return clipped


def track(value: float, top: float, width: int, *, ascii_mode: bool, clipped: bool) -> str:
    if clipped or value >= top - 1e-12:
        if ascii_mode:
            return ASCII_FULL * width
        return FULL * width
    exact = 0.0 if top <= 0 else (value / top) * width
    if ascii_mode:
        cells = round_half_up(exact)
        if value > 0 and cells == 0:
            cells = 1
        cells = min(width, cells)
        return ASCII_FULL * cells + ASCII_EMPTY * (width - cells)
    full = int(math.floor(exact + 1e-12))
    eighth = round_half_up((exact - full) * 8)
    if eighth == 8:
        full += 1
        eighth = 0
    if value > 0 and full == 0 and eighth == 0:
        eighth = 1
    if full >= width:
        return FULL * width
    return FULL * full + EIGHTHS[eighth] + EMPTY * (width - full - (1 if eighth else 0))


def render(
    rows: list[tuple[str, float]],
    *,
    width: int,
    ascii_mode: bool,
    title: str | None,
    unit: str | None,
    maximum: float | None,
    auto_clip: bool,
    sort: str,
) -> str:
    if not WIDTH_MIN <= width <= WIDTH_MAX:
        raise ValueError(f"width must be {WIDTH_MIN}–{WIDTH_MAX}")
    if maximum is not None and maximum <= 0:
        raise ValueError("--max must be > 0")
    cleaned: list[tuple[str, float]] = []
    for label, value in rows:
        if value < 0:
            raise ValueError(
                "negative value "
                f"({clip_label(label)}, {fmt_number(value)}). "
                "render_bars.py only draws values >= 0. "
                "Hand-render a diverging bar from references/scale-rules.md"
            )
        cleaned.append((clip_label(label, ascii_mode=ascii_mode), value))
    if sort == "value":
        cleaned.sort(key=lambda row: (-row[1], row[0]))
    elif sort == "label":
        cleaned.sort(key=lambda row: row[0].casefold())
    elif sort != "input":
        raise ValueError(f"unknown sort {sort!r}")

    values = [value for _, value in cleaned]
    if maximum is not None:
        top = maximum
        clipped = {i for i, value in enumerate(values) if value > top + 1e-9}
    elif auto_clip:
        clipped = clipped_indexes(values)
        body = [value for i, value in enumerate(values) if i not in clipped]
        top = nice_ceil(max(body) if body else 0.0)
        # A body value that still exceeds the nice top is not a clip.
        clipped = {i for i in clipped if values[i] > top + 1e-9}
    else:
        clipped = set()
        top = nice_ceil(max(values) if values else 0.0)

    label_width = max(len(label) for label, _ in cleaned)
    value_width = max(len(fmt_number(value)) for value in values)
    lines: list[str] = []
    if title:
        lines.append(title)
        lines.append("")
    for index, (label, value) in enumerate(cleaned):
        bar = track(value, top, width, ascii_mode=ascii_mode, clipped=index in clipped)
        number = fmt_number(value).rjust(value_width)
        suffix = "  clipped" if index in clipped else ""
        lines.append(f"{label.ljust(label_width)}  {bar}  {number}{suffix}")
    lines.append("")
    if clipped:
        names = ", ".join(
            f"{cleaned[i][0]} ({fmt_number(cleaned[i][1])})" for i in sorted(clipped)
        )
        lines.append(f"Clipped to the body of the data: {names}.")
    if ascii_mode:
        lines.append(f"Scale 0-{fmt_number(top)} | width {width} | #.")
    else:
        lines.append(f"Scale 0–{fmt_number(top)} · width {width} · █░")
    if unit:
        lines.append(f"Units: {unit}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render_bars.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Draw a zero-baseline horizontal bar chart as text.\n"
            "The bar track is 40–60 characters (default 50). "
            "A value at least 3× the next one, and in a short leading run, "
            "is drawn full and marked clipped. Pass --no-clip to keep the true max."
        ),
        epilog=(
            "examples:\n"
            "  python3 render_bars.py --pairs \"West=42;East=21;North=8\"\n"
            "  python3 render_bars.py --ascii --width 40 --title Regions --file data.tsv\n"
            "  python3 render_bars.py --no-clip --pairs \"Launch=180;Build=41\"\n"
            "\n"
            "rows from --file or stdin, one per line:\n"
            "  label<TAB>number\n"
            "  label=number\n"
            "  label,number\n"
            "  label number\n"
            "Blank lines and lines starting with # are ignored.\n"
            "Comma form does not allow thousands separators in the number.\n"
            "Labels in --pairs cannot contain ';' or '='.\n"
            "\n"
            "Negatives are an error. Draw those as a diverging bar\n"
            "from references/scale-rules.md.\n"
        ),
    )
    parser.add_argument(
        "--pairs",
        help="rows as Label=number separated by semicolons",
    )
    parser.add_argument("--file", help="read rows from this UTF-8 text file")
    parser.add_argument("--title", help="line printed above the bars")
    parser.add_argument("--unit", help="footer phrase, e.g. 'USD thousands'")
    parser.add_argument(
        "--width",
        type=int,
        default=WIDTH_DEFAULT,
        help=f"bar track width, {WIDTH_MIN}–{WIDTH_MAX} (default {WIDTH_DEFAULT})",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="use # and . instead of unicode blocks",
    )
    parser.add_argument(
        "--max",
        type=float,
        dest="maximum",
        help="explicit scale top. Values above it are marked clipped",
    )
    parser.add_argument(
        "--no-clip",
        action="store_true",
        help="scale to the true maximum instead of clipping outliers",
    )
    parser.add_argument(
        "--sort",
        choices=("input", "value", "label"),
        default="input",
        help="row order (default: input)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = load_rows(args)
        chart = render(
            rows,
            width=args.width,
            ascii_mode=args.ascii,
            title=args.title,
            unit=args.unit,
            maximum=args.maximum,
            auto_clip=not args.no_clip,
            sort=args.sort,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(chart)
    return 0


if __name__ == "__main__":
    sys.exit(main())
