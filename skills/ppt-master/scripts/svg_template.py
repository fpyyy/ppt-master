#!/usr/bin/env python3
"""
PPT Master - Locked SVG Template Tool

Create and apply locked SVG templates without exposing template SVG source to
the runtime agent. The script is the only component that reads template SVGs:
it extracts a compact contract at template-creation time and later fills the
SVG from JSON data.

Usage:
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py inspect <svg_dir>
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py create <svg_dir> <template_id>
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py visualize-content <template_dir>
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py apply <template_dir> <page_stem> --data fill.json -o out.svg
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_llm_xml.py <svg_dir> -o <output_dir>

Examples:
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py inspect reference/AI-template
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py create reference/AI-template bit_locked
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py visualize-content skills/ppt-master/templates/layouts/bit_locked
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py apply skills/ppt-master/templates/layouts/bit_locked content --data fill.json -o projects/demo/svg_output/03_content.svg

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from svg_llm_xml import write_llm_xml_dir  # noqa: E402

SKILL_DIR = SCRIPT_DIR.parent
LAYOUTS_DIR = SKILL_DIR / "templates" / "layouts"

PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z][A-Za-z0-9_]*)\}\}")
SVG_CLOSE_RE = re.compile(r"</svg\s*>\s*$", re.IGNORECASE)
REQUIRED_TEMPLATE_FILES = (
    "title.svg",
    "toc.svg",
    "chapter.svg",
    "content.svg",
    "ending.svg",
)
STANDARD_PAGE_ROLES = {
    "title": "title",
    "toc": "toc",
    "chapter": "chapter",
    "content": "content",
    "ending": "ending",
}
LOCAL_ASSET_EXTS = {
    ".apng",
    ".avif",
    ".gif",
    ".jpg",
    ".jpeg",
    ".png",
    ".svg",
    ".webp",
}
COLOR_ATTRS = ("fill", "stroke", "stop-color", "flood-color", "color")
IGNORED_COLOR_VALUES = {
    "",
    "none",
    "transparent",
    "inherit",
    "initial",
    "unset",
}
NAMED_COLORS = {
    "black": "#000000",
    "white": "#FFFFFF",
    "red": "#FF0000",
    "green": "#008000",
    "blue": "#0000FF",
    "gray": "#808080",
    "grey": "#808080",
}
DEFAULT_FONT_FAMILY = '"Microsoft YaHei", Arial, sans-serif'
DEFAULT_CODE_FAMILY = 'Consolas, "Courier New", monospace'


class TemplateError(RuntimeError):
    """Raised for user-facing template failures."""


@dataclass
class Workspace:
    workspace_id: str
    bbox: tuple[float, float, float, float]
    element: str
    source: str = "declared"


@dataclass
class SvgSummary:
    source: Path
    file_name: str
    stem: str
    role: str
    view_box: str
    sha256: str
    svg_text: str
    placeholders: dict[str, int]
    placeholder_fits: dict[str, dict[str, Any]]
    workspaces: list[Workspace]
    local_assets: list[Path]
    embedded_image_count: int


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _format_float(value: float) -> int | float:
    if value.is_integer():
        return int(value)
    return round(value, 3)


def _safe_xml_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    if not safe or not re.match(r"[A-Za-z_]", safe):
        safe = f"workspace-{safe or 'fill'}"
    return safe


def _parse_number(value: str) -> float:
    match = re.match(r"^\s*(-?\d+(?:\.\d+)?)", value)
    if not match:
        raise TemplateError(f"not a numeric SVG coordinate: {value!r}")
    return float(match.group(1))


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = re.split(r"[\s,]+", value.strip())
    if len(parts) != 4:
        raise TemplateError(
            "data-ppt-workspace-bbox must contain four numbers: x y width height"
        )
    x, y, width, height = (_parse_number(part) for part in parts)
    if width <= 0 or height <= 0:
        raise TemplateError("workspace bbox width and height must be positive")
    return x, y, width, height


def _format_view_box(value: tuple[float, float, float, float]) -> str:
    return " ".join(str(_format_float(part)) for part in value)


def _infer_root_view_box(root: ET.Element, svg_file: Path) -> str:
    width = _parse_optional_number(root.attrib.get("width"))
    height = _parse_optional_number(root.attrib.get("height"))
    if width is None or height is None or width <= 0 or height <= 0:
        raise TemplateError(
            f"{svg_file.name}: missing root viewBox and cannot infer it from width/height"
        )
    return _format_view_box((0, 0, width, height))


def _inject_root_view_box(svg_text: str, view_box: str) -> str:
    if re.search(r"<svg\b[^>]*\bviewBox\s*=", svg_text, re.IGNORECASE):
        return svg_text
    match = re.search(r"<svg\b[^>]*", svg_text, re.IGNORECASE)
    if not match:
        return svg_text
    return svg_text[:match.end()] + f' viewBox="{view_box}"' + svg_text[match.end():]


def _parse_optional_number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return _parse_number(value)
    except TemplateError:
        return None


def _style_value(style: str, name: str) -> str | None:
    for part in style.split(";"):
        key, sep, value = part.partition(":")
        if sep and key.strip().lower() == name.lower():
            return value.strip()
    return None


def _attribute_or_style(elem: ET.Element, name: str) -> str | None:
    for attr_name, attr_value in elem.attrib.items():
        if _local_name(attr_name).lower() == name.lower():
            return attr_value.strip()
    return _style_value(elem.attrib.get("style", ""), name)


def _rgb_part(value: str) -> int | None:
    value = value.strip()
    try:
        if value.endswith("%"):
            numeric = round(float(value[:-1]) * 2.55)
        else:
            numeric = round(float(value))
    except ValueError:
        return None
    return max(0, min(255, numeric))


def _normalize_color(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip().strip("\"'")
    lowered = raw.lower()
    if lowered in IGNORED_COLOR_VALUES or lowered.startswith("url("):
        return None
    if lowered == "currentcolor":
        return None
    if lowered in NAMED_COLORS:
        return NAMED_COLORS[lowered]

    hex_match = re.fullmatch(r"#([0-9A-Fa-f]{3,8})", raw)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) in {3, 4}:
            expanded = "".join(char * 2 for char in digits)
            if len(digits) == 4 and expanded[6:8].upper() == "00":
                return None
            return f"#{expanded[:6].upper()}"
        if len(digits) == 8 and digits[6:8].upper() == "00":
            return None
        return f"#{digits[:6].upper()}"

    rgb_match = re.fullmatch(r"rgba?\(([^)]+)\)", lowered)
    if rgb_match:
        parts = [part.strip() for part in rgb_match.group(1).split(",")]
        if len(parts) not in {3, 4}:
            return None
        if len(parts) == 4:
            try:
                if float(parts[3]) <= 0:
                    return None
            except ValueError:
                return None
        channels = [_rgb_part(part) for part in parts[:3]]
        if any(channel is None for channel in channels):
            return None
        r, g, b = (int(channel) for channel in channels)
        return f"#{r:02X}{g:02X}{b:02X}"

    return None


def _rgb_tuple(color: str) -> tuple[int, int, int]:
    return (
        int(color[1:3], 16),
        int(color[3:5], 16),
        int(color[5:7], 16),
    )


def _color_luminance(color: str) -> float:
    r, g, b = (channel / 255 for channel in _rgb_tuple(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _color_saturation(color: str) -> float:
    r, g, b = (channel / 255 for channel in _rgb_tuple(color))
    maximum = max(r, g, b)
    minimum = min(r, g, b)
    return 0.0 if maximum == 0 else (maximum - minimum) / maximum


def _is_neutral_color(color: str) -> bool:
    return _color_saturation(color) < 0.12


def _element_area(elem: ET.Element) -> float:
    tag = _local_name(elem.tag)
    if tag in {"rect", "image"}:
        width = _parse_optional_number(elem.attrib.get("width")) or 0.0
        height = _parse_optional_number(elem.attrib.get("height")) or 0.0
        return max(0.0, width * height)
    if tag == "circle":
        radius = _parse_optional_number(elem.attrib.get("r")) or 0.0
        return max(0.0, 3.14159 * radius * radius)
    if tag == "ellipse":
        rx = _parse_optional_number(elem.attrib.get("rx")) or 0.0
        ry = _parse_optional_number(elem.attrib.get("ry")) or 0.0
        return max(0.0, 3.14159 * rx * ry)
    if tag in {"text", "tspan"}:
        font_size = _font_size(elem)
        return max(0.0, font_size * font_size * max(1, len(_text_content(elem))) * 0.55)
    return 0.0


def _transform_translate(elem: ET.Element) -> tuple[float, float]:
    transform = elem.attrib.get("transform", "")
    match = re.search(
        r"translate\(\s*([-+]?\d+(?:\.\d+)?)(?:[\s,]+([-+]?\d+(?:\.\d+)?))?",
        transform,
    )
    if not match:
        return 0.0, 0.0
    x = float(match.group(1))
    y = float(match.group(2) or 0)
    return x, y


def _element_bbox(elem: ET.Element) -> tuple[float, float, float, float] | None:
    explicit = elem.attrib.get("data-ppt-workspace-bbox")
    if explicit:
        return _parse_bbox(explicit)

    attrs = elem.attrib
    if all(name in attrs for name in ("x", "y", "width", "height")):
        x = _parse_number(attrs["x"])
        y = _parse_number(attrs["y"])
        width = _parse_number(attrs["width"])
        height = _parse_number(attrs["height"])
        if width <= 0 or height <= 0:
            raise TemplateError("workspace width and height must be positive")
        return x, y, width, height
    return None


def _bbox_inside(
    candidate: tuple[float, float, float, float],
    view_box: tuple[float, float, float, float],
) -> bool:
    x, y, width, height = candidate
    vx, vy, vw, vh = view_box
    return (
        width > 0
        and height > 0
        and x >= vx
        and y >= vy
        and x + width <= vx + vw
        and y + height <= vy + vh
    )


def _text_content(elem: ET.Element) -> str:
    return "".join(elem.itertext())


def _font_size(elem: ET.Element) -> float:
    direct = _parse_optional_number(elem.attrib.get("font-size"))
    if direct:
        return direct
    styled = _parse_optional_number(_style_value(elem.attrib.get("style", ""), "font-size"))
    return styled or 24.0


def _text_anchor(elem: ET.Element) -> str:
    direct = elem.attrib.get("text-anchor")
    if direct:
        return direct.strip()
    styled = _style_value(elem.attrib.get("style", ""), "text-anchor")
    return styled.strip() if styled else "start"


def _text_xy(elem: ET.Element) -> tuple[float | None, float | None]:
    tx, ty = _transform_translate(elem)
    x = _parse_optional_number(elem.attrib.get("x"))
    y = _parse_optional_number(elem.attrib.get("y"))
    if x is None or y is None:
        for child in elem:
            if _local_name(child.tag) != "tspan":
                continue
            if x is None:
                x = _parse_optional_number(child.attrib.get("x"))
            if y is None:
                y = _parse_optional_number(child.attrib.get("y"))
            if x is not None and y is not None:
                break
    return (x + tx if x is not None else None, y + ty if y is not None else None)


def _collect_placeholder_fits(
    root: ET.Element,
    placeholders: dict[str, int],
    view_box: tuple[float, float, float, float],
) -> dict[str, dict[str, Any]]:
    fits: dict[str, dict[str, Any]] = {}
    vx, _vy, vw, _vh = view_box
    for elem in root.iter():
        if _local_name(elem.tag) != "text":
            continue
        content = _text_content(elem)
        names = {match.group(1) for match in PLACEHOLDER_RE.finditer(content)}
        if not names:
            continue
        x, _y = _text_xy(elem)
        font_size = _font_size(elem)
        anchor = _text_anchor(elem)
        if x is None:
            available_width = vw * 0.8
        elif anchor == "middle":
            available_width = 2 * min(max(0.0, x - vx), max(0.0, vx + vw - x))
        elif anchor == "end":
            available_width = max(0.0, x - vx)
        else:
            available_width = max(0.0, vx + vw - x)
        available_width = max(font_size * 4, available_width * 0.92)
        text_fit = {
            "estimated_width": _format_float(available_width),
            "font_size": _format_float(font_size),
            "max_cjk_chars": max(2, int(available_width / font_size)),
            "max_latin_chars": max(4, int(available_width / (font_size * 0.55))),
            "source": "estimated",
        }
        for name in names:
            if name not in placeholders:
                continue
            previous = fits.get(name)
            if previous is None or text_fit["max_cjk_chars"] < previous["max_cjk_chars"]:
                fits[name] = text_fit
    return fits


def _infer_title_bottom(
    root: ET.Element,
    view_box: tuple[float, float, float, float],
) -> float | None:
    _vx, vy, _vw, vh = view_box
    candidates: list[float] = []
    for elem in root.iter():
        if _local_name(elem.tag) != "text":
            continue
        content = _text_content(elem)
        x, y = _text_xy(elem)
        if y is None:
            continue
        font_size = _font_size(elem)
        is_title = bool(re.search(r"\{\{(?:Page)?Title\}\}", content, re.IGNORECASE))
        if is_title or y <= vy + vh * 0.24:
            candidates.append(y + font_size * 0.65)
    return max(candidates) if candidates else None


def _infer_content_workspace(
    root: ET.Element,
    svg_file: Path,
    view_box: tuple[float, float, float, float],
) -> Workspace:
    vx, vy, vw, vh = view_box
    labelled_candidates: list[tuple[float, tuple[float, float, float, float], str]] = []
    for elem in root.iter():
        label_parts = []
        for attr_name, attr_value in elem.attrib.items():
            if _local_name(attr_name) in {"id", "class", "aria-label", "data-name"}:
                label_parts.append(attr_value)
        label = " ".join(label_parts).lower()
        if not any(token in label for token in ("workspace", "content", "body", "main")):
            continue
        bbox = _element_bbox(elem)
        if bbox and _bbox_inside(bbox, view_box):
            area = bbox[2] * bbox[3]
            labelled_candidates.append((area, bbox, _local_name(elem.tag)))
    if labelled_candidates:
        _area, bbox, element = max(labelled_candidates, key=lambda item: item[0])
        return Workspace("main", bbox, element, source="auto-labelled")

    title_bottom = _infer_title_bottom(root, view_box)
    margin_x = vw * 0.075
    bottom_margin = vh * 0.075
    top = max(vy + vh * 0.2, (title_bottom or vy) + vh * 0.05)
    bottom = vy + vh - bottom_margin
    if bottom - top < vh * 0.35:
        top = vy + vh * 0.22
    bbox = (vx + margin_x, top, vw - 2 * margin_x, bottom - top)
    if bbox[2] <= 0 or bbox[3] <= 0:
        raise TemplateError(f"{svg_file.name}: failed to infer a usable content workspace")
    return Workspace("main", bbox, "auto", source="auto-heuristic")


def _infer_role(stem: str) -> str:
    return STANDARD_PAGE_ROLES.get(stem.lower(), "content")


def _find_workspaces(root: ET.Element, svg_file: Path) -> list[Workspace]:
    workspaces: list[Workspace] = []
    for elem in root.iter():
        workspace_id = elem.attrib.get("data-ppt-workspace")
        if not workspace_id:
            continue
        try:
            bbox = _element_bbox(elem)
        except TemplateError as exc:
            raise TemplateError(f"{svg_file.name}: workspace {workspace_id!r}: {exc}") from exc
        if bbox is None:
            raise TemplateError(
                f"{svg_file.name}: workspace {workspace_id!r} has no geometry. "
                "Remove the marker to use automatic content inference, or add "
                "x/y/width/height / data-ppt-workspace-bbox=\"x y width height\"."
            )
        workspaces.append(
            Workspace(
                workspace_id=workspace_id,
                bbox=bbox,
                element=_local_name(elem.tag),
            )
        )
    return workspaces


def _href_value(elem: ET.Element) -> str:
    return (
        elem.attrib.get("href")
        or elem.attrib.get("{http://www.w3.org/1999/xlink}href")
        or ""
    )


def _collect_local_assets(root: ET.Element, svg_file: Path) -> tuple[list[Path], int]:
    assets: set[Path] = set()
    embedded_count = 0
    for elem in root.iter():
        href = _href_value(elem).strip()
        if not href:
            continue
        if href.startswith("data:"):
            embedded_count += 1
            continue
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith("#"):
            continue
        asset = (svg_file.parent / href).resolve()
        if asset.suffix.lower() in LOCAL_ASSET_EXTS and asset.exists() and asset.is_file():
            assets.add(asset)
    return sorted(assets), embedded_count


def _record_color_use(
    uses: dict[str, dict[str, float]],
    *,
    color: str,
    attr: str,
    elem: ET.Element,
) -> None:
    usage = uses.setdefault(
        color,
        {
            "count": 0,
            "text_count": 0,
            "fill_count": 0,
            "stroke_count": 0,
            "stop_count": 0,
            "area_score": 0.0,
        },
    )
    tag = _local_name(elem.tag)
    area = _element_area(elem)
    usage["count"] += 1
    if tag in {"text", "tspan"}:
        usage["text_count"] += 1
    if attr == "fill":
        usage["fill_count"] += 1
        usage["area_score"] += area
    elif attr == "stroke":
        usage["stroke_count"] += 1
        usage["area_score"] += area * 0.15
    elif attr in {"stop-color", "flood-color"}:
        usage["stop_count"] += 1


def _collect_color_uses(llm_xml_dir: Path) -> dict[str, dict[str, float]]:
    uses: dict[str, dict[str, float]] = {}
    for xml_file in sorted(llm_xml_dir.glob("*.xml")):
        root = ET.fromstring(xml_file.read_text(encoding="utf-8"))
        for elem in root.iter():
            for attr in COLOR_ATTRS:
                value = _attribute_or_style(elem, attr)
                if value and value.strip().lower() == "currentcolor":
                    value = _attribute_or_style(elem, "color")
                color = _normalize_color(value)
                if color is None:
                    continue
                _record_color_use(uses, color=color, attr=attr, elem=elem)
    return uses


def _ranked_colors(
    colors: list[str],
    uses: dict[str, dict[str, float]],
    *,
    prefer_accent: bool = False,
) -> list[str]:
    def score(color: str) -> tuple[float, float, float, float]:
        usage = uses[color]
        saturation = _color_saturation(color)
        area = usage["area_score"]
        if prefer_accent:
            return (
                saturation,
                usage["fill_count"] + usage["stop_count"] * 0.6,
                min(area / 100000.0, 12.0),
                usage["count"],
            )
        return (
            area,
            usage["fill_count"],
            usage["count"],
            _color_luminance(color),
        )

    return sorted(colors, key=score, reverse=True)


def _first_color(candidates: list[str], fallback: str) -> str:
    return candidates[0] if candidates else fallback


def _infer_template_colors(llm_xml_dir: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    uses = _collect_color_uses(llm_xml_dir)
    if not uses:
        colors = {
            "bg": "#FFFFFF",
            "secondary_bg": "#FFFFFF",
            "primary": "#111111",
            "accent": "#111111",
            "secondary_accent": "#111111",
            "text": "#111111",
            "text_secondary": "#111111",
            "border": "#111111",
        }
        return colors, []

    all_colors = list(uses)
    fill_colors = [color for color in all_colors if uses[color]["fill_count"] > 0]
    text_colors = [color for color in all_colors if uses[color]["text_count"] > 0]
    stroke_colors = [color for color in all_colors if uses[color]["stroke_count"] > 0]
    bg = _first_color(_ranked_colors(fill_colors, uses), "#FFFFFF")

    ranked_text = _ranked_colors(text_colors, uses)
    text = _first_color([color for color in ranked_text if color != bg], "#111111")
    if text == "#111111" and bg != "#111111":
        existing_neutrals = [
            color for color in all_colors
            if color != bg and _is_neutral_color(color)
        ]
        if _color_luminance(bg) >= 0.5:
            contrast_side = lambda color: _color_luminance(color) < 0.45
        else:
            contrast_side = lambda color: _color_luminance(color) >= 0.55
        text = _first_color([color for color in existing_neutrals if contrast_side(color)], text)

    text_secondary = _first_color(
        [color for color in ranked_text if color not in {bg, text}],
        text,
    )

    accent_pool = [
        color for color in all_colors
        if color not in {bg, text, text_secondary} and not _is_neutral_color(color)
    ]
    ranked_accents = _ranked_colors(accent_pool, uses, prefer_accent=True)
    primary = _first_color(ranked_accents, _first_color([c for c in all_colors if c != bg], text))
    accent = _first_color([c for c in ranked_accents if c != primary], primary)
    secondary_accent = _first_color(
        [c for c in ranked_accents if c not in {primary, accent}],
        accent,
    )

    secondary_bg = _first_color(
        [
            color for color in _ranked_colors(fill_colors, uses)
            if color not in {bg, text, primary, accent}
        ],
        bg,
    )
    border = _first_color(
        [color for color in _ranked_colors(stroke_colors, uses) if color != bg],
        secondary_bg,
    )

    observations = [
        {
            "hex": color,
            "count": int(uses[color]["count"]),
            "fill_count": int(uses[color]["fill_count"]),
            "stroke_count": int(uses[color]["stroke_count"]),
            "text_count": int(uses[color]["text_count"]),
        }
        for color in _ranked_colors(all_colors, uses)[:12]
    ]
    return {
        "bg": bg,
        "secondary_bg": secondary_bg,
        "primary": primary,
        "accent": accent,
        "secondary_accent": secondary_accent,
        "text": text,
        "text_secondary": text_secondary,
        "border": border,
    }, observations


def _walk_font_runs(
    elem: ET.Element,
    *,
    inherited_family: str | None,
    inherited_size: float | None,
    runs: list[dict[str, Any]],
) -> None:
    family = _attribute_or_style(elem, "font-family") or inherited_family
    size_raw = _attribute_or_style(elem, "font-size")
    size = _parse_optional_number(size_raw) if size_raw else inherited_size
    tag = _local_name(elem.tag)
    if tag == "text":
        content = _text_content(elem).strip()
        if content and (family or size):
            runs.append(
                {
                    "family": family or DEFAULT_FONT_FAMILY,
                    "size": size or 24.0,
                    "content": content,
                }
            )
    for child in elem:
        _walk_font_runs(
            child,
            inherited_family=family,
            inherited_size=size,
            runs=runs,
        )


def _collect_font_runs(llm_xml_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for xml_file in sorted(llm_xml_dir.glob("*.xml")):
        root = ET.fromstring(xml_file.read_text(encoding="utf-8"))
        _walk_font_runs(
            root,
            inherited_family=None,
            inherited_size=None,
            runs=runs,
        )
    return runs


def _clamp_int(value: float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(round(value))))


def _font_family_for_run(runs: list[dict[str, Any]], pattern: str) -> str | None:
    matches = [
        run for run in runs
        if re.search(pattern, str(run["content"]), re.IGNORECASE)
    ]
    if not matches:
        return None
    return max(matches, key=lambda run: float(run["size"]))["family"]


def _font_size_for_run(runs: list[dict[str, Any]], pattern: str) -> float | None:
    matches = [
        float(run["size"]) for run in runs
        if re.search(pattern, str(run["content"]), re.IGNORECASE)
    ]
    return max(matches) if matches else None


def _infer_template_typography(
    llm_xml_dir: Path,
) -> tuple[dict[str, str | int], list[dict[str, Any]]]:
    runs = _collect_font_runs(llm_xml_dir)
    if not runs:
        return {
            "font_family": DEFAULT_FONT_FAMILY,
            "title_family": DEFAULT_FONT_FAMILY,
            "body_family": DEFAULT_FONT_FAMILY,
            "emphasis_family": DEFAULT_FONT_FAMILY,
            "code_family": DEFAULT_CODE_FAMILY,
            "body": 22,
            "title": 34,
            "subtitle": 26,
            "annotation": 15,
        }, []

    family_counter: Counter[str] = Counter()
    size_counter: Counter[int] = Counter()
    for run in runs:
        family_counter[str(run["family"])] += max(1, len(str(run["content"])))
        size_counter[int(round(float(run["size"])))] += 1

    body_family = family_counter.most_common(1)[0][0]
    title_family = (
        _font_family_for_run(runs, r"\{\{(?:PPTTitle|PageTitle|SectionTitle)\}\}")
        or max(runs, key=lambda run: float(run["size"]))["family"]
        or body_family
    )
    page_title_size = _font_size_for_run(runs, r"\{\{(?:PageTitle|SectionTitle)\}\}")
    cover_title_size = _font_size_for_run(runs, r"\{\{PPTTitle\}\}")
    max_size = max(float(run["size"]) for run in runs)
    min_size = min(float(run["size"]) for run in runs)
    title_size = int(round(page_title_size or max_size))
    body_size = _clamp_int(title_size / 1.5, 16, 28)
    if min_size < body_size and min_size >= 14:
        annotation_size = int(round(min_size))
    else:
        annotation_size = _clamp_int(body_size * 0.72, 10, body_size)
    subtitle_size = _clamp_int(body_size * 1.25, body_size + 2, max(title_size, body_size + 2))

    typography: dict[str, str | int] = {
        "font_family": body_family,
        "title_family": str(title_family),
        "body_family": body_family,
        "emphasis_family": str(title_family),
        "code_family": DEFAULT_CODE_FAMILY,
        "body": body_size,
        "title": title_size,
        "subtitle": subtitle_size,
        "annotation": annotation_size,
    }
    if cover_title_size and int(round(cover_title_size)) != title_size:
        typography["cover_title"] = int(round(cover_title_size))

    observations = [
        {
            "family": family,
            "weighted_count": count,
            "sizes": [
                size for size, _size_count in size_counter.most_common()
                if any(
                    str(run["family"]) == family
                    and int(round(float(run["size"]))) == size
                    for run in runs
                )
            ][:6],
        }
        for family, count in family_counter.most_common(8)
    ]
    return typography, observations


def _infer_template_style_lock(llm_xml_dir: Path) -> dict[str, Any]:
    colors, color_observations = _infer_template_colors(llm_xml_dir)
    typography, font_observations = _infer_template_typography(llm_xml_dir)
    return {
        "source": "llm_xml",
        "colors": colors,
        "typography": typography,
        "observed_colors": color_observations,
        "observed_fonts": font_observations,
    }


def _read_svg_summary(svg_file: Path) -> SvgSummary:
    text = svg_file.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise TemplateError(f"{svg_file.name}: invalid XML: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise TemplateError(f"{svg_file.name}: root element must be <svg>")
    view_box = root.attrib.get("viewBox", "").strip()
    normalized_text = text
    if not view_box:
        view_box = _infer_root_view_box(root, svg_file)
        normalized_text = _inject_root_view_box(text, view_box)

    placeholders: dict[str, int] = {}
    for match in PLACEHOLDER_RE.finditer(text):
        placeholders[match.group(1)] = placeholders.get(match.group(1), 0) + 1

    role = _infer_role(svg_file.stem)
    view_box_tuple = _parse_bbox(view_box)
    placeholder_fits = _collect_placeholder_fits(root, placeholders, view_box_tuple)
    workspaces = _find_workspaces(root, svg_file)
    if role == "content" and not workspaces:
        workspaces = [_infer_content_workspace(root, svg_file, view_box_tuple)]
    if role != "content" and workspaces:
        raise TemplateError(
            f"{svg_file.name}: only content.svg may declare workspaces. "
            "For title/toc/chapter/ending pages, expose editable text through {{...}} placeholders only."
        )

    local_assets, embedded_count = _collect_local_assets(root, svg_file)
    digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return SvgSummary(
        source=svg_file,
        file_name=svg_file.name,
        stem=svg_file.stem,
        role=role,
        view_box=view_box,
        sha256=digest,
        svg_text=normalized_text,
        placeholders=placeholders,
        placeholder_fits=placeholder_fits,
        workspaces=workspaces,
        local_assets=local_assets,
        embedded_image_count=embedded_count,
    )


def _scan_svg_dir(svg_dir: Path) -> list[SvgSummary]:
    if not svg_dir.is_dir():
        raise TemplateError(f"SVG directory not found: {svg_dir}")
    svg_files = {path.name.lower(): path for path in svg_dir.glob("*.svg") if path.is_file()}
    if not svg_files:
        raise TemplateError(f"No .svg files found in {svg_dir}")
    missing = [name for name in REQUIRED_TEMPLATE_FILES if name not in svg_files]
    extra = sorted(name for name in svg_files if name not in REQUIRED_TEMPLATE_FILES)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"extra: {', '.join(extra)}")
        raise TemplateError(
            "Template SVG directory must contain exactly five top-level SVG files: "
            f"{', '.join(REQUIRED_TEMPLATE_FILES)} ({'; '.join(details)})."
        )
    ordered_files = [svg_files[name] for name in REQUIRED_TEMPLATE_FILES]
    return [_read_svg_summary(path) for path in ordered_files]


def _contract_page(summary: SvgSummary) -> dict[str, Any]:
    return {
        "stem": summary.stem,
        "file": summary.file_name,
        "role": summary.role,
        "viewBox": summary.view_box,
        "sha256": summary.sha256,
        "placeholders": [
            {
                "name": name,
                "token": f"{{{{{name}}}}}",
                "count": count,
                **(
                    {"text_fit": summary.placeholder_fits[name]}
                    if name in summary.placeholder_fits
                    else {}
                ),
            }
            for name, count in sorted(summary.placeholders.items())
        ],
        "workspaces": [
            {
                "id": workspace.workspace_id,
                "bbox": [_format_float(part) for part in workspace.bbox],
                "element": workspace.element,
                "source": workspace.source,
            }
            for workspace in summary.workspaces
        ],
    }


def build_contract(
    template_id: str,
    summaries: list[SvgSummary],
    *,
    canvas_format: str,
    style_lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the compact template contract from SVG summaries."""
    view_boxes = {summary.view_box for summary in summaries}
    if len(view_boxes) != 1:
        raise TemplateError(
            "All SVG pages in one locked template must use the same viewBox. "
            f"Found: {', '.join(sorted(view_boxes))}"
        )
    contract = {
        "schema_version": 1,
        "engine": "locked_svg",
        "template_id": template_id,
        "canvas_format": canvas_format,
        "pages": [_contract_page(summary) for summary in summaries],
    }
    if style_lock:
        contract["style_lock"] = style_lock
    return contract


def _render_style_lock(style_lock: dict[str, Any]) -> list[str]:
    colors = style_lock.get("colors") or {}
    typography = style_lock.get("typography") or {}
    observed_colors = style_lock.get("observed_colors") or []
    observed_fonts = style_lock.get("observed_fonts") or []

    color_rows = [
        "| Lock Key | Value | Runtime Usage |",
        "|---|---|---|",
    ]
    color_notes = {
        "bg": "Page background / implicit canvas",
        "secondary_bg": "Cards, bands, low-emphasis panels",
        "primary": "Template brand color; titles, icons, section marks",
        "accent": "Data highlights and high-emphasis callouts",
        "secondary_accent": "Secondary emphasis and gradient companion",
        "text": "Main text",
        "text_secondary": "Captions, labels, annotations",
        "border": "Dividers and outlines",
    }
    for key, note in color_notes.items():
        if key in colors:
            color_rows.append(f"| `{key}` | `{colors[key]}` | {note} |")

    type_rows = [
        "| Lock Key | Value |",
        "|---|---|",
    ]
    for key in (
        "font_family",
        "title_family",
        "body_family",
        "emphasis_family",
        "code_family",
        "body",
        "title",
        "cover_title",
        "subtitle",
        "annotation",
    ):
        if key in typography:
            value = typography[key]
            display = f"`{value}`" if isinstance(value, str) else f"`{value}px`"
            type_rows.append(f"| `{key}` | {display} |")

    observed_color_rows = [
        "| HEX | Uses | Fill | Stroke | Text |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in observed_colors:
        observed_color_rows.append(
            f"| `{item['hex']}` | {item['count']} | {item['fill_count']} | "
            f"{item['stroke_count']} | {item['text_count']} |"
        )

    observed_font_rows = [
        "| Font Family | Weighted Uses | Observed Sizes |",
        "|---|---:|---|",
    ]
    for item in observed_fonts:
        sizes = ", ".join(f"`{size}px`" for size in item.get("sizes", [])) or "None"
        observed_font_rows.append(
            f"| `{item['family']}` | {item['weighted_count']} | {sizes} |"
        )

    return [
        "## III. Template Style Lock",
        "",
        "**Hard rule**: Downstream PPT generation MUST copy these colors and "
        "typography values into the project `design_spec.md` and `spec_lock.md`. "
        "Do not replace them during the Eight Confirmations unless the user "
        "explicitly asks to override the locked template style.",
        "",
        "- Source: `llm_xml/*.xml` generated at template creation time",
        "- Runtime scope: generated workspace content, charts, icons, and free-design "
        "pages in the same deck",
        "",
        "### Colors",
        "",
        *color_rows,
        "",
        "### Typography",
        "",
        *type_rows,
        "",
        "### Extraction Evidence",
        "",
        "Observed palette:",
        "",
        *observed_color_rows,
        "",
        "Observed fonts:",
        "",
        *observed_font_rows,
        "",
    ]


def _render_design_spec(
    *,
    template_id: str,
    canvas_format: str,
    pages: list[SvgSummary],
    style_lock: dict[str, Any],
) -> str:
    placeholders = {
        page.stem: [f"{{{{{name}}}}}" for name in sorted(page.placeholders)]
        for page in pages
    }
    frontmatter = {
        "template_id": template_id,
        "canvas_format": canvas_format,
        "template_engine": "locked_svg",
        "template_contract": "template_contract.json",
        "placeholder_style": "custom",
        "style_lock": True,
        "style_lock_source": "llm_xml",
        "primary_color": style_lock.get("colors", {}).get("primary", ""),
        "placeholders": placeholders,
    }
    fm_lines = ["---"]
    for key, value in frontmatter.items():
        if isinstance(value, list):
            fm_lines.append(f"{key}: [{', '.join(value)}]")
        elif isinstance(value, dict):
            fm_lines.append(f"{key}:")
            for page_stem, values in value.items():
                encoded = ", ".join(json.dumps(v, ensure_ascii=False) for v in values)
                fm_lines.append(f"  {page_stem}: [{encoded}]")
        else:
            fm_lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    fm_lines.append("---")

    roster = [
        "| File | Role | Placeholders | Workspaces |",
        "|---|---|---|---|",
    ]
    for page in pages:
        page_placeholders = ", ".join(
            f"`{{{{{name}}}}}`" for name in sorted(page.placeholders)
        ) or "None"
        workspace_desc = ", ".join(
            f"`{workspace.workspace_id}` {workspace.bbox[2]:g}x{workspace.bbox[3]:g}"
            for workspace in page.workspaces
        ) or "None"
        roster.append(
            f"| `{page.file_name}` | {page.role} | {page_placeholders} | {workspace_desc} |"
        )

    return "\n".join(
        [
            *fm_lines,
            "",
            f"# {template_id} - Locked SVG Template",
            "",
            "## I. Runtime Contract",
            "",
            "- Contract file: `template_contract.json`",
            "- Template engine: `locked_svg`",
            "- Runtime fill command: `svg_template.py apply <template_dir> <page_stem> --data <fill.json> -o <out.svg>`",
            "- Runtime agents read `template_contract.json`, not template SVG source.",
            "",
            "## II. Page Roster",
            "",
            *roster,
            "",
            *_render_style_lock(style_lock),
        ]
    )


def _copy_referenced_assets(summaries: list[SvgSummary], output_dir: Path) -> None:
    for summary in summaries:
        for asset in summary.local_assets:
            try:
                rel = asset.relative_to(summary.source.parent)
            except ValueError:
                rel = Path(asset.name)
            target = output_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if asset.resolve() != target.resolve():
                shutil.copy2(asset, target)


def _register_template(template_id: str) -> None:
    register_script = SCRIPT_DIR / "register_template.py"
    result = subprocess.run(
        [sys.executable, str(register_script), template_id],
        cwd=SKILL_DIR.parent.parent,
        text=True,
    )
    if result.returncode != 0:
        raise TemplateError(f"register_template.py failed for {template_id}")


def cmd_inspect(args: argparse.Namespace) -> int:
    summaries = _scan_svg_dir(args.svg_dir.resolve())
    print(f"SVG files: {len(summaries)}")
    for summary in summaries:
        placeholders = ", ".join(
            f"{{{{{name}}}}} x{count}" for name, count in sorted(summary.placeholders.items())
        ) or "none"
        workspaces = ", ".join(
            f"{workspace.workspace_id}={workspace.bbox[0]:g},{workspace.bbox[1]:g},"
            f"{workspace.bbox[2]:g},{workspace.bbox[3]:g} ({workspace.source})"
            for workspace in summary.workspaces
        ) or "none"
        print(
            f"- {summary.file_name}: role={summary.role}; viewBox={summary.view_box}; "
            f"placeholders={placeholders}; workspaces={workspaces}; "
            f"embedded_images={summary.embedded_image_count}; local_assets={len(summary.local_assets)}"
        )
    if args.llm_xml_dir:
        written = write_llm_xml_dir(args.svg_dir.resolve(), args.llm_xml_dir.resolve())
        print(f"LLM XML files: {len(written)} -> {args.llm_xml_dir}")
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    summaries = _scan_svg_dir(args.svg_dir.resolve())
    output_root = args.output_dir.resolve() if args.output_dir else LAYOUTS_DIR
    template_dir = output_root / args.template_id
    if template_dir.exists():
        if not args.force:
            raise TemplateError(
                f"Template directory already exists: {template_dir}. Use --force to replace it."
            )
        shutil.rmtree(template_dir)
    template_dir.mkdir(parents=True, exist_ok=True)

    for summary in summaries:
        svg_path = template_dir / summary.file_name
        svg_path.write_text(summary.svg_text, encoding="utf-8")
        summary.sha256 = hashlib.sha256(svg_path.read_bytes()).hexdigest()
    _copy_referenced_assets(summaries, template_dir)
    llm_xml_dir = template_dir / "llm_xml"
    write_llm_xml_dir(template_dir, llm_xml_dir)
    style_lock = _infer_template_style_lock(llm_xml_dir)

    contract = build_contract(
        args.template_id,
        summaries,
        canvas_format=args.canvas_format,
        style_lock=style_lock,
    )
    (template_dir / "template_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    design_spec = _render_design_spec(
        template_id=args.template_id,
        canvas_format=args.canvas_format,
        pages=summaries,
        style_lock=style_lock,
    )
    (template_dir / "design_spec.md").write_text(design_spec, encoding="utf-8")

    if not args.no_register and output_root == LAYOUTS_DIR:
        _register_template(args.template_id)
    else:
        print(f"Created locked SVG template: {template_dir}")
        print("Registration skipped.")
    return 0


def _load_contract(template_dir: Path) -> dict[str, Any]:
    contract_path = template_dir / "template_contract.json"
    if not contract_path.exists():
        raise TemplateError(
            f"Missing template_contract.json in {template_dir}. "
            "Rebuild this template with the SVG-only create-template workflow."
        )
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("engine") != "locked_svg":
        raise TemplateError(f"Unsupported template contract: {contract_path}")
    return data


def _find_page(contract: dict[str, Any], page_stem: str) -> dict[str, Any]:
    for page in contract.get("pages", []):
        if page.get("stem") == page_stem:
            return page
    raise TemplateError(f"Page stem {page_stem!r} not found in template_contract.json")


def _svg_num(value: Any) -> str:
    return str(_format_float(float(value)))


def _workspace_overlay(workspace: dict[str, Any], index: int, stroke_width: float) -> str:
    bbox = workspace.get("bbox")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise TemplateError(f"invalid workspace bbox for {workspace.get('id') or index!r}")
    x, y, width, height = (float(part) for part in bbox)
    workspace_id = str(workspace.get("id") or f"workspace-{index}")
    label = (
        f"{workspace_id}: "
        f"{_svg_num(x)}, {_svg_num(y)}, {_svg_num(width)}x{_svg_num(height)}"
    )
    label_x = x + 10
    label_y = y + 26
    label_width = max(260, min(width - 20, 10 * len(label))) if width > 40 else 260
    return "\n".join(
        [
            f'<rect id="workspace-{html.escape(_safe_xml_id(workspace_id))}" '
            f'x="{_svg_num(x)}" y="{_svg_num(y)}" '
            f'width="{_svg_num(width)}" height="{_svg_num(height)}" '
            'fill="#f97316" fill-opacity="0.14" stroke="#f97316" '
            f'stroke-width="{_svg_num(stroke_width)}" stroke-dasharray="14 8" '
            'vector-effect="non-scaling-stroke"/>',
            f'<rect x="{_svg_num(label_x - 6)}" y="{_svg_num(label_y - 20)}" '
            f'width="{_svg_num(label_width)}" height="26" rx="4" '
            'fill="#fff7ed" fill-opacity="0.92" stroke="#f97316" '
            'vector-effect="non-scaling-stroke"/>',
            f'<text x="{_svg_num(label_x)}" y="{_svg_num(label_y)}" '
            'font-family="Arial, Microsoft YaHei, sans-serif" font-size="18" '
            f'fill="#9a3412">{html.escape(label)}</text>',
        ]
    )


def _render_content_viewbox_debug(
    *,
    template_dir: Path,
    content_page: dict[str, Any],
    output_path: Path,
) -> None:
    content_svg = template_dir / str(content_page.get("file") or "content.svg")
    if not content_svg.exists():
        raise TemplateError(f"content template SVG missing: {content_svg}")
    view_box = str(content_page.get("viewBox") or "").strip()
    if not view_box:
        raise TemplateError("content page missing viewBox in template_contract.json")
    view_x, view_y, view_width, view_height = _parse_bbox(view_box)
    stroke_width = max(view_width, view_height) / 320
    svg_payload = base64.b64encode(content_svg.read_bytes()).decode("ascii")
    background = f"data:image/svg+xml;base64,{svg_payload}"
    overlays = [
        _workspace_overlay(workspace, index, stroke_width)
        for index, workspace in enumerate(content_page.get("workspaces") or [], start=1)
    ]
    if not overlays:
        overlays.append(
            '<text x="24" y="64" font-family="Arial, Microsoft YaHei, sans-serif" '
            'font-size="22" fill="#b45309">No content workspaces declared</text>'
        )
    debug_svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="{html.escape(view_box)}" '
            f'width="{_svg_num(view_width)}" height="{_svg_num(view_height)}">',
            "  <desc>Debug overlay for content.svg viewBox and locked template workspaces.</desc>",
            f'  <image x="{_svg_num(view_x)}" y="{_svg_num(view_y)}" '
            f'width="{_svg_num(view_width)}" height="{_svg_num(view_height)}" '
            f'opacity="0.58" preserveAspectRatio="none" xlink:href="{background}"/>',
            f'  <rect id="content-viewbox" x="{_svg_num(view_x)}" y="{_svg_num(view_y)}" '
            f'width="{_svg_num(view_width)}" height="{_svg_num(view_height)}" '
            'fill="none" stroke="#2563eb" '
            f'stroke-width="{_svg_num(stroke_width)}" vector-effect="non-scaling-stroke"/>',
            '  <g id="content-workspace-overlays">',
            "    " + "\n    ".join(overlays),
            "  </g>",
            "</svg>",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(debug_svg, encoding="utf-8")


def cmd_visualize_content(args: argparse.Namespace) -> int:
    template_dir = args.template_dir.resolve()
    contract = _load_contract(template_dir)
    content_page = _find_page(contract, "content")
    output_path = args.output.resolve() if args.output else template_dir / "debug" / "content_viewbox.svg"
    _render_content_viewbox_debug(
        template_dir=template_dir,
        content_page=content_page,
        output_path=output_path,
    )
    print(f"Wrote content viewBox debug SVG: {output_path}")
    return 0


def _normalize_placeholder_key(key: str) -> str:
    key = key.strip()
    match = PLACEHOLDER_RE.fullmatch(key)
    return match.group(1) if match else key


def _load_fill_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TemplateError("fill data must be a JSON object")
    placeholders = data.get("placeholders", {})
    workspaces = data.get("workspaces", {})
    if not isinstance(placeholders, dict) or not isinstance(workspaces, dict):
        raise TemplateError("fill data must contain object fields: placeholders, workspaces")
    return data


def _replace_placeholders(text: str, values: dict[str, Any], *, strict: bool) -> str:
    normalized = {
        _normalize_placeholder_key(str(key)): html.escape(str(value), quote=False)
        for key, value in values.items()
    }
    missing: set[str] = set()

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in normalized:
            return normalized[name]
        missing.add(name)
        return match.group(0)

    result = PLACEHOLDER_RE.sub(_sub, text)
    if strict and missing:
        raise TemplateError(f"missing placeholder values: {', '.join(sorted(missing))}")
    return result


def _weighted_text_units(value: str) -> float:
    units = 0.0
    for char in value:
        if char.isspace():
            units += 0.35
        elif unicodedata.east_asian_width(char) in {"F", "W"}:
            units += 1.0
        else:
            units += 0.55
    return units


def _check_placeholder_fit(
    page: dict[str, Any],
    values: dict[str, Any],
    *,
    enabled: bool,
) -> None:
    if not enabled:
        return
    fit_by_name = {}
    for placeholder in page.get("placeholders", []):
        if isinstance(placeholder, dict) and isinstance(placeholder.get("text_fit"), dict):
            fit_by_name[str(placeholder.get("name") or "")] = placeholder["text_fit"]
    if not fit_by_name:
        return
    normalized = {
        _normalize_placeholder_key(str(key)): str(value)
        for key, value in values.items()
    }
    too_long = []
    for name, value in normalized.items():
        fit = fit_by_name.get(name)
        if not fit:
            continue
        max_units = float(fit.get("max_cjk_chars") or 0)
        if max_units <= 0:
            continue
        used_units = _weighted_text_units(value)
        if used_units > max_units:
            too_long.append(
                f"{name} uses {used_units:.1f} width units, limit {max_units:g} "
                f"(max_cjk_chars={fit.get('max_cjk_chars')}, "
                f"max_latin_chars={fit.get('max_latin_chars')})"
            )
    if too_long:
        raise TemplateError(
            "placeholder text is likely to overflow its locked template box: "
            + "; ".join(too_long)
            + ". Shorten the value or rebuild the template with a larger placeholder area."
        )


def _fragment_inner_svg(fragment_path: Path) -> tuple[str, tuple[float, float, float, float]]:
    text = fragment_path.read_text(encoding="utf-8").strip()
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise TemplateError(f"{fragment_path.name}: invalid fragment SVG: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise TemplateError(f"{fragment_path.name}: fragment root must be <svg>")
    view_box = root.attrib.get("viewBox", "").strip()
    if not view_box:
        raise TemplateError(f"{fragment_path.name}: fragment root missing viewBox")
    bbox = _parse_bbox(view_box)
    start = text.find(">")
    end = text.lower().rfind("</svg>")
    if start == -1 or end == -1 or end <= start:
        raise TemplateError(f"{fragment_path.name}: cannot extract fragment body")
    return text[start + 1:end].strip(), bbox


def _workspace_by_id(page: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    for workspace in page.get("workspaces", []):
        if workspace.get("id") == workspace_id:
            return workspace
    raise TemplateError(
        f"Workspace {workspace_id!r} is not declared for page {page.get('stem')!r}"
    )


def _append_workspace_fragments(
    svg_text: str,
    page: dict[str, Any],
    workspace_values: dict[str, Any],
    *,
    base_dir: Path,
) -> str:
    additions: list[str] = []
    for workspace_id, raw_path in workspace_values.items():
        workspace = _workspace_by_id(page, str(workspace_id))
        x, y, width, height = (float(part) for part in workspace["bbox"])
        fragment_path = Path(str(raw_path))
        if not fragment_path.is_absolute():
            fragment_path = (base_dir / fragment_path).resolve()
        if not fragment_path.exists():
            raise TemplateError(f"workspace fragment not found: {fragment_path}")
        inner, frag_box = _fragment_inner_svg(fragment_path)
        _fx, _fy, frag_width, frag_height = frag_box
        sx = width / frag_width
        sy = height / frag_height
        additions.append(
            "\n".join(
                [
                    f'<g id="workspace-fill-{html.escape(_safe_xml_id(str(workspace_id)))}" '
                    f'data-ppt-workspace-fill="{html.escape(str(workspace_id))}" '
                    f'transform="translate({_format_float(x)} {_format_float(y)}) '
                    f'scale({_format_float(sx)} {_format_float(sy)})">',
                    inner,
                    "</g>",
                ]
            )
        )

    if not additions:
        return svg_text
    match = SVG_CLOSE_RE.search(svg_text)
    if not match:
        raise TemplateError("template SVG is missing closing </svg>")
    insertion = "\n" + "\n".join(additions) + "\n"
    return svg_text[:match.start()] + insertion + svg_text[match.start():]


def cmd_apply(args: argparse.Namespace) -> int:
    template_dir = args.template_dir.resolve()
    contract = _load_contract(template_dir)
    page = _find_page(contract, args.page_stem)
    template_svg = template_dir / page["file"]
    if not template_svg.exists():
        raise TemplateError(f"template page SVG missing: {template_svg}")
    fill_data = _load_fill_data(args.data.resolve())

    svg_text = template_svg.read_text(encoding="utf-8")
    _check_placeholder_fit(
        page,
        fill_data.get("placeholders", {}),
        enabled=not args.no_fit_check,
    )
    svg_text = _replace_placeholders(
        svg_text,
        fill_data.get("placeholders", {}),
        strict=args.strict,
    )
    svg_text = _append_workspace_fragments(
        svg_text,
        page,
        fill_data.get("workspaces", {}),
        base_dir=args.data.resolve().parent,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg_text, encoding="utf-8")
    print(f"Wrote filled SVG: {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and apply locked SVG templates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Scan SVG files and print a compact, base64-safe summary.",
    )
    inspect_parser.add_argument("svg_dir", type=Path)
    inspect_parser.add_argument(
        "--llm-xml-dir",
        type=Path,
        help="Optional output directory for sanitized LLM-friendly XML copies.",
    )
    inspect_parser.set_defaults(func=cmd_inspect)

    create_parser = subparsers.add_parser(
        "create",
        help="Create a locked SVG template from a directory of SVG files.",
    )
    create_parser.add_argument("svg_dir", type=Path)
    create_parser.add_argument("template_id")
    create_parser.add_argument("--canvas-format", default="ppt169")
    create_parser.add_argument("--output-dir", type=Path)
    create_parser.add_argument("--force", action="store_true")
    create_parser.add_argument("--no-register", action="store_true")
    create_parser.set_defaults(func=cmd_create)

    visualize_parser = subparsers.add_parser(
        "visualize-content",
        help="Write debug/content_viewbox.svg with the content viewBox and workspace overlay.",
    )
    visualize_parser.add_argument("template_dir", type=Path)
    visualize_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output SVG path. Defaults to <template_dir>/debug/content_viewbox.svg.",
    )
    visualize_parser.set_defaults(func=cmd_visualize_content)

    apply_parser = subparsers.add_parser(
        "apply",
        help="Fill one locked SVG page from JSON placeholder/workspace data.",
    )
    apply_parser.add_argument("template_dir", type=Path)
    apply_parser.add_argument("page_stem")
    apply_parser.add_argument("--data", required=True, type=Path)
    apply_parser.add_argument("-o", "--output", required=True, type=Path)
    apply_parser.add_argument("--strict", action="store_true")
    apply_parser.add_argument(
        "--no-fit-check",
        action="store_true",
        help="Disable estimated placeholder length checks.",
    )
    apply_parser.set_defaults(func=cmd_apply)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TemplateError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
