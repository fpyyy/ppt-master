#!/usr/bin/env python3
"""
PPT Master - SVG Layout Structure Checker

Detect structural layout defects that text and SVG syntax checks cannot see:
off-center hub-spoke diagrams, uneven card grids, and malformed timelines.

Usage:
    .\\.venv\\Scripts\\python.exe scripts/svg_layout_checker.py <project_path_or_svg>

Examples:
    .\\.venv\\Scripts\\python.exe scripts/svg_layout_checker.py projects/demo
    .\\.venv\\Scripts\\python.exe scripts/svg_layout_checker.py projects/demo/svg_output/10_slide.svg

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


SVG_NS = "http://www.w3.org/2000/svg"
CENTER_TOLERANCE = 24.0
PAIR_TOLERANCE = 28.0
ALIGN_TOLERANCE = 6.0
SIZE_TOLERANCE = 4.0


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
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class CircleInfo:
    cx: float
    cy: float
    r: float


@dataclass
class LineInfo:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class GroupInfo:
    elem: ET.Element
    group_id: str
    layout: str
    matrix: Matrix


@dataclass
class Issue:
    path: Path
    severity: str
    group_id: str
    message: str


@dataclass
class LayoutElement:
    element_id: str
    kind: str
    box: Box


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _f(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.match(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(value).strip())
    return float(match.group(0)) if match else default


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


def _target_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".svg" else []
    svg_dir = target / "svg_output" if (target / "svg_output").is_dir() else target
    return sorted(svg_dir.glob("*.svg"))


def _layout_name(elem: ET.Element) -> str:
    explicit = elem.get("data-layout") or elem.get("data-ppt-layout") or ""
    if explicit:
        return explicit.strip().lower().replace("-", "_")
    group_id = (elem.get("id") or "").strip().lower().replace("-", "_")
    for known in ("hub_spoke", "card_grid", "icon_grid", "timeline"):
        if known in group_id:
            return known
    return ""


def _find_layout_groups(root: ET.Element) -> list[GroupInfo]:
    groups: list[GroupInfo] = []

    def walk(elem: ET.Element, matrix: Matrix) -> None:
        next_matrix = matrix.multiply(_parse_transform(elem.get("transform")))
        if _local_name(elem.tag) == "g":
            layout = _layout_name(elem)
            if layout:
                groups.append(GroupInfo(
                    elem=elem,
                    group_id=elem.get("id") or layout,
                    layout=layout,
                    matrix=next_matrix,
                ))
        for child in list(elem):
            walk(child, next_matrix)

    walk(root, Matrix())
    return groups


def _rect_box(elem: ET.Element, matrix: Matrix) -> Box:
    x = _f(elem.get("x"))
    y = _f(elem.get("y"))
    w = _f(elem.get("width"))
    h = _f(elem.get("height"))
    p1 = matrix.point(x, y)
    p2 = matrix.point(x + w, y + h)
    return Box(min(p1[0], p2[0]), min(p1[1], p2[1]), abs(p2[0] - p1[0]), abs(p2[1] - p1[1]))


def _circle_info(elem: ET.Element, matrix: Matrix) -> CircleInfo:
    cx, cy = matrix.point(_f(elem.get("cx")), _f(elem.get("cy")))
    sx = math.hypot(matrix.a, matrix.b)
    sy = math.hypot(matrix.c, matrix.d)
    return CircleInfo(cx=cx, cy=cy, r=_f(elem.get("r")) * max(sx, sy))


def _line_info(elem: ET.Element, matrix: Matrix) -> LineInfo:
    x1, y1 = matrix.point(_f(elem.get("x1")), _f(elem.get("y1")))
    x2, y2 = matrix.point(_f(elem.get("x2")), _f(elem.get("y2")))
    return LineInfo(x1=x1, y1=y1, x2=x2, y2=y2)


def _descendant_shapes(group: GroupInfo) -> tuple[list[Box], list[CircleInfo], list[LineInfo]]:
    rects: list[Box] = []
    circles: list[CircleInfo] = []
    lines: list[LineInfo] = []

    def walk(elem: ET.Element, matrix: Matrix) -> None:
        next_matrix = matrix.multiply(_parse_transform(elem.get("transform")))
        tag = _local_name(elem.tag)
        if tag == "rect":
            box = _rect_box(elem, next_matrix)
            if box.w >= 70 and box.h >= 40:
                rects.append(box)
        elif tag == "circle":
            circle = _circle_info(elem, next_matrix)
            if circle.r >= 8:
                circles.append(circle)
        elif tag == "line":
            lines.append(_line_info(elem, next_matrix))
        for child in list(elem):
            walk(child, next_matrix)

    for child in list(group.elem):
        walk(child, group.matrix)
    return rects, circles, lines


def _declared_center(group: GroupInfo) -> tuple[float, float] | None:
    raw = group.elem.get("data-center") or group.elem.get("data-layout-center")
    if not raw:
        return None
    nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw)]
    if len(nums) < 2:
        return None
    return group.matrix.point(nums[0], nums[1])


def _check_hub_spoke(path: Path, group: GroupInfo) -> list[Issue]:
    rects, circles, lines = _descendant_shapes(group)
    issues: list[Issue] = []
    if len(rects) < 4 or not circles:
        issues.append(Issue(path, "error", group.group_id, "hub-spoke requires one hub circle and at least four card rectangles"))
        return issues

    hub = max(circles, key=lambda item: item.r)
    card_center_x = sum(rect.cx for rect in rects) / len(rects)
    card_center_y = sum(rect.cy for rect in rects) / len(rects)
    declared = _declared_center(group)
    expected_x, expected_y = declared if declared else (card_center_x, card_center_y)

    hub_deviation = math.hypot(hub.cx - expected_x, hub.cy - expected_y)
    if hub_deviation > CENTER_TOLERANCE:
        issues.append(Issue(
            path,
            "error",
            group.group_id,
            (
                f"hub center=({hub.cx:.1f},{hub.cy:.1f}) differs from spoke ring center="
                f"({expected_x:.1f},{expected_y:.1f}) by {hub_deviation:.1f}px"
            ),
        ))

    if declared:
        ring_deviation = math.hypot(card_center_x - expected_x, card_center_y - expected_y)
        if ring_deviation > CENTER_TOLERANCE:
            issues.append(Issue(
                path,
                "error",
                group.group_id,
                (
                    f"card ring center=({card_center_x:.1f},{card_center_y:.1f}) differs from "
                    f"declared center=({expected_x:.1f},{expected_y:.1f}) by {ring_deviation:.1f}px"
                ),
            ))

    widths = [rect.w for rect in rects]
    heights = [rect.h for rect in rects]
    if max(widths) - min(widths) > SIZE_TOLERANCE or max(heights) - min(heights) > SIZE_TOLERANCE:
        issues.append(Issue(path, "error", group.group_id, "hub-spoke card rectangles must share one size"))

    if len(lines) and len(lines) < len(rects):
        issues.append(Issue(path, "error", group.group_id, f"hub-spoke has {len(rects)} cards but only {len(lines)} connector lines"))

    opposite_errors = 0
    for rect in rects:
        mirror_x = 2 * expected_x - rect.cx
        mirror_y = 2 * expected_y - rect.cy
        nearest = min(rects, key=lambda other: math.hypot(other.cx - mirror_x, other.cy - mirror_y))
        if math.hypot(nearest.cx - mirror_x, nearest.cy - mirror_y) > PAIR_TOLERANCE:
            opposite_errors += 1
    if opposite_errors > len(rects) // 2:
        issues.append(Issue(path, "error", group.group_id, "hub-spoke cards are not arranged as symmetric opposite pairs"))

    return issues


def _cluster(values: list[float], tolerance: float) -> list[list[float]]:
    clusters: list[list[float]] = []
    for value in sorted(values):
        if not clusters or abs(value - sum(clusters[-1]) / len(clusters[-1])) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return clusters


def _check_card_grid(path: Path, group: GroupInfo) -> list[Issue]:
    rects, _circles, _lines = _descendant_shapes(group)
    if len(rects) < 3:
        return []
    issues: list[Issue] = []
    widths = [rect.w for rect in rects]
    heights = [rect.h for rect in rects]
    if max(widths) - min(widths) > SIZE_TOLERANCE or max(heights) - min(heights) > SIZE_TOLERANCE:
        issues.append(Issue(path, "error", group.group_id, "card grid rectangles must share one size"))

    row_clusters = _cluster([rect.cy for rect in rects], ALIGN_TOLERANCE)
    for row in row_clusters:
        if len(row) >= 2 and max(row) - min(row) > ALIGN_TOLERANCE:
            issues.append(Issue(path, "error", group.group_id, "card grid row centers are not aligned"))
            break
    return issues


def _check_timeline(path: Path, group: GroupInfo) -> list[Issue]:
    rects, circles, _lines = _descendant_shapes(group)
    centers = [(item.cx, item.cy) for item in circles] if len(circles) >= 3 else [(item.cx, item.cy) for item in rects]
    if len(centers) < 3:
        return []
    xs = [point[0] for point in centers]
    ys = [point[1] for point in centers]
    if max(ys) - min(ys) <= ALIGN_TOLERANCE or max(xs) - min(xs) <= ALIGN_TOLERANCE:
        return []
    return [Issue(path, "error", group.group_id, "timeline nodes must align on one horizontal or vertical axis")]


def check_file(path: Path) -> list[Issue]:
    root = ET.parse(path).getroot()
    issues: list[Issue] = []
    for group in _find_layout_groups(root):
        if group.layout == "hub_spoke":
            issues.extend(_check_hub_spoke(path, group))
        elif group.layout in {"card_grid", "icon_grid"}:
            issues.extend(_check_card_grid(path, group))
        elif group.layout == "timeline":
            issues.extend(_check_timeline(path, group))
    return issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect structural layout defects in generated SVGs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", type=Path, help="Project directory, SVG directory, or one SVG file.")
    parser.add_argument(
        "--from-layout",
        action="store_true",
        help="Validate constraints from layout_v2_compiled.json instead of structural SVG groups.",
    )
    return parser


def _intersects(a: Box, b: Box) -> bool:
    return not (a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y)


def _validate_layout_compiled(project_path: Path) -> list[str]:
    compiled_path = project_path / "layout_v2_compiled.json"
    if not compiled_path.exists():
        return [f"missing compiled layout file: {compiled_path}"]
    payload = json.loads(compiled_path.read_text(encoding="utf-8"))
    issues: list[str] = []
    for slide in payload.get("slides", []):
        sid = slide.get("id", "unknown")
        elements: list[LayoutElement] = []
        for raw in slide.get("elements", []):
            box = raw.get("box") or {}
            try:
                parsed = Box(float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"]))
            except (KeyError, TypeError, ValueError):
                issues.append(f"{sid}::{raw.get('id', 'unknown')} invalid-bbox")
                continue
            elements.append(LayoutElement(raw.get("id", "unknown"), raw.get("kind", "unknown"), parsed))
        for i in range(len(elements)):
            left = elements[i]
            if left.box.x < 0 or left.box.y < 0 or left.box.w <= 0 or left.box.h <= 0:
                issues.append(f"{sid}::{left.element_id} invalid-geometry")
            for j in range(i + 1, len(elements)):
                right = elements[j]
                if left.kind == "rect" and right.kind == "rect":
                    continue
                if _intersects(left.box, right.box):
                    issues.append(f"{sid}::{left.element_id} overlaps {right.element_id}")

        for constraint in slide.get("constraints", []):
            if not isinstance(constraint, dict):
                continue
            ctype = constraint.get("type")
            targets = constraint.get("targets", [])
            if ctype == "equal_left" and isinstance(targets, list) and len(targets) >= 2:
                left_values = []
                for target in targets:
                    matched = next((item for item in elements if item.element_id == target), None)
                    if matched:
                        left_values.append(matched.box.x)
                if left_values and (max(left_values) - min(left_values) > ALIGN_TOLERANCE):
                    issues.append(f"{sid}::constraint equal_left violated")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.from_layout:
        target = args.target.resolve()
        project = target if target.is_dir() else target.parent
        issues = _validate_layout_compiled(project)
        if issues:
            for msg in issues:
                print(f"[ERROR] {msg}", file=sys.stderr)
            print("[FAIL] deterministic layout checker failed", file=sys.stderr)
            return 2
        print("[OK] deterministic layout checker passed", file=sys.stderr)
        return 0
    files = _target_files(args.target.resolve())
    if not files:
        print(f"[ERROR] no SVG files found under {args.target}", file=sys.stderr)
        return 1

    total = 0
    for path in files:
        try:
            issues = check_file(path)
        except ET.ParseError as exc:
            print(f"[ERROR] {path}: invalid SVG: {exc}", file=sys.stderr)
            return 1
        total += len(issues)
        for issue in issues:
            print(f"[{issue.severity.upper()}] {path.name}::{issue.group_id}: {issue.message}", file=sys.stderr)

    if total:
        print(f"[FAIL] {total} structural layout issue(s) found. Re-layout before export.", file=sys.stderr)
        return 2
    print("[OK] layout structure gate passed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
