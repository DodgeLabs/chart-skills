#!/usr/bin/env python3
# Copyright (c) 2026 Dodge Labs LLC. MIT License.
"""Propose a palette from static CSS. Does not write a confirmed theme."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import brandio  # noqa: E402

USER_AGENT = "chart-brand/1.0 (palette proposal; +https://github.com/DodgeLabs/chart-skills)"
MAX_BYTES = 1_000_000
MAX_SHEETS = 6
TIMEOUT = 15
ALPHA_MIN = 0.5

HEX_RE = re.compile(r"(?<![A-Za-z0-9])#([0-9A-Fa-f]{8}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![A-Za-z0-9])")
RGB_RE = re.compile(
    r"rgba?\(\s*([0-9.]+%?)\s*(?:,|\s)\s*([0-9.]+%?)\s*(?:,|\s)\s*([0-9.]+%?)"
    r"(?:\s*(?:,|/)\s*([0-9.]+%?))?\s*\)",
    re.IGNORECASE,
)
VAR_RE = re.compile(r"(--[A-Za-z_][\w-]*)\s*:\s*([^;}{]+)")
LINK_RE = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
HREF_RE = re.compile(r"href\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
REL_RE = re.compile(r"rel\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)

# Token must match the whole name piece, so "red" does not fire inside "stored".
ROLE_TOKENS = {
    "background": ("background", "bg", "canvas", "paper"),
    "ink": ("text", "ink", "foreground", "fg"),
    "accent": ("accent", "brand", "red"),
    "positive": ("positive", "success", "green"),
    "negative": ("negative", "danger", "error", "red"),
    "mark": ("highlight", "mark", "marker"),
    "primary": ("primary", "navy"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palette_from_css.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Read hex colors and CSS custom properties from a stylesheet or an HTML page.\n"
            "Prints a proposal. Writes a toml only with --proposal, and that file is\n"
            "status = unconfirmed. write_matplotlibrc.py will refuse it without --confirm.\n"
            "JavaScript-set colors and @import rules are not followed."
        ),
    )
    parser.add_argument("source", help="http(s) URL, HTML file, or CSS file")
    parser.add_argument(
        "--proposal",
        type=Path,
        help="write an unconfirmed brand.toml proposal to this path",
    )
    parser.add_argument("--name", help="proposal name. Default: host or file stem")
    return parser


def _fetch(url: str) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read(MAX_BYTES + 1)
            final = response.geturl()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise brandio.ThemeError(f"could not fetch {url}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise brandio.ThemeError(f"{url} is larger than {MAX_BYTES} bytes. Stopped.")
    charset = "utf-8"
    return raw.decode(charset, errors="replace"), final


def _read_local(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise brandio.ThemeError(f"could not read {path}: {exc}") from exc
    if len(data) > MAX_BYTES:
        raise brandio.ThemeError(f"{path} is larger than {MAX_BYTES} bytes. Stopped.")
    return data.decode("utf-8", errors="replace")


def _channel(raw: str) -> int:
    if raw.endswith("%"):
        return int(round(float(raw[:-1]) / 100 * 255))
    return int(round(float(raw)))


def _alpha(raw: str | None) -> float:
    if raw is None:
        return 1.0
    if raw.endswith("%"):
        return float(raw[:-1]) / 100
    value = float(raw)
    if value > 1:
        return value / 255
    return value


def parse_css_color(raw: str) -> tuple[tuple[int, int, int], float] | None:
    text = raw.strip().rstrip(";").replace("!important", "").strip()
    if text.lower().startswith("var("):
        return None
    hex_match = HEX_RE.search(text)
    if hex_match:
        token = hex_match.group(1)
        if len(token) == 8:
            rgb = brandio.parse_hex(token[:6])
            return rgb, int(token[6:], 16) / 255
        return brandio.parse_hex(token), 1.0
    rgb_match = RGB_RE.search(text)
    if not rgb_match:
        return None
    try:
        rgb = tuple(_channel(rgb_match.group(i)) for i in (1, 2, 3))
    except ValueError:
        return None
    if any(channel < 0 or channel > 255 for channel in rgb):
        return None
    return rgb, _alpha(rgb_match.group(4))  # type: ignore[return-value]


def _looks_like_html(page: str) -> bool:
    head = page[:8000].lower()
    return "<html" in head or "<style" in head or "<body" in head or "<link" in head


def _tokens(name: str) -> set[str]:
    return {piece for piece in re.split(r"[^a-z0-9]+", name.lower()) if piece}


def collect(source: str) -> tuple[str, list[str], list[str]]:
    """Return (display name, list of css texts, notes)."""
    notes: list[str] = []
    parsed = urlparse(source)
    texts: list[str] = []
    if parsed.scheme in ("http", "https"):
        page, final = _fetch(source)
        name = urlparse(final).netloc or source
        base = final
        if not _looks_like_html(page):
            texts.append(page)
            return name, texts, ["Read one stylesheet. Did not execute JavaScript or follow @import."]
        texts.append(page)
        sheets = 0
        for tag in LINK_RE.findall(page):
            rel = REL_RE.search(tag)
            href = HREF_RE.search(tag)
            if not rel or not href or "stylesheet" not in rel.group(1).lower():
                continue
            link = urljoin(base, href.group(1))
            if urlparse(link).scheme not in ("http", "https"):
                notes.append(f"Skipped stylesheet {link}")
                continue
            if sheets >= MAX_SHEETS:
                notes.append(f"Stopped after {MAX_SHEETS} linked stylesheets.")
                break
            try:
                css, _final = _fetch(link)
            except brandio.ThemeError as exc:
                notes.append(str(exc))
                continue
            texts.append(css)
            sheets += 1
        notes.append("Did not execute JavaScript or follow @import.")
        return name, texts, notes
    path = Path(source)
    if not path.is_file():
        raise brandio.ThemeError(f"not a file or http(s) URL: {source}")
    page = _read_local(path)
    name = path.stem
    if path.suffix.lower() in (".css", ".scss"):
        texts.append(page)
        notes.append("Read one local stylesheet. Did not follow @import.")
        return name, texts, notes
    texts.append(page)
    base = path.resolve().parent
    for tag in LINK_RE.findall(page):
        rel = REL_RE.search(tag)
        href = HREF_RE.search(tag)
        if not rel or not href or "stylesheet" not in rel.group(1).lower():
            continue
        link = href.group(1)
        if urlparse(link).scheme in ("http", "https"):
            notes.append(f"Skipped remote stylesheet {link}")
            continue
        local = (base / link).resolve()
        if local.is_file():
            texts.append(_read_local(local))
        else:
            notes.append(f"Missing stylesheet {local}")
    notes.append("Did not execute JavaScript or follow @import.")
    return name, texts, notes


def extract(texts: list[str]) -> tuple[list[tuple[str, str]], Counter, int]:
    """Variables as (name, hex), hex frequency, translucent skipped count."""
    declared: dict[str, str] = {}
    order: list[str] = []
    for text in texts:
        for name, raw in VAR_RE.findall(text):
            if name not in declared:
                order.append(name)
            declared[name] = raw.strip()
    resolved: list[tuple[str, str]] = []
    seen: set[str] = set()

    def resolve(raw: str, depth: int = 0) -> tuple[tuple[int, int, int], float] | None:
        text = raw.strip().rstrip(";").replace("!important", "").strip()
        var_match = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", text)
        if var_match and depth < 4:
            target = declared.get(var_match.group(1))
            if target is None:
                return None
            return resolve(target, depth + 1)
        return parse_css_color(text)

    skipped = 0
    for name in order:
        parsed = resolve(declared[name])
        if parsed is None:
            continue
        rgb, alpha = parsed
        if alpha < ALPHA_MIN:
            continue
        if name in seen:
            continue
        seen.add(name)
        resolved.append((name, brandio.to_hex(rgb)))

    counts: Counter[str] = Counter()
    for text in texts:
        for match in HEX_RE.finditer(text):
            token = match.group(1)
            if len(token) == 8:
                alpha = int(token[6:], 16) / 255
                if alpha < ALPHA_MIN:
                    skipped += 1
                    continue
                token = token[:6]
            counts[brandio.normalize_hex(token)] += 1
        for match in RGB_RE.finditer(text):
            parsed = parse_css_color(match.group(0))
            if parsed is None:
                continue
            rgb, alpha = parsed
            if alpha < ALPHA_MIN:
                skipped += 1
                continue
            counts[brandio.to_hex(rgb)] += 1
    return resolved, counts, skipped


def propose(variables: list[tuple[str, str]], counts: Counter) -> dict:
    buckets = {"background": [], "ink": [], "mark": [], "data": []}
    for _name, hex_color in variables:
        buckets[brandio.classify(brandio.parse_hex(hex_color))].append(hex_color)
    if not buckets["data"]:
        for hex_color, _count in counts.most_common():
            kind = brandio.classify(brandio.parse_hex(hex_color))
            if kind == "data" and hex_color not in buckets["data"]:
                buckets["data"].append(hex_color)
    # Preserve order, drop duplicates.
    data: list[str] = []
    for hex_color in buckets["data"]:
        if hex_color not in data:
            data.append(hex_color)
    if not data:
        raise brandio.ThemeError(
            "no solid data colors found. Background, ink, and translucent colors were set aside."
        )
    categorical = data[:8]
    roles: dict[str, str] = {}
    for name, hex_color in variables:
        tokens = _tokens(name)
        for role, hints in ROLE_TOKENS.items():
            if role in roles:
                continue
            if tokens & set(hints):
                roles[role] = hex_color
    theme = brandio.theme_from_hexes(
        "proposal",
        categorical,
        source="css proposal",
        status="unconfirmed",
        background=roles.get("background"),
        ink=roles.get("ink"),
        accent=roles.get("accent"),
        positive=roles.get("positive"),
        negative=roles.get("negative"),
        mark=roles.get("mark"),
    )
    if roles.get("primary"):
        theme["roles"]["primary"] = roles["primary"]
    theme["note"] = (
        "Unconfirmed CSS proposal. Custom properties are suggestions. "
        "A person has to approve the series list before this becomes a theme. "
        "Pull callout colors, especially reds, out of categorical if they also mean bad or highlight."
    )
    return theme


def render_report(
    source_name: str,
    variables: list[tuple[str, str]],
    counts: Counter,
    skipped: int,
    notes: list[str],
    proposal_path: Path | None,
) -> str:
    lines = [f"Source: {source_name}", ""]
    if variables:
        lines.append("Custom properties:")
        for name, hex_color in variables:
            kind = brandio.classify(brandio.parse_hex(hex_color))
            lines.append(f"  {name}  {hex_color}  {kind}")
        lines.append("")
    else:
        lines.append("No CSS custom properties resolved to solid colors.")
        lines.append("")
    lines.append("Hex by frequency:")
    if counts:
        for hex_color, count in counts.most_common(20):
            kind = brandio.classify(brandio.parse_hex(hex_color))
            lines.append(f"  {count:4d}  {hex_color}  {kind}")
    else:
        lines.append("  none")
    lines.append("")
    if skipped:
        noun = "color" if skipped == 1 else "colors"
        lines.append(f"Skipped {skipped} translucent {noun} (alpha < {ALPHA_MIN}).")
    if variables:
        lines.append(
            "The series suggestion uses custom properties classified as data. "
            "The frequency list also counts icons and embeds."
        )
    for note in notes:
        lines.append(note)
    lines.append("")
    lines.append(brandio.proposal_footer(proposal_path))
    return "\n".join(lines) + "\n"


def _print_issues(theme: dict) -> None:
    issues = brandio.check_theme(brandio.normalize(theme))
    if not issues:
        return
    print("Contrast on this proposal, before a person edits it:")
    for level, message in issues:
        print(f"  {level}: {message}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source_name, texts, notes = collect(args.source)
        variables, counts, skipped = extract(texts)
    except brandio.ThemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = render_report(source_name, variables, counts, skipped, notes, args.proposal)
    sys.stdout.write(report)
    try:
        theme = propose(variables, counts)
    except brandio.ThemeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.name:
        theme["name"] = args.name
    else:
        theme["name"] = source_name
    theme["source"] = f"css proposal from {args.source}"
    _print_issues(theme)
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
