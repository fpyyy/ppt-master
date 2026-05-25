#!/usr/bin/env python3
"""
PPT Master - LayoutSpec v2 Compiler

Compile LayoutSpec v2 (semantic slide spec) into deterministic geometry and SVG.

Usage:
    .\\.venv\\Scripts\\python.exe scripts/layout_compile.py <project_path>

Examples:
    .\\.venv\\Scripts\\python.exe scripts/layout_compile.py projects/demo
    .\\.venv\\Scripts\\python.exe scripts/layout_compile.py projects/demo --input layout_v2.json

Dependencies:
    None (only uses standard library and PPT Master sibling modules)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from svg_to_pptx.drawingml_utils import estimate_text_width  # noqa: E402


CANVAS_W = 1920.0
CANVAS_H = 1080.0
ALLOWED_SLIDE_TYPES = {
    "cover",
    "toc",
    "section",
    "single_content",
    "two_column",
    "image_with_caption",
    "comparison_table",
    "timeline",
    "hub_spoke",
    "card_grid",
    "pipeline",
    "icon_text_list",
}
COORDINATE_KEYS = {"x", "y", "w", "h", "left", "right", "top", "bottom", "cx", "cy"}


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


def _default_tokens() -> dict[str, Any]:
    return {
        "slide": {
            "width": CANVAS_W,
            "height": CANVAS_H,
            "margin_left": 120.0,
            "margin_right": 120.0,
            "margin_top": 80.0,
            "margin_bottom": 80.0,
        },
        "font": {
            "title": 56.0,
            "subtitle": 36.0,
            "body": 30.0,
            "caption": 22.0,
            "min_body": 22.0,
        },
        "spacing": {
            "xs": 8.0,
            "s": 16.0,
            "m": 24.0,
            "l": 40.0,
            "xl": 64.0,
        },
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("layout_v2 spec must be a JSON object")
    return payload


def _deny_coordinates(value: Any, context: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in COORDINATE_KEYS:
                raise ValueError(f"LayoutSpec v2 forbids coordinate key '{key}' at {context}")
            _deny_coordinates(child, f"{context}.{key}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _deny_coordinates(child, f"{context}[{idx}]")


def _require_fields(slide: dict[str, Any], index: int) -> None:
    for name in ("slide_type", "content", "constraints", "capacity", "overflow_policy"):
        if name not in slide:
            raise ValueError(f"slide #{index + 1} missing required field '{name}'")
    if slide["slide_type"] not in ALLOWED_SLIDE_TYPES:
        raise ValueError(f"slide #{index + 1} has unsupported slide_type '{slide['slide_type']}'")


def _wrap_text(text: str, font_size: float, max_width: float, weight: str = "normal") -> list[str]:
    if not text.strip():
        return []
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for token in words[1:]:
        trial = f"{current} {token}"
        if estimate_text_width(trial, font_size, weight) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = token
    lines.append(current)
    return lines


def _fit_text(
    text: str,
    box: Box,
    *,
    base_size: float,
    min_size: float,
    max_lines: int,
    weight: str = "normal",
) -> dict[str, Any]:
    for font_size in [base_size - i for i in range(max(0, int(base_size - min_size) + 1))]:
        lines = _wrap_text(text, font_size, box.w, weight)
        line_h = font_size * 1.28
        if lines and len(lines) <= max_lines and len(lines) * line_h <= box.h:
            return {"lines": lines, "font_size": font_size, "state": "ok"}
    lines = _wrap_text(text, min_size, box.w, weight)
    line_h = min_size * 1.18
    if lines and len(lines) <= max_lines and len(lines) * line_h <= box.h:
        return {"lines": lines, "font_size": min_size, "state": "tighten_line_gap"}
    return {"lines": lines[:max_lines], "font_size": min_size, "state": "fail"}


def _content_box(tokens: dict[str, Any]) -> Box:
    slide = tokens["slide"]
    return Box(
        slide["margin_left"],
        slide["margin_top"],
        slide["width"] - slide["margin_left"] - slide["margin_right"],
        slide["height"] - slide["margin_top"] - slide["margin_bottom"],
    )


def _text_el(el_id: str, box: Box, fit: dict[str, Any], *, fill: str = "#0F172A", anchor: str = "start") -> dict[str, Any]:
    return {"id": el_id, "kind": "text", "box": box.__dict__, "fit": fit, "fill": fill, "anchor": anchor}


def _rect_el(el_id: str, box: Box, *, fill: str = "none", stroke: str = "#CBD5E1", rx: float = 0.0) -> dict[str, Any]:
    return {"id": el_id, "kind": "rect", "box": box.__dict__, "fill": fill, "stroke": stroke, "rx": rx}


def _build_slide(slide: dict[str, Any], idx: int, tokens: dict[str, Any]) -> dict[str, Any]:
    content = slide["content"]
    cbox = _content_box(tokens)
    fonts = tokens["font"]
    spacing = tokens["spacing"]
    elements: list[dict[str, Any]] = []
    issues: list[str] = []
    sid = slide.get("id") or f"P{idx + 1:02d}"
    stype = slide["slide_type"]

    title_box = Box(cbox.x, cbox.y, cbox.w, 92.0)
    title = str(content.get("title", ""))
    title_fit = _fit_text(title, title_box, base_size=fonts["title"], min_size=fonts["subtitle"], max_lines=2, weight="bold")
    elements.append(_text_el(f"{sid}.title", title_box, title_fit))
    if title_fit["state"] == "fail":
        issues.append(f"{sid}.title overflow")

    body_top = title_box.bottom + spacing["m"]
    body_h = cbox.bottom - body_top
    body_box = Box(cbox.x, body_top, cbox.w, body_h)

    if stype in {"cover", "section"}:
        subtitle = str(content.get("subtitle", content.get("summary", "")))
        box = Box(cbox.x, body_top + 120, cbox.w, 220)
        fit = _fit_text(subtitle, box, base_size=fonts["subtitle"], min_size=fonts["body"], max_lines=4)
        elements.append(_text_el(f"{sid}.subtitle", box, fit, fill="#334155"))
    elif stype == "toc":
        items = content.get("items", [])
        if not isinstance(items, list):
            items = []
        max_items = int(slide["capacity"].get("max_items", 6))
        rows = items[:max_items]
        row_h = 72.0
        gap = 16.0
        start_y = body_top
        num_w = 92.0
        text_x = cbox.x + num_w + 28.0
        for i, raw in enumerate(rows):
            label = raw["text"] if isinstance(raw, dict) and "text" in raw else str(raw)
            num = raw.get("number", f"{i+1:02d}") if isinstance(raw, dict) else f"{i+1:02d}"
            ry = start_y + i * (row_h + gap)
            nbox = Box(cbox.x, ry, num_w, row_h)
            tbox = Box(text_x, ry, cbox.w - (text_x - cbox.x), row_h)
            nfit = _fit_text(str(num), nbox, base_size=34.0, min_size=24.0, max_lines=1, weight="bold")
            tfit = _fit_text(str(label), tbox, base_size=fonts["body"], min_size=fonts["min_body"], max_lines=2)
            elements.append(_text_el(f"{sid}.toc.{i}.number", nbox, nfit, fill="#0F172A"))
            elements.append(_text_el(f"{sid}.toc.{i}.text", tbox, tfit, fill="#0F172A"))
            if tfit["state"] == "fail":
                issues.append(f"{sid}.toc.{i}.text overflow")
    elif stype in {"single_content", "icon_text_list"}:
        bullets = content.get("bullets", content.get("items", []))
        if not isinstance(bullets, list):
            bullets = []
        max_items = int(slide["capacity"].get("max_items", 6))
        y = body_top
        for i, item in enumerate(bullets[:max_items]):
            txt = item["text"] if isinstance(item, dict) and "text" in item else str(item)
            row = Box(cbox.x + 18.0, y, cbox.w - 18.0, 76.0)
            fit = _fit_text(txt, row, base_size=fonts["body"], min_size=fonts["min_body"], max_lines=2)
            elements.append(_text_el(f"{sid}.item.{i}", row, fit))
            y += 90.0
    elif stype in {"two_column", "image_with_caption", "comparison_table", "timeline", "hub_spoke", "card_grid", "pipeline"}:
        left = Box(cbox.x, body_top, (cbox.w - spacing["l"]) / 2.0, body_h)
        right = Box(left.right + spacing["l"], body_top, left.w, body_h)
        elements.append(_rect_el(f"{sid}.left.box", left))
        elements.append(_rect_el(f"{sid}.right.box", right))
        ltxt = str(content.get("left_text", content.get("left", "")))
        rtxt = str(content.get("right_text", content.get("right", "")))
        lfit = _fit_text(ltxt, Box(left.x + 20, left.y + 20, left.w - 40, left.h - 40), base_size=fonts["body"], min_size=fonts["min_body"], max_lines=14)
        rfit = _fit_text(rtxt, Box(right.x + 20, right.y + 20, right.w - 40, right.h - 40), base_size=fonts["body"], min_size=fonts["min_body"], max_lines=14)
        elements.append(_text_el(f"{sid}.left.text", Box(left.x + 20, left.y + 20, left.w - 40, left.h - 40), lfit))
        elements.append(_text_el(f"{sid}.right.text", Box(right.x + 20, right.y + 20, right.w - 40, right.h - 40), rfit))
    else:
        raise ValueError(f"unsupported slide_type {stype}")

    return {"id": sid, "slide_type": stype, "elements": elements, "issues": issues, "constraints": slide["constraints"]}


def _intersects(a: Box, b: Box) -> bool:
    return not (a.right <= b.x or b.right <= a.x or a.bottom <= b.y or b.bottom <= a.y)


def _validate(compiled: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for slide in compiled["slides"]:
        text_boxes: list[tuple[str, Box]] = []
        all_boxes: list[tuple[str, Box, str]] = []
        for el in slide["elements"]:
            box = Box(**el["box"])
            all_boxes.append((el["id"], box, el["kind"]))
            if el["kind"] == "text":
                if el["fit"]["state"] == "fail":
                    errs.append(f"{slide['id']}::{el['id']} text-overflow-fail")
                text_boxes.append((el["id"], box))
        for eid, box, _kind in all_boxes:
            if box.x < 0 or box.y < 0 or box.right > CANVAS_W or box.bottom > CANVAS_H:
                errs.append(f"{slide['id']}::{eid} outside-canvas")
        for i in range(len(text_boxes)):
            for j in range(i + 1, len(text_boxes)):
                left = text_boxes[i]
                right = text_boxes[j]
                if _intersects(left[1], right[1]):
                    errs.append(f"{slide['id']}::{left[0]} overlaps {right[0]}")
    return errs


def _render_svg(slide: dict[str, Any], out_path: Path) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">',
        '<rect x="0" y="0" width="1920" height="1080" fill="#FFFFFF"/>',
    ]
    for el in slide["elements"]:
        box = Box(**el["box"])
        if el["kind"] == "rect":
            lines.append(
                f'<rect id="{el["id"]}" x="{box.x:.2f}" y="{box.y:.2f}" width="{box.w:.2f}" height="{box.h:.2f}" '
                f'fill="{el["fill"]}" stroke="{el["stroke"]}" rx="{el["rx"]:.2f}"/>'
            )
            continue
        fit = el["fit"]
        y = box.y + fit["font_size"]
        for line in fit["lines"]:
            safe = (
                line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            lines.append(
                f'<text id="{el["id"]}" x="{box.x:.2f}" y="{y:.2f}" font-size="{fit["font_size"]:.2f}" '
                f'fill="{el["fill"]}" font-family="Microsoft YaHei">{safe}</text>'
            )
            y += fit["font_size"] * 1.28
    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile LayoutSpec v2 to deterministic SVG geometry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory.")
    parser.add_argument("--input", default="layout_v2.json", help="Layout spec filename under project path.")
    parser.add_argument("--strict", action="store_true", help="Fail on any validation issue.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = args.project_path.resolve()
    input_path = project / args.input
    if not input_path.exists():
        print(f"[ERROR] missing layout spec: {input_path}", file=sys.stderr)
        return 1

    payload = _load_json(input_path)
    _deny_coordinates(payload.get("slides", []), "slides")
    slides = payload.get("slides")
    if not isinstance(slides, list) or not slides:
        print("[ERROR] layout_v2.json must contain a non-empty slides array", file=sys.stderr)
        return 1

    tokens = _default_tokens()
    user_tokens = payload.get("design_tokens")
    if isinstance(user_tokens, dict):
        for key, value in user_tokens.items():
            if isinstance(value, dict) and isinstance(tokens.get(key), dict):
                tokens[key].update(value)

    compiled_slides: list[dict[str, Any]] = []
    for idx, slide in enumerate(slides):
        if not isinstance(slide, dict):
            print(f"[ERROR] slide #{idx + 1} must be object", file=sys.stderr)
            return 1
        _require_fields(slide, idx)
        compiled_slides.append(_build_slide(slide, idx, tokens))

    compiled = {"version": "layout_v2_compiled", "tokens": tokens, "slides": compiled_slides}
    errors = _validate(compiled)
    for slide in compiled_slides:
        for msg in slide["issues"]:
            errors.append(msg)

    compiled_path = project / "layout_v2_compiled.json"
    compiled_path.write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")

    svg_dir = project / "svg_output"
    svg_dir.mkdir(parents=True, exist_ok=True)
    for index, slide in enumerate(compiled_slides, start=1):
        out_name = f"{index:02d}_{slide['id'].lower()}_{slide['slide_type']}.svg"
        _render_svg(slide, svg_dir / out_name)

    if errors:
        for msg in errors:
            print(f"[ERROR] {msg}", file=sys.stderr)
        if args.strict:
            print("[FAIL] layout compile validation failed", file=sys.stderr)
            return 2
    print(f"[OK] compiled {len(compiled_slides)} slide(s) -> {compiled_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
