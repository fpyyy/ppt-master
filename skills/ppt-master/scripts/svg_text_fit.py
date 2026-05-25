#!/usr/bin/env python3
"""
PPT Master - SVG Text Fit Gate

Detect and optionally fix SVG text that exceeds its containing rectangle or
canvas. The fixer wraps single-line space-separated text without changing
font-size; unresolved cases are reported for Executor re-layout.

Usage:
    .\\.venv\\Scripts\\python.exe scripts/svg_text_fit.py <project_path_or_svg> [--fix]

Examples:
    .\\.venv\\Scripts\\python.exe scripts/svg_text_fit.py projects/demo
    .\\.venv\\Scripts\\python.exe scripts/svg_text_fit.py projects/demo --fix
    .\\.venv\\Scripts\\python.exe scripts/svg_text_fit.py projects/demo/svg_output/02_toc.svg --fix

Dependencies:
    None (only uses standard library and PPT Master sibling modules)
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from svg_to_pptx.drawingml_utils import estimate_text_width  # noqa: E402


ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

SVG_NS = "http://www.w3.org/2000/svg"
TOLERANCE = 2.0
DEFAULT_PADDING = 4.0
LINE_GAP_RATIO = 1.28


@dataclass
class Matrix:
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    def multiply(self, other: "Matrix") -> "Matrix":
        return Matrix(
            a=self.a * other.a + self.c * other.b,
            b=self.b * other.a + self.d * other.b,
            c=self.a * other.c + self.c * other.d,
            d=self.b * other.c + self.d * other.d,
            e=self.a * other.e + self.c * other.f + self.e,
            f=self.b * other.e + self.d * other.f + self.f,
        )

    def point(self, x: float, y: float) -> tuple[float, float]:
        return (
            self.a * x + self.c * y + self.e,
            self.b * x + self.d * y + self.f,
        )


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def area(self) -> float:
        return max(0.0, self.w) * max(0.0, self.h)

    def contains_point(self, x: float, y: float, *, pad: float = 0.0) -> bool:
        return self.x - pad <= x <= self.right + pad and self.y - pad <= y <= self.bottom + pad

    def overflow(self, other: "Box") -> tuple[float, float, float, float]:
        return (
            max(0.0, other.x - self.x),
            max(0.0, other.y - self.y),
            max(0.0, self.right - other.right),
            max(0.0, self.bottom - other.bottom),
        )


@dataclass
class TextInfo:
    elem: ET.Element
    parent: ET.Element | None
    matrix: Matrix
    bbox: Box
    anchor_x: float
    anchor_y: float
    text: str
    font_size: float
    font_weight: str
    text_anchor: str
    line_count: int


@dataclass
class RectInfo:
    elem: ET.Element
    parent: ET.Element | None
    bbox: Box
    group_id: str


@dataclass
class Issue:
    path: Path
    text: TextInfo
    container: Box
    kind: str
    message: str


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _f(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.match(r"[-+]?\d*\.?\d+", str(value).strip())
    return float(match.group(0)) if match else default


def _style_value(style: str | None, name: str) -> str | None:
    if not style:
        return None
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if key.strip() == name:
            return value.strip()
    return None


def _attr(elem: ET.Element, name: str, default: str | None = None) -> str | None:
    return elem.get(name) or _style_value(elem.get("style"), name) or default


def _parse_transform(value: str | None) -> Matrix:
    if not value:
        return Matrix()
    matrix = Matrix()
    for name, raw_args in re.findall(r"([a-zA-Z]+)\(([^)]*)\)", value):
        args = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw_args)]
        if name == "translate" and args:
            op = Matrix(e=args[0], f=args[1] if len(args) > 1 else 0.0)
        elif name == "scale" and args:
            sx = args[0]
            sy = args[1] if len(args) > 1 else sx
            op = Matrix(a=sx, d=sy)
        elif name == "matrix" and len(args) >= 6:
            op = Matrix(*args[:6])
        else:
            continue
        matrix = matrix.multiply(op)
    return matrix


def _parse_view_box(root: ET.Element) -> Box:
    raw = root.get("viewBox", "")
    nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", raw)]
    if len(nums) == 4:
        return Box(nums[0], nums[1], nums[2], nums[3])
    return Box(0.0, 0.0, _f(root.get("width"), 1280.0), _f(root.get("height"), 720.0))


def _text_content(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()


def _line_infos(elem: ET.Element, font_size: float, font_weight: str) -> list[tuple[float, float, str, float]]:
    base_x = _f(elem.get("x"), 0.0)
    base_y = _f(elem.get("y"), 0.0)

    lines: list[tuple[float, float, str, float]] = []
    direct = (elem.text or "").strip()
    if direct:
        lines.append((base_x, base_y, html.unescape(direct), estimate_text_width(direct, font_size, font_weight)))

    current_x = base_x
    current_y = base_y
    for child in elem:
        if _local_name(child.tag) != "tspan":
            continue
        if child.get("x") is not None:
            current_x = _f(child.get("x"), current_x)
        if child.get("y") is not None:
            current_y = _f(child.get("y"), current_y)
        if child.get("dy") is not None:
            current_y += _f(child.get("dy"), 0.0)
        text = _text_content(child)
        if text:
            child_size = _f(_attr(child, "font-size"), font_size)
            child_weight = _attr(child, "font-weight", font_weight) or font_weight
            lines.append((
                current_x,
                current_y,
                html.unescape(text),
                estimate_text_width(text, child_size, child_weight),
            ))
    if not lines:
        text = _text_content(elem)
        if text:
            lines.append((base_x, base_y, html.unescape(text), estimate_text_width(text, font_size, font_weight)))
    return lines


def _text_info(elem: ET.Element, parent: ET.Element | None, matrix: Matrix) -> TextInfo | None:
    text = _text_content(elem)
    if not text:
        return None
    font_size = _f(_attr(elem, "font-size"), 16.0)
    font_weight = _attr(elem, "font-weight", "400") or "400"
    text_anchor = _attr(elem, "text-anchor", "start") or "start"
    local_lines = _line_infos(elem, font_size, font_weight)
    if not local_lines:
        return None

    boxes = []
    for x, y, _line, width in local_lines:
        if text_anchor == "middle":
            left = x - width / 2
        elif text_anchor == "end":
            left = x - width
        else:
            left = x
        right = left + width
        top = y - font_size * 0.85
        bottom = y + font_size * 0.35
        x1, y1 = matrix.point(left, top)
        x2, y2 = matrix.point(right, bottom)
        boxes.append(Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)))

    left = min(box.x for box in boxes)
    top = min(box.y for box in boxes)
    right = max(box.right for box in boxes)
    bottom = max(box.bottom for box in boxes)
    anchor_x, anchor_y = matrix.point(local_lines[0][0], local_lines[0][1])
    return TextInfo(
        elem=elem,
        parent=parent,
        matrix=matrix,
        bbox=Box(left, top, right - left, bottom - top),
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        text=text,
        font_size=font_size,
        font_weight=font_weight,
        text_anchor=text_anchor,
        line_count=len(local_lines),
    )


def _rect_info(elem: ET.Element, parent: ET.Element | None, matrix: Matrix, group_id: str) -> RectInfo | None:
    if elem.get("data-ppt-workspace"):
        return None
    x = _f(elem.get("x"), 0.0)
    y = _f(elem.get("y"), 0.0)
    w = _f(elem.get("width"), 0.0)
    h = _f(elem.get("height"), 0.0)
    if w <= 0 or h <= 0:
        return None
    x1, y1 = matrix.point(x, y)
    x2, y2 = matrix.point(x + w, y + h)
    return RectInfo(
        elem=elem,
        parent=parent,
        bbox=Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)),
        group_id=group_id,
    )


def _collect(root: ET.Element) -> tuple[list[TextInfo], list[RectInfo]]:
    texts: list[TextInfo] = []
    rects: list[RectInfo] = []

    def walk(elem: ET.Element, parent: ET.Element | None, matrix: Matrix, group_id: str) -> None:
        next_matrix = matrix.multiply(_parse_transform(elem.get("transform")))
        next_group = elem.get("id") if _local_name(elem.tag) == "g" and elem.get("id") else group_id
        tag = _local_name(elem.tag)
        if tag == "text":
            info = _text_info(elem, parent, next_matrix)
            if info:
                texts.append(info)
        elif tag == "rect":
            info = _rect_info(elem, parent, next_matrix, next_group)
            if info:
                rects.append(info)
        for child in list(elem):
            walk(child, elem, next_matrix, next_group)

    walk(root, None, Matrix(), "")
    return texts, rects


def _container_for_text(text: TextInfo, rects: list[RectInfo], canvas: Box) -> tuple[Box, RectInfo | None]:
    candidates = [
        rect for rect in rects
        if rect.bbox.contains_point(text.anchor_x, text.anchor_y, pad=8.0)
        and rect.bbox.w > text.font_size * 3
        and rect.bbox.h > text.font_size * 1.2
    ]
    if not candidates:
        return canvas, None
    rect = min(candidates, key=lambda item: item.bbox.area)
    return rect.bbox, rect


def _is_cjk_like(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff" or "\u3040" <= char <= "\u30ff" or "\uac00" <= char <= "\ud7af"


def _wrap_units(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    if any(char.isspace() for char in stripped):
        return stripped.split()
    if all(_is_cjk_like(char) for char in stripped):
        return list(stripped)
    return [stripped]


def _wrap_text(text: str, font_size: float, font_weight: str, max_width: float) -> list[str]:
    units = _wrap_units(text)
    if not units:
        return []
    lines: list[str] = []
    current = units[0]
    cjk_mode = len(units) > 1 and all(_is_cjk_like(unit) for unit in units)
    for unit in units[1:]:
        sep = "" if cjk_mode else " "
        trial = current + sep + unit
        if estimate_text_width(trial, font_size, font_weight) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = unit
    lines.append(current)
    return lines


def _can_rewrite_text(text: TextInfo) -> bool:
    if text.text_anchor != "start" or not text.text.strip():
        return False
    for child in text.elem:
        if _local_name(child.tag) != "tspan":
            return False
        disallowed = set(child.attrib) - {"x", "y", "dx", "dy"}
        if disallowed:
            return False
    return True


def _has_broken_latin_word(elem: ET.Element) -> bool:
    lines = [
        _text_content(child).strip()
        for child in elem
        if _local_name(child.tag) == "tspan" and _text_content(child).strip()
    ]
    for left, right in zip(lines, lines[1:]):
        if not (left[-1:].isalpha() and right[:1].isalpha()):
            continue
        if len(left) <= 3 or len(right) <= 3:
            return True
    return False


def _rewrite_as_tspans(text: TextInfo, lines: list[str]) -> None:
    elem = text.elem
    x = elem.get("x")
    y = elem.get("y")
    if x is None or y is None:
        match = re.search(r"translate\(\s*([-+]?\d*\.?\d+)[,\s]+([-+]?\d*\.?\d+)", elem.get("transform", ""))
        if match:
            elem.attrib.pop("transform", None)
            x = match.group(1)
            y = match.group(2)
            elem.set("x", x)
            elem.set("y", y)
    x = x or "0"
    elem.text = "\n"
    for child in list(elem):
        elem.remove(child)
    gap = max(1, int(round(text.font_size * LINE_GAP_RATIO)))
    for idx, line in enumerate(lines):
        tspan = ET.Element(f"{{{SVG_NS}}}tspan")
        tspan.set("x", x)
        tspan.set("dy", "0" if idx == 0 else str(gap))
        tspan.text = line
        elem.append(tspan)
        tspan.tail = "\n"


def _try_fix_issue(issue: Issue, rect: RectInfo | None) -> bool:
    text = issue.text
    if not _can_rewrite_text(text):
        return False
    local_x = _f(text.elem.get("x"), 0.0)
    if local_x == 0.0:
        match = re.search(r"translate\(\s*([-+]?\d*\.?\d+)", text.elem.get("transform", ""))
        if match:
            local_x = float(match.group(1))
    container = issue.container
    available = max(0.0, container.right - text.anchor_x - DEFAULT_PADDING)
    if available < text.font_size * 4:
        return False
    normalized_text = " ".join(text.text.split())
    lines = _wrap_text(normalized_text, text.font_size, text.font_weight, available)
    if len(lines) <= 1:
        return False
    needed_bottom = text.anchor_y + (len(lines) - 1) * text.font_size * LINE_GAP_RATIO + text.font_size * 0.35
    if needed_bottom > container.bottom - DEFAULT_PADDING:
        return False
    _rewrite_as_tspans(text, lines)
    return local_x >= 0


def _issues_for_tree(path: Path, root: ET.Element) -> list[Issue]:
    texts, rects = _collect(root)
    canvas = _parse_view_box(root)
    issues: list[Issue] = []
    for text in texts:
        # Page numbers and one/two-digit badges are allowed to sit in tiny shapes.
        if re.fullmatch(r"\d{1,3}|\d+(?:\.\d+)?%", text.text.strip()):
            continue
        if _has_broken_latin_word(text.elem):
            issues.append(Issue(
                path=path,
                text=text,
                container=text.bbox,
                kind="broken-latin-word",
                message=f"text '{text.text[:64]}' appears to split a Latin word across tspans",
            ))
            continue
        container, _rect = _container_for_text(text, rects, canvas)
        overflow = text.bbox.overflow(container)
        if any(value > TOLERANCE for value in overflow):
            issues.append(Issue(
                path=path,
                text=text,
                container=container,
                kind="text-overflow",
                message=(
                    f"text '{text.text[:64]}' bbox=({text.bbox.x:.1f},{text.bbox.y:.1f},"
                    f"{text.bbox.w:.1f},{text.bbox.h:.1f}) exceeds container="
                    f"({container.x:.1f},{container.y:.1f},{container.w:.1f},{container.h:.1f})"
                ),
            ))
    return issues


def _target_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".svg" else []
    svg_dir = target / "svg_output" if (target / "svg_output").is_dir() else target
    return sorted(svg_dir.glob("*.svg"))


def check_file(path: Path, *, fix: bool = False) -> tuple[list[Issue], int]:
    tree = ET.parse(path)
    root = tree.getroot()
    issues = _issues_for_tree(path, root)
    fixed = 0
    if fix and issues:
        _, rects = _collect(root)
        for issue in issues:
            _container, rect = _container_for_text(issue.text, rects, _parse_view_box(root))
            if _try_fix_issue(issue, rect):
                fixed += 1
        if fixed:
            tree.write(path, encoding="utf-8", xml_declaration=True)
            tree = ET.parse(path)
            root = tree.getroot()
            issues = _issues_for_tree(path, root)
    return issues, fixed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect SVG text overflow against containers without changing font size.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", type=Path, help="Project directory, SVG directory, or one SVG file.")
    parser.add_argument("--fix", action="store_true", help="Wrap simple overflowing single-line text in-place.")
    parser.add_argument(
        "--from-layout",
        action="store_true",
        help="Validate text-fit results from layout_v2_compiled.json instead of scanning SVGs.",
    )
    return parser


def _validate_from_layout(project_path: Path) -> int:
    compiled_path = project_path / "layout_v2_compiled.json"
    if not compiled_path.exists():
        print(f"[ERROR] missing compiled layout file: {compiled_path}", file=sys.stderr)
        return 1
    payload = json.loads(compiled_path.read_text(encoding="utf-8"))
    unresolved: list[str] = []
    for slide in payload.get("slides", []):
        slide_id = slide.get("id", "unknown")
        for element in slide.get("elements", []):
            if element.get("kind") != "text":
                continue
            fit = element.get("fit", {})
            if fit.get("state") == "fail":
                unresolved.append(f"{slide_id}::{element.get('id', 'unknown')}")
    if unresolved:
        for item in unresolved:
            print(f"[OVERFLOW] {item}: unresolved in deterministic layout", file=sys.stderr)
        print("[FAIL] deterministic layout text-fit gate failed", file=sys.stderr)
        return 2
    print("[OK] deterministic layout text-fit gate passed", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    target = args.target.resolve()
    if args.from_layout:
        project = target if target.is_dir() else target.parent
        return _validate_from_layout(project)
    files = _target_files(target)
    if not files:
        print(f"Error: no SVG files found for {target}", file=sys.stderr)
        return 1

    total_issues = 0
    total_fixed = 0
    for path in files:
        try:
            issues, fixed = check_file(path, fix=args.fix)
        except ET.ParseError as exc:
            print(f"[ERROR] {path}: invalid SVG: {exc}", file=sys.stderr)
            return 1
        total_fixed += fixed
        total_issues += len(issues)
        if fixed:
            print(f"[FIXED] {path}: wrapped {fixed} text element(s)", file=sys.stderr)
        for issue in issues:
            print(f"[OVERFLOW] {issue.path.name}: {issue.message}", file=sys.stderr)

    if total_issues:
        print(
            f"[FAIL] {total_issues} text overflow issue(s) remain. "
            "Do not reduce font-size; wrap, expand containers, shorten wording, or re-layout.",
            file=sys.stderr,
        )
        return 2
    print(f"[OK] text fit gate passed; fixed {total_fixed} element(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
