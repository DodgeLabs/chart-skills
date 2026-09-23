#!/usr/bin/env python3
# Copyright (c) 2026 Dodge Labs LLC. MIT License.
"""Propose a palette from a slide or screenshot. Does not write a confirmed theme."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import brandio  # noqa: E402

MAX_SIDE = 180


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palette_from_image.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Quantize an image and print a palette proposal.\n"
            "Needs Pillow. Writes a toml only with --proposal, and that file is\n"
            "status = unconfirmed. write_matplotlibrc.py will refuse it without --confirm.\n"
            "This does not see type, logos, or which color is the brand. A person confirms."
        ),
    )
    parser.add_argument("image", type=Path, help="PNG, JPEG, or other file Pillow can open")
    parser.add_argument("--colors", type=int, default=6, help="data colors to suggest (default 6)")
    parser.add_argument("--proposal", type=Path, help="write an unconfirmed brand.toml proposal")
    parser.add_argument("--name", help="proposal name. Default: file stem")
    return parser


def quantize(path: Path, colors: int) -> list[tuple[str, int, int]]:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise brandio.ThemeError(
            "palette_from_image.py needs Pillow. Install with: pip install pillow\n"
            "Did not guess colors from the file."
        ) from exc
    try:
        image = Image.open(path)
    except OSError as exc:
        raise brandio.ThemeError(f"could not open {path}: {exc}") from exc
    image = image.convert("RGBA")
    canvas = Image.new("RGB", image.size, (255, 255, 255))
    canvas.paste(image, mask=image.getchannel("A"))
    longest = max(canvas.size)
    if longest > MAX_SIDE:
        scale = MAX_SIDE / longest
        size = (max(1, int(canvas.width * scale)), max(1, int(canvas.height * scale)))
        canvas = canvas.resize(size, Image.Resampling.LANCZOS)
    palette_size = max(colors + 4, 8)
    quantized = canvas.quantize(
        colors=palette_size,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    raw_palette = quantized.getpalette() or []
    counts = quantized.getcolors() or []
    total = sum(count for count, _index in counts) or 1
    ranked: list[tuple[str, int, int]] = []
    for count, index in sorted(counts, reverse=True):
        start = index * 3
        rgb = tuple(raw_palette[start : start + 3])
        if len(rgb) != 3:
            continue
        ranked.append((brandio.to_hex(rgb), count, total))  # type: ignore[arg-type]
    return ranked


def propose(ranked: list[tuple[str, int, int]], colors: int, source: str, name: str) -> dict:
    buckets: dict[str, list[str]] = {"background": [], "ink": [], "mark": [], "data": []}
    for hex_color, _count, _total in ranked:
        kind = brandio.classify(brandio.parse_hex(hex_color))
        if hex_color not in buckets[kind]:
            buckets[kind].append(hex_color)
    data = buckets["data"][:colors]
    if not data:
        raise brandio.ThemeError(
            "no mid-tone data colors survived quantization. "
            "The image may be mostly paper and type. Nothing was proposed as a series."
        )
    theme = brandio.theme_from_hexes(
        name,
        data,
        source=f"image proposal from {source}",
        status="unconfirmed",
        background=buckets["background"][0] if buckets["background"] else None,
        ink=buckets["ink"][0] if buckets["ink"] else None,
        mark=buckets["mark"][0] if buckets["mark"] else None,
    )
    theme["note"] = (
        "Unconfirmed image proposal from median-cut quantization. "
        "Pixel count is not brand importance. A person has to approve the series list."
    )
    return theme


def render_report(path: Path, ranked: list[tuple[str, int, int]], proposal_path: Path | None) -> str:
    lines = [f"Source: {path}", "", "Quantized colors:"]
    for hex_color, count, total in ranked:
        kind = brandio.classify(brandio.parse_hex(hex_color))
        share = 100 * count / total
        lines.append(f"  {share:5.1f}%  {hex_color}  {kind}")
    lines.append("")
    lines.append("Near-white, near-black, and highlighter washes are not series colors.")
    lines.append("Transparent pixels were flattened onto white before quantization.")
    lines.append("")
    lines.append(brandio.proposal_footer(proposal_path))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.colors < 1 or args.colors > 8:
        print("error: --colors must be 1–8", file=sys.stderr)
        return 2
    try:
        ranked = quantize(args.image, args.colors)
        if not ranked:
            raise brandio.ThemeError(f"no colors read from {args.image}")
        report = render_report(args.image, ranked, args.proposal)
    except brandio.ThemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(report)
    try:
        name = args.name or args.image.stem
        theme = propose(ranked, args.colors, str(args.image), name)
    except brandio.ThemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    issues = brandio.check_theme(brandio.normalize(theme))
    if issues:
        print("Contrast on this proposal, before a person edits it:")
        for level, message in issues:
            print(f"  {level}: {message}")
    if args.proposal:
        try:
            args.proposal.parent.mkdir(parents=True, exist_ok=True)
            args.proposal.write_text(brandio.theme_text(theme), encoding="utf-8")
        except OSError as exc:
            print(f"error: could not write {args.proposal}: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {args.proposal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
