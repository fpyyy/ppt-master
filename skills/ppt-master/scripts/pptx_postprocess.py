#!/usr/bin/env python3
"""
PPT Master - PPTX Post-processing Tool

Apply small DrawingML-level fixes after SVG pages have been exported to PPTX.
Currently this vertically centers numeric-only text boxes, which is needed for
template circle/badge numbering because PowerPoint otherwise keeps text box
content top-aligned.

Usage:
    .\\.venv\\Scripts\\python.exe scripts/pptx_postprocess.py <project_path_or_pptx>

Examples:
    .\\.venv\\Scripts\\python.exe scripts/pptx_postprocess.py projects/demo
    .\\.venv\\Scripts\\python.exe scripts/pptx_postprocess.py projects/demo/exports/demo.pptx
    .\\.venv\\Scripts\\python.exe scripts/pptx_postprocess.py projects/demo --all
    .\\.venv\\Scripts\\python.exe scripts/pptx_postprocess.py projects/demo --no-backup

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path


_SHAPE_RE = re.compile(r"(?s)<p:sp\b.*?</p:sp>")
_BODY_PR_RE = re.compile(r"<a:bodyPr\b([^>]*)>")
_TEXT_RE = re.compile(r"<a:t(?:\s[^>]*)?>(.*?)</a:t>", re.DOTALL)
_ANCHOR_RE = re.compile(r'\sanchor="[^"]*"')


@dataclass
class PostprocessResult:
    pptx_path: Path
    changed_textboxes: int
    changed_slides: int


def _candidate_pptx_files(target: Path, *, all_exports: bool) -> list[Path]:
    if target.is_file():
        if target.suffix.lower() != ".pptx":
            raise ValueError(f"target file is not a PPTX: {target}")
        return [target]

    if not target.is_dir():
        raise ValueError(f"target does not exist: {target}")

    exports_dir = target / "exports"
    if not exports_dir.is_dir():
        raise ValueError(f"project exports directory does not exist: {exports_dir}")

    pptx_files = sorted(
        exports_dir.glob("*.pptx"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not pptx_files:
        raise ValueError(f"no PPTX files found in {exports_dir}")
    return pptx_files if all_exports else [pptx_files[0]]


def _is_numeric_textbox(shape_xml: str) -> bool:
    if 'txBox="1"' not in shape_xml:
        return False

    text_parts = [
        html.unescape(match.group(1))
        for match in _TEXT_RE.finditer(shape_xml)
    ]
    text = "".join(text_parts).strip()
    return bool(re.fullmatch(r"\d+", text))


def _center_textbox_body(shape_xml: str) -> tuple[str, bool]:
    if not _is_numeric_textbox(shape_xml):
        return shape_xml, False

    match = _BODY_PR_RE.search(shape_xml)
    if not match:
        return shape_xml, False

    attrs = match.group(1)
    self_closing = attrs.rstrip().endswith("/")
    if self_closing:
        attrs = attrs.rstrip()[:-1].rstrip()

    if 'anchor="ctr"' in attrs:
        return shape_xml, False
    if "anchor=" in attrs:
        new_attrs = _ANCHOR_RE.sub(' anchor="ctr"', attrs, count=1)
    else:
        new_attrs = f'{attrs} anchor="ctr"'

    close = "/>" if self_closing else ">"
    updated = shape_xml[:match.start()] + f"<a:bodyPr{new_attrs}{close}" + shape_xml[match.end():]
    return updated, updated != shape_xml


def _process_slide_xml(slide_xml: str) -> tuple[str, int]:
    changed = 0

    def replace_shape(match: re.Match[str]) -> str:
        nonlocal changed
        updated, did_change = _center_textbox_body(match.group(0))
        if did_change:
            changed += 1
        return updated

    return _SHAPE_RE.sub(replace_shape, slide_xml), changed


def postprocess_pptx(pptx_path: Path, *, make_backup: bool = True) -> PostprocessResult:
    if make_backup:
        backup_path = pptx_path.with_suffix(pptx_path.suffix + ".bak")
        shutil.copy2(pptx_path, backup_path)

    changed_textboxes = 0
    changed_slides = 0

    with zipfile.ZipFile(pptx_path, "r") as source:
        entries = {info.filename: source.read(info.filename) for info in source.infolist()}
        infos = {info.filename: info for info in source.infolist()}

    for name, raw in list(entries.items()):
        if not re.fullmatch(r"ppt/slides/slide\d+\.xml", name):
            continue
        slide_xml = raw.decode("utf-8")
        updated, count = _process_slide_xml(slide_xml)
        if count:
            entries[name] = updated.encode("utf-8")
            changed_textboxes += count
            changed_slides += 1

    if changed_textboxes:
        with zipfile.ZipFile(pptx_path, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for name, raw in entries.items():
                info = infos[name]
                new_info = zipfile.ZipInfo(filename=name, date_time=info.date_time)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                new_info.external_attr = info.external_attr
                output.writestr(new_info, raw)

    return PostprocessResult(
        pptx_path=pptx_path,
        changed_textboxes=changed_textboxes,
        changed_slides=changed_slides,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply PPTX-level fixes after svg_to_pptx export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=Path,
        help="Project directory or a specific .pptx file. Project mode processes latest exports/*.pptx.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="In project mode, process all PPTX files in exports/ instead of only the newest.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create <file>.pptx.bak before modifying PPTX files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        pptx_files = _candidate_pptx_files(args.target.resolve(), all_exports=args.all)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    total = 0
    for pptx_path in pptx_files:
        try:
            result = postprocess_pptx(pptx_path, make_backup=not args.no_backup)
        except (OSError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
            print(f"Error processing {pptx_path}: {exc}", file=sys.stderr)
            return 1
        total += result.changed_textboxes
        print(
            f"[OK] {result.pptx_path}: centered {result.changed_textboxes} "
            f"numeric textbox(es) on {result.changed_slides} slide(s)",
            file=sys.stderr,
        )

    print(f"[Done] Centered {total} numeric textbox(es)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
