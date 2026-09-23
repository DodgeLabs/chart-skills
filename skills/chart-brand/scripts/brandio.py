# Copyright (c) 2026 Dodge Labs LLC. MIT License.
"""Shared theme reader, writer, and contrast checks for chart-brand.

Thresholds match references/contrast.md. The toml shape matches
references/matplotlibrc-template.md.
"""

from __future__ import annotations

import math
from pathlib import Path

# Thresholds are specified in references/contrast.md.
INK_CONTRAST_MIN = 4.5
SERIES_CONTRAST_MIN = 3.0
SERIES_DELTA_E_FAIL = 18.0
SERIES_DELTA_E_WARN = 28.0
SIGN_DELTA_E_MIN = 25.0

SCHEMA = 1
ROOT_KEYS = ("schema", "name", "status", "source", "note", "categorical", "sequential")
ROLE_KEYS = ("primary", "accent", "ink", "background", "positive", "negative", "mark", "grid")
TYPE_KEYS = ("sans", "size")
STATUSES = ("confirmed", "unconfirmed")

# Omitted roles. Also listed in references/matplotlibrc-template.md.
DEFAULT_BACKGROUND = "#FFFFFF"
DEFAULT_INK = "#1C1C1C"
DEFAULT_POSITIVE = "#2D8A56"
DEFAULT_NEGATIVE = "#B23A3A"
DEFAULT_SANS = "DejaVu Sans"
DEFAULT_SIZE = 11

SEQUENTIAL_STOPS = (0.18, 0.38, 0.58, 0.78, 1.0)
GRID_INK_SHARE = 0.18


class ThemeError(ValueError):
    pass


def parse_hex(raw: str) -> tuple[int, int, int]:
    text = raw.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
        raise ThemeError(f"not a 3- or 6-digit hex color: {raw!r}")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def normalize_hex(raw: str) -> str:
    return to_hex(parse_hex(raw))


def _channel_to_linear(channel: int) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _linear_to_channel(value: float) -> int:
    value = min(1.0, max(0.0, value))
    if value <= 0.0031308:
        encoded = 12.92 * value
    else:
        encoded = 1.055 * (value ** (1 / 2.4)) - 0.055
    return int(round(encoded * 255))


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    red, green, blue = (_channel_to_linear(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    left, right = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(left, right), min(left, right)
    return (lighter + 0.05) / (darker + 0.05)


def saturation(rgb: tuple[int, int, int]) -> float:
    peak = max(rgb)
    floor = min(rgb)
    if peak == 0:
        return 0.0
    return (peak - floor) / peak


def _lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    red, green, blue = (_channel_to_linear(channel) for channel in rgb)
    x = red * 0.4124564 + green * 0.3575761 + blue * 0.1804375
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
    z = red * 0.0193339 + green * 0.1191920 + blue * 0.9503041
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883

    def pivot(channel: float) -> float:
        if channel > 0.008856:
            return channel ** (1 / 3)
        return 7.787 * channel + 16 / 116

    fx, fy, fz = pivot(x), pivot(y), pivot(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """CIE76 distance. A warning heuristic, not a certification."""
    l1, a1, b1 = _lab(a)
    l2, a2, b2 = _lab(b)
    return math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linear-light mix. t = 0 returns a, t = 1 returns b."""
    mixed = []
    for left, right in zip(a, b):
        mixed.append(
            _linear_to_channel(_channel_to_linear(left) * (1 - t) + _channel_to_linear(right) * t)
        )
    return mixed[0], mixed[1], mixed[2]


def classify(rgb: tuple[int, int, int]) -> str:
    """background, mark, ink, or data. Used by the palette proposals."""
    lum = relative_luminance(rgb)
    sat = saturation(rgb)
    if lum >= 0.90 and sat < 0.15:
        return "background"
    if lum >= 0.85 and sat >= 0.15:
        return "mark"
    if lum <= 0.18 and sat < 0.12:
        return "ink"
    return "data"


def sequential_palette(
    background: tuple[int, int, int], primary: tuple[int, int, int]
) -> list[str]:
    return [to_hex(mix(background, primary, stop)) for stop in SEQUENTIAL_STOPS]


def grid_color(ink: tuple[int, int, int], background: tuple[int, int, int]) -> str:
    return to_hex(mix(background, ink, GRID_INK_SHARE))


def _toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _strip_comment(line: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    for char in line:
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            out.append(char)
            continue
        if char == "#":
            break
        out.append(char)
    return "".join(out).strip()


def _unquote(raw: str, key: str) -> str:
    if len(raw) < 2 or not raw.endswith('"'):
        raise ThemeError(f"{key} has an unterminated string")
    out: list[str] = []
    escaped = False
    for char in raw[1:-1]:
        if escaped:
            out.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(char, char))
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            out.append(char)
    if escaped:
        raise ThemeError(f"{key} ends with a dangling escape")
    return "".join(out)


def _parse_scalar(raw: str, key: str) -> object:
    if raw.startswith('"'):
        return _unquote(raw, key)
    if raw in ("true", "false"):
        return raw == "true"
    if re_int(raw):
        return int(raw)
    if re_float(raw):
        return float(raw)
    raise ThemeError(f"could not parse {key} = {raw}")


def re_int(raw: str) -> bool:
    if not raw:
        return False
    body = raw[1:] if raw[0] in "+-" else raw
    return body.isdigit()


def re_float(raw: str) -> bool:
    body = raw[1:] if raw[:1] in "+-" else raw
    if body.count(".") != 1:
        return False
    left, right = body.split(".")
    return (left.isdigit() or left == "") and (right.isdigit() or right == "") and body != "."


def read_theme(path: Path) -> dict:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ThemeError(f"could not read {path}: {exc}") from exc
    root: dict = {}
    sections: dict[str, dict] = {}
    current_name: str | None = None
    current: dict = root
    index = 0
    while index < len(lines):
        line = _strip_comment(lines[index])
        index += 1
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip()
            if name not in ("roles", "type"):
                raise ThemeError(f"unknown table [{name}]")
            if name in sections:
                raise ThemeError(f"duplicate table [{name}]")
            sections[name] = {}
            current_name = name
            current = sections[name]
            continue
        if "=" not in line:
            raise ThemeError(f"expected key = value, got {line!r}")
        key, raw_value = (part.strip() for part in line.split("=", 1))
        allowed = ROOT_KEYS if current_name is None else (ROLE_KEYS if current_name == "roles" else TYPE_KEYS)
        if key not in allowed:
            where = "root" if current_name is None else current_name
            raise ThemeError(f"unknown {where} key {key!r}")
        if key in current:
            raise ThemeError(f"duplicate key {key}")
        if raw_value.startswith("["):
            body = raw_value
            while "]" not in body:
                if index >= len(lines):
                    raise ThemeError(f"{key} array is not closed")
                body += _strip_comment(lines[index])
                index += 1
            if not body.endswith("]"):
                raise ThemeError(f"{key} array has trailing text")
            inner = body[1:-1].strip()
            items: list[str] = []
            if inner:
                for piece in inner.split(","):
                    piece = piece.strip()
                    if not piece:
                        continue
                    value = _parse_scalar(piece, key)
                    if not isinstance(value, str):
                        raise ThemeError(f"{key} entries must be strings")
                    items.append(value)
            current[key] = items
            continue
        current[key] = _parse_scalar(raw_value, key)
    theme = {
        "schema": root.get("schema", SCHEMA),
        "name": root.get("name", ""),
        "status": root.get("status", "confirmed"),
        "source": root.get("source", ""),
        "note": root.get("note", ""),
        "categorical": list(root.get("categorical") or []),
        "sequential": list(root.get("sequential") or []),
        "roles": dict(sections.get("roles") or {}),
        "type": dict(sections.get("type") or {}),
    }
    _validate_loaded(theme, path)
    return theme


def _validate_loaded(theme: dict, path: Path) -> None:
    if theme["schema"] != SCHEMA:
        raise ThemeError(f"{path} has schema {theme['schema']}; this package writes schema {SCHEMA}")
    if not isinstance(theme["name"], str) or not theme["name"].strip():
        raise ThemeError(f"{path} needs a name")
    if theme["status"] not in STATUSES:
        raise ThemeError(f"{path} status must be confirmed or unconfirmed")
    if not theme["categorical"]:
        raise ThemeError(f"{path} needs a categorical list")
    theme["categorical"] = [_as_hex(item, "categorical") for item in theme["categorical"]]
    theme["sequential"] = [_as_hex(item, "sequential") for item in theme["sequential"]]
    roles = {}
    for key, value in theme["roles"].items():
        if value in ("", None):
            continue
        if not isinstance(value, str):
            raise ThemeError(f"roles.{key} must be a hex string")
        roles[key] = _as_hex(value, f"roles.{key}")
    theme["roles"] = roles
    size = theme["type"].get("size", DEFAULT_SIZE)
    if isinstance(size, float) and size.is_integer():
        size = int(size)
    if not isinstance(size, int) or not 8 <= size <= 24:
        raise ThemeError("type.size must be an integer from 8 to 24")
    sans = theme["type"].get("sans", DEFAULT_SANS)
    if not isinstance(sans, str) or not sans.strip():
        raise ThemeError("type.sans must be a font family name")
    theme["type"] = {"sans": sans.strip(), "size": size}
    for key in ("source", "note"):
        if not isinstance(theme[key], str):
            raise ThemeError(f"{key} must be a string")


def _as_hex(value: str, key: str) -> str:
    try:
        return normalize_hex(value)
    except ThemeError as exc:
        raise ThemeError(f"{key}: {exc}") from exc


def theme_from_hexes(
    name: str,
    hexes: list[str],
    *,
    source: str = "hex list",
    status: str = "confirmed",
    note: str = "",
    background: str | None = None,
    ink: str | None = None,
    accent: str | None = None,
    positive: str | None = None,
    negative: str | None = None,
    mark: str | None = None,
    font: str | None = None,
    size: int | None = None,
) -> dict:
    if not name.strip():
        raise ThemeError("name is empty")
    if not hexes:
        raise ThemeError("pass at least one hex color")
    categorical = [_as_hex(item, "hex") for item in hexes]
    roles = {
        "primary": categorical[0],
        "accent": _as_hex(accent, "accent") if accent else categorical[0],
        "background": _as_hex(background, "background") if background else DEFAULT_BACKGROUND,
        "ink": _as_hex(ink, "ink") if ink else DEFAULT_INK,
        "positive": _as_hex(positive, "positive") if positive else DEFAULT_POSITIVE,
        "negative": _as_hex(negative, "negative") if negative else DEFAULT_NEGATIVE,
    }
    if mark:
        roles["mark"] = _as_hex(mark, "mark")
    return {
        "schema": SCHEMA,
        "name": name.strip(),
        "status": status,
        "source": source,
        "note": note,
        "categorical": categorical,
        "sequential": [],
        "roles": roles,
        "type": {"sans": (font or DEFAULT_SANS).strip(), "size": size or DEFAULT_SIZE},
    }


def apply_overrides(theme: dict, overrides: dict) -> None:
    roles = theme["roles"]
    for key in ("background", "ink", "accent", "positive", "negative", "mark"):
        if overrides.get(key):
            roles[key] = _as_hex(overrides[key], key)
    if overrides.get("font"):
        theme["type"]["sans"] = overrides["font"].strip()
    if overrides.get("size"):
        theme["type"]["size"] = overrides["size"]
    if overrides.get("name"):
        theme["name"] = overrides["name"].strip()


def normalize(theme: dict) -> dict:
    """Fill derived sequential and grid colors. Does not drop explicit values."""
    roles = theme["roles"]
    if "primary" not in roles:
        roles["primary"] = theme["categorical"][0]
    background = parse_hex(roles.get("background", DEFAULT_BACKGROUND))
    ink = parse_hex(roles.get("ink", DEFAULT_INK))
    primary = parse_hex(roles["primary"])
    roles.setdefault("background", to_hex(background))
    roles.setdefault("ink", to_hex(ink))
    roles.setdefault("accent", roles["primary"])
    roles.setdefault("positive", DEFAULT_POSITIVE)
    roles.setdefault("negative", DEFAULT_NEGATIVE)
    if "grid" not in roles:
        roles["grid"] = grid_color(ink, background)
    if not theme["sequential"]:
        theme["sequential"] = sequential_palette(background, primary)
    return theme


def check_theme(theme: dict) -> list[tuple[str, str]]:
    """Return (level, message). level is 'fail' or 'warn'. Assumes normalize()."""
    issues: list[tuple[str, str]] = []
    roles = theme["roles"]
    background = parse_hex(roles["background"])
    ink = parse_hex(roles["ink"])
    ink_ratio = contrast_ratio(ink, background)
    if ink_ratio < INK_CONTRAST_MIN:
        issues.append(
            (
                "fail",
                f"ink {roles['ink']} on background {roles['background']} is "
                f"{ink_ratio:.2f}:1. Need >= {INK_CONTRAST_MIN}:1.",
            )
        )
    positive = parse_hex(roles["positive"])
    negative = parse_hex(roles["negative"])
    series = [parse_hex(item) for item in theme["categorical"]]
    if len(series) > 12:
        issues.append(("fail", f"{len(series)} series colors is too many. Keep 12 or fewer."))
    elif len(series) > 6:
        issues.append(
            (
                "warn",
                f"{len(series)} series colors is a lot. A chart that needs more than 6 is usually the wrong chart.",
            )
        )
    for index, (label, rgb) in enumerate(zip(theme["categorical"], series)):
        ratio = contrast_ratio(rgb, background)
        if ratio < SERIES_CONTRAST_MIN:
            issues.append(
                (
                    "fail",
                    f"series {label} on background {roles['background']} is {ratio:.2f}:1. "
                    f"Need >= {SERIES_CONTRAST_MIN}:1 or the bar disappears.",
                )
            )
        for other_label, other in zip(theme["categorical"][index + 1 :], series[index + 1 :]):
            distance = delta_e(rgb, other)
            if distance < SERIES_DELTA_E_FAIL:
                issues.append(
                    (
                        "fail",
                        f"{label} and {other_label} are {distance:.0f} apart (ΔE76). "
                        f"Need >= {SERIES_DELTA_E_FAIL:.0f} to use both as series.",
                    )
                )
            elif distance < SERIES_DELTA_E_WARN:
                issues.append(
                    (
                        "warn",
                        f"{label} and {other_label} are close (ΔE76 {distance:.0f}). "
                        "They may be hard to tell apart.",
                    )
                )
        neg_distance = delta_e(rgb, negative)
        if 1 <= neg_distance < SERIES_DELTA_E_WARN:
            issues.append(
                (
                    "warn",
                    f"series {label} is close to negative {roles['negative']} "
                    f"(ΔE76 {neg_distance:.0f}). It will be read as a loss.",
                )
            )
    sign_distance = delta_e(positive, negative)
    if sign_distance < SIGN_DELTA_E_MIN:
        issues.append(
            (
                "fail",
                f"positive {roles['positive']} and negative {roles['negative']} are "
                f"{sign_distance:.0f} apart (ΔE76). Need >= {SIGN_DELTA_E_MIN:.0f}.",
            )
        )
    for label, rgb in zip(theme["categorical"], series):
        if delta_e(rgb, positive) < 1:
            issues.append(
                (
                    "warn",
                    f"positive {roles['positive']} is also a series color ({label}). "
                    "Do not use it for sign and for a series on the same axes.",
                )
            )
            break
    accent = parse_hex(roles["accent"])
    if delta_e(accent, negative) < 1:
        issues.append(
            (
                "warn",
                f"accent {roles['accent']} and negative {roles['negative']} are the same hue. "
                "One meaning per chart.",
            )
        )
    if any(delta_e(accent, rgb) < 1 for rgb in series):
        issues.append(
            (
                "warn",
                f"accent {roles['accent']} is also a series color. "
                "A highlighted bar will look like that series.",
            )
        )
    if roles["primary"] != theme["categorical"][0]:
        issues.append(
            (
                "warn",
                f"primary {roles['primary']} is not categorical[0] ({theme['categorical'][0]}). "
                "Single-series charts use primary. The cycle uses categorical order.",
            )
        )
    mark = roles.get("mark")
    if mark:
        ratio = contrast_ratio(parse_hex(mark), background)
        if ratio < SERIES_CONTRAST_MIN:
            issues.append(
                (
                    "warn",
                    f"mark {mark} contrasts {ratio:.2f}:1 with the background. "
                    "Use it as a wash, not a bar.",
                )
            )
    return issues


def theme_text(theme: dict) -> str:
    lines = [
        "# chart-brand theme file.",
        "# Edit, then run write_matplotlibrc.py --theme on it. Delete sequential or grid to derive them again.",
        "",
        f"schema = {SCHEMA}",
        f"name = {_toml_string(theme['name'])}",
        f"status = {_toml_string(theme['status'])}",
        f"source = {_toml_string(theme['source'])}",
    ]
    if theme.get("note"):
        lines.append(f"note = {_toml_string(theme['note'])}")
    lines.append("")
    lines.extend(_array("categorical", theme["categorical"]))
    lines.append("")
    lines.extend(_array("sequential", theme["sequential"]))
    lines.append("")
    lines.append("[roles]")
    for key in ROLE_KEYS:
        if key in theme["roles"] and theme["roles"][key]:
            lines.append(f"{key} = {_toml_string(theme['roles'][key])}")
    lines.append("")
    lines.append("[type]")
    lines.append(f"sans = {_toml_string(theme['type']['sans'])}")
    lines.append(f"size = {theme['type']['size']}")
    lines.append("")
    return "\n".join(lines)


def _array(key: str, values: list[str]) -> list[str]:
    if not values:
        return [f"{key} = []"]
    lines = [f"{key} = ["]
    lines.extend(f"  {_toml_string(value)}," for value in values)
    lines.append("]")
    return lines


def matplotlibrc_text(theme: dict) -> str:
    roles = theme["roles"]
    sans = theme["type"]["sans"]
    stack = [sans]
    for fallback in ("DejaVu Sans", "Arial", "Helvetica", "sans-serif"):
        if fallback.casefold() not in {item.casefold() for item in stack}:
            stack.append(fallback)
    # Matplotlib treats an unquoted # as a comment. Hex values have to be double-quoted.
    cycle = ", ".join(f'"{color}"' for color in theme["categorical"])
    size = theme["type"]["size"]
    lines = [
        f"# chart-brand theme: {theme['name']}",
        "# Load this AFTER any seaborn set_theme call. set_theme replaces the color cycle.",
        f"# source: {theme['source']}",
        "",
        "font.family: sans-serif",
        f"font.sans-serif: {', '.join(stack)}",
        f"font.size: {size}",
        "",
        f'figure.facecolor: "{roles["background"]}"',
        f'figure.edgecolor: "{roles["background"]}"',
        "figure.dpi: 144",
        "figure.figsize: 7.6, 4.4",
        f'savefig.facecolor: "{roles["background"]}"',
        f'savefig.edgecolor: "{roles["background"]}"',
        "savefig.dpi: 144",
        "savefig.bbox: tight",
        "pdf.fonttype: 42",
        "ps.fonttype: 42",
        "",
        f'text.color: "{roles["ink"]}"',
        f'axes.facecolor: "{roles["background"]}"',
        f'axes.edgecolor: "{roles["ink"]}"',
        f'axes.labelcolor: "{roles["ink"]}"',
        f'axes.titlecolor: "{roles["ink"]}"',
        "axes.titlesize: 14",
        "axes.titlelocation: left",
        "axes.titlepad: 12",
        "axes.linewidth: 0.8",
        "axes.axisbelow: True",
        "axes.grid: True",
        "axes.grid.axis: y",
        "axes.spines.top: False",
        "axes.spines.right: False",
        "axes.unicode_minus: False",
        f"axes.prop_cycle: cycler('color', [{cycle}])",
        "",
        f'grid.color: "{roles["grid"]}"',
        "grid.linewidth: 0.6",
        "grid.alpha: 1",
        "",
        f'xtick.color: "{roles["ink"]}"',
        f'ytick.color: "{roles["ink"]}"',
        "xtick.labelsize: 10",
        "ytick.labelsize: 10",
        "",
        "legend.frameon: False",
        "legend.fontsize: 10",
        "",
        "lines.linewidth: 2.2",
        "lines.solid_capstyle: round",
        "lines.markersize: 6",
        "",
        "patch.linewidth: 0.0",
        "",
    ]
    return "\n".join(lines)


def write_theme_files(directory: Path, theme: dict) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    toml_path = directory / "brand.toml"
    rc_path = directory / "matplotlibrc"
    toml_path.write_text(theme_text(theme), encoding="utf-8")
    rc_path.write_text(matplotlibrc_text(theme), encoding="utf-8")
    return toml_path, rc_path


def proposal_footer(proposal_path: Path | None) -> str:
    target = proposal_path.as_posix() if proposal_path else "PROPOSAL.toml"
    return (
        "Status: unconfirmed.\n"
        "This is a proposal, not a theme. Show it to a person.\n"
        "Do not write brand files until they approve.\n"
        "After they approve:\n"
        "  python3 scripts/write_matplotlibrc.py "
        f"--theme {target} --confirm --out DIR"
    )
