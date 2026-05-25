#!/usr/bin/env python3
"""
PPT Master - LayoutSpec v2 Migration Helper

Create a baseline LayoutSpec v2 from an existing project (legacy SVG-first flow).

Usage:
    .\\.venv\\Scripts\\python.exe scripts/migrate_layout_v2.py <project_path>

Examples:
    .\\.venv\\Scripts\\python.exe scripts/migrate_layout_v2.py projects/demo

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _extract_texts(svg_path: Path) -> list[str]:
    root = ET.parse(svg_path).getroot()
    values: list[str] = []
    for elem in root.iter():
        if elem.tag.rsplit("}", 1)[-1] != "text":
            continue
        text = "".join(elem.itertext()).strip()
        text = re.sub(r"\s+", " ", text)
        if text:
            values.append(text)
    return values


def _to_slide(svg_path: Path, index: int) -> dict[str, Any]:
    texts = _extract_texts(svg_path)
    title = texts[0] if texts else f"Slide {index + 1}"
    bullets = texts[1:7] if len(texts) > 1 else []
    slide_type = "toc" if any("目录" in t or "contents" in t.lower() for t in texts[:2]) else "single_content"
    content: dict[str, Any] = {"title": title}
    if slide_type == "toc":
        content["items"] = [{"number": f"{i+1:02d}", "text": item} for i, item in enumerate(bullets)]
    else:
        content["bullets"] = bullets
    return {
        "id": f"P{index+1:02d}",
        "slide_type": slide_type,
        "content": content,
        "constraints": [],
        "capacity": {"max_items": 6},
        "overflow_policy": {
            "mode": "shrink_or_split",
            "min_font_size": 22,
            "max_lines": 8
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate legacy project SVGs to layout_v2.json")
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--output", default="layout_v2.json", help="Output file name under project path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = args.project_path.resolve()
    svg_dir = project / "svg_output"
    files = sorted(svg_dir.glob("*.svg"))
    if not files:
        print(f"[ERROR] no SVG files found under {svg_dir}")
        return 1
    payload = {"slides": [_to_slide(path, idx) for idx, path in enumerate(files)]}
    output = project / args.output
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
