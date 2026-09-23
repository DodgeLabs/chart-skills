#!/usr/bin/env python3
# Copyright (c) 2026 Dodge Labs LLC. MIT License.
"""Write brand.toml, matplotlibrc, and proof PNGs from a hex list or a theme."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import brandio  # noqa: E402

PROOFS = ("bars.png", "lines.png", "variance.png")

LINE_SERIES = (
    ("Advisory", (20, 22, 21, 24, 28, 27, 30, 33)),
    ("Projects", (14, 15, 18, 17, 16, 22, 25, 24)),
    ("Workshops", (6, 8, 7, 11, 10, 9, 12, 14)),
    ("Support", (10, 10, 11, 12, 12, 13, 13, 14)),
    ("Internal", (4, 5, 5, 6, 8, 7, 9, 8)),
    ("Community", (3, 4, 4, 5, 5, 6, 6, 7)),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="write_matplotlibrc.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Turn a hex list or a brand.toml into a matplotlib theme and proof figures.\n"
            "The hex list is the categorical series, in the order given. It is not extended.\n"
            "A theme with status = \"unconfirmed\" is refused unless --confirm is set.\n"
            "--confirm means a person already approved that palette."
        ),
        epilog=(
            "examples:\n"
            "  python3 write_matplotlibrc.py --name \"Acme\" --hex 14133D 2D8A56 \\\n"
            "      --background F7F5F3 --ink 1F1F1F --out chart-theme\n"
            "  python3 write_matplotlibrc.py --theme brand.toml --out chart-theme\n"
            "  python3 write_matplotlibrc.py --theme proposal.toml --confirm --out chart-theme\n"
            "\n"
            "Proof PNGs use sample data. They are a review of the theme, not a client figure.\n"
            "Load the rc after any seaborn set_theme call. See references/matplotlibrc-template.md.\n"
        ),
    )
    parser.add_argument("--theme", type=Path, help="existing brand.toml or palette proposal")
    parser.add_argument("--name", help="theme name. Required with --hex. Overrides --theme")
    parser.add_argument("--hex", nargs="+", help="categorical series, in order")
    parser.add_argument("--background", help="background hex")
    parser.add_argument("--ink", help="text hex")
    parser.add_argument("--accent", help="callout hex. Not added to the series cycle")
    parser.add_argument("--positive", help="up / favorable hex")
    parser.add_argument("--negative", help="down / unfavorable hex")
    parser.add_argument("--mark", help="highlighter wash. Not a bar color")
    parser.add_argument("--font", help="sans-serif family to list first in the rc file")
    parser.add_argument("--size", type=int, help="base font size, 8–24")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("chart-theme"),
        help="directory for brand.toml, matplotlibrc, and proofs (default: ./chart-theme)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="a person approved this palette. Required when status is unconfirmed",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="write even if a contrast check fails. Does not bypass --confirm",
    )
    parser.add_argument(
        "--no-proofs",
        action="store_true",
        help="write brand.toml and matplotlibrc only",
    )
    return parser


def theme_from_args(args: argparse.Namespace) -> dict:
    if args.theme and args.hex:
        raise brandio.ThemeError("pass --theme or --hex, not both")
    if args.theme is None and not args.hex:
        raise brandio.ThemeError("pass --hex or --theme")
    if args.size is not None and not 8 <= args.size <= 24:
        raise brandio.ThemeError("--size must be an integer from 8 to 24")
    overrides = {
        "name": args.name,
        "background": args.background,
        "ink": args.ink,
        "accent": args.accent,
        "positive": args.positive,
        "negative": args.negative,
        "mark": args.mark,
        "font": args.font,
        "size": args.size,
    }
    if args.hex:
        if not args.name:
            raise brandio.ThemeError("--name is required with --hex")
        theme = brandio.theme_from_hexes(args.name, args.hex, font=args.font, size=args.size)
        # theme_from_hexes already applied font and size. Re-apply color overrides only.
        overrides["font"] = None
        overrides["size"] = None
        overrides["name"] = None
        brandio.apply_overrides(theme, overrides)
        return theme
    theme = brandio.read_theme(args.theme)
    if theme["status"] == "unconfirmed" and not args.confirm:
        raise brandio.ThemeError(
            f"{args.theme} is unconfirmed. Show it to a person. "
            "Re-run with --confirm only after they approve. --force does not skip this."
        )
    if args.confirm:
        theme["status"] = "confirmed"
    brandio.apply_overrides(theme, overrides)
    return theme


def _footnote(ax, ink: str) -> None:
    ax.annotate(
        "Sample data — not a client result",
        xy=(1, -0.16),
        xycoords="axes fraction",
        ha="right",
        va="top",
        fontsize=8,
        color=ink,
        alpha=0.7,
        annotation_clip=False,
    )


def write_proofs(directory: Path, theme: dict) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    rc_path = directory / "matplotlibrc"
    plt.style.use(str(rc_path))
    import matplotlib.colors as mcolors

    def as_rgb(color: object) -> tuple[int, int, int]:
        return tuple(int(round(channel * 255)) for channel in mcolors.to_rgb(color))

    roles = theme["roles"]
    if as_rgb(plt.rcParams["figure.facecolor"]) != brandio.parse_hex(roles["background"]):
        raise RuntimeError("matplotlibrc did not apply the background color. Hex values must stay quoted.")
    cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    if not cycle or as_rgb(cycle[0]) != brandio.parse_hex(theme["categorical"][0]):
        raise RuntimeError("matplotlibrc did not apply the categorical cycle.")
    ink = roles["ink"]
    written: list[Path] = []

    labels = ["Discovery", "Design", "Build", "Handoff"]
    hours = [18, 27, 41, 14]
    fig, ax = plt.subplots()
    bars = ax.bar(labels, hours, color=roles["primary"], width=0.72, zorder=3)
    ax.set_ylim(0, max(hours) * 1.22)
    ax.set_ylabel("Hours")
    ax.set_title("Sample pipeline")
    for rect, value in zip(bars, hours):
        ax.annotate(
            str(value),
            xy=(rect.get_x() + rect.get_width() / 2, rect.get_height()),
            ha="center",
            va="bottom",
            fontsize=10,
            color=ink,
            xytext=(0, 3),
            textcoords="offset points",
        )
    _footnote(ax, ink)
    path = directory / "bars.png"
    fig.savefig(path)
    plt.close(fig)
    written.append(path)

    weeks = [f"W{i}" for i in range(1, 9)]
    series = LINE_SERIES[: len(theme["categorical"])]
    fig, ax = plt.subplots()
    for name, values in series:
        ax.plot(weeks, values, marker="o", label=name, zorder=3)
    ax.set_ylim(0, max(max(values) for _, values in series) * 1.18)
    ax.set_ylabel("Hours")
    ax.set_title("Sample load")
    ax.legend(loc="upper left")
    _footnote(ax, ink)
    path = directory / "lines.png"
    fig.savefig(path)
    plt.close(fig)
    written.append(path)

    variance_labels = ["Discovery", "Design", "Build", "Handoff"]
    variance = [6, -4, 11, -7]
    colors = [roles["positive"] if value >= 0 else roles["negative"] for value in variance]
    fig, ax = plt.subplots()
    ax.barh(variance_labels, variance, color=colors, height=0.7, zorder=3)
    ax.axvline(0, color=ink, linewidth=0.8, zorder=2)
    ax.invert_yaxis()
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    span = max(abs(value) for value in variance)
    ax.set_xlim(-span * 1.35, span * 1.35)
    ax.set_xlabel("Hours vs plan")
    ax.set_title("Sample variance to plan")
    for index, value in enumerate(variance):
        ax.text(
            value + (0.35 if value >= 0 else -0.35),
            index,
            f"{value:+d}",
            va="center",
            ha="left" if value >= 0 else "right",
            color=ink,
            fontsize=10,
        )
    _footnote(ax, ink)
    path = directory / "variance.png"
    fig.savefig(path)
    plt.close(fig)
    written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        theme = brandio.normalize(theme_from_args(args))
        issues = brandio.check_theme(theme)
    except brandio.ThemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    failures = [message for level, message in issues if level == "fail"]
    warnings = [message for level, message in issues if level == "warn"]
    if failures and not args.force:
        print("error: contrast check failed. Nothing was written.", file=sys.stderr)
        for message in failures:
            print(f"error: {message}", file=sys.stderr)
        for message in warnings:
            print(f"warning: {message}", file=sys.stderr)
        print("Re-run with --force only if a person accepts these failures.", file=sys.stderr)
        return 2
    if args.force and failures:
        warnings = [f"FORCED: {message}" for message in failures] + warnings
    try:
        toml_path, rc_path = brandio.write_theme_files(args.out, theme)
    except OSError as exc:
        print(f"error: could not write theme files: {exc}", file=sys.stderr)
        return 2
    written = [toml_path, rc_path]
    if not args.no_proofs:
        try:
            written.extend(write_proofs(args.out, theme))
        except ModuleNotFoundError:
            print(f"wrote {toml_path}")
            print(f"wrote {rc_path}")
            print(
                "error: matplotlib is not installed, so no proof PNGs were written. "
                "Install matplotlib and re-run, or pass --no-proofs.",
                file=sys.stderr,
            )
            return 3
        except Exception as exc:  # noqa: BLE001 — surface the plot failure, files already exist
            print(f"wrote {toml_path}")
            print(f"wrote {rc_path}")
            print(f"error: proof figures failed: {exc}", file=sys.stderr)
            return 3
    for path in written:
        print(f"wrote {path}")
    for message in warnings:
        print(f"warning: {message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
