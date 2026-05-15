#!/usr/bin/env python3
"""
PPT Master - SVG LLM XML Sanitizer

Rewrite SVG files into compact XML that is safe to show to language models:
base64 image payloads and vector path drawing commands are replaced with short
pseudocode while ordinary structure, text, colors, and geometry attributes stay
visible.

Usage:
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_llm_xml.py <svg_file_or_dir> -o <output>

Examples:
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_llm_xml.py reference/template -o reference/template/llm_xml
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_llm_xml.py reference/template/content.svg -o content.xml

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


BASE64_DATA_RE = re.compile(
    r"^data:(?P<mime>[^;,]+)(?:;[^,]*)?;base64,(?P<payload>.*)$",
    re.IGNORECASE | re.DOTALL,
)
PATH_COMMAND_RE = re.compile(r"[AaCcHhLlMmQqSsTtVvZz]")


class SanitizerError(RuntimeError):
    """Raised for user-facing sanitizer failures."""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _path_pseudocode(value: str) -> str:
    commands = " ".join(dict.fromkeys(PATH_COMMAND_RE.findall(value)))
    command_label = commands or "unknown"
    return f"VECTOR_PATH_OMITTED(chars={len(value)}, commands='{command_label}')"


def _data_uri_pseudocode(value: str) -> str:
    match = BASE64_DATA_RE.match(value.strip())
    if not match:
        return value
    mime = match.group("mime")
    payload = match.group("payload")
    return f"data:{mime};base64,BASE64_IMAGE_OMITTED(chars={len(payload)})"


def sanitize_svg_text(svg_text: str, *, source_name: str = "svg") -> str:
    """Return a compact XML rendering of an SVG without heavy payloads."""
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise SanitizerError(f"{source_name}: invalid XML: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise SanitizerError(f"{source_name}: root element must be <svg>")

    path_count = 0
    image_count = 0
    for elem in root.iter():
        for attr_name, attr_value in list(elem.attrib.items()):
            local_attr = _local_name(attr_name)
            if local_attr == "d":
                elem.set(attr_name, _path_pseudocode(attr_value))
                path_count += 1
                continue
            sanitized = _data_uri_pseudocode(attr_value)
            if sanitized != attr_value:
                elem.set(attr_name, sanitized)
                elem.set("data-llm-omitted", "base64-image")
                image_count += 1

    root.set("data-llm-sanitized", "true")
    root.set("data-llm-omitted-paths", str(path_count))
    root.set("data-llm-omitted-base64-images", str(image_count))
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def write_llm_xml_file(svg_file: Path, output_file: Path) -> Path:
    """Sanitize one SVG file into one XML file."""
    if not svg_file.exists() or not svg_file.is_file():
        raise SanitizerError(f"SVG file not found: {svg_file}")
    if svg_file.suffix.lower() != ".svg":
        raise SanitizerError(f"Input file must be .svg: {svg_file}")

    sanitized = sanitize_svg_text(
        svg_file.read_text(encoding="utf-8"),
        source_name=svg_file.name,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(sanitized + "\n", encoding="utf-8")
    return output_file


def write_llm_xml_dir(svg_dir: Path, output_dir: Path) -> list[Path]:
    """Sanitize every top-level SVG in a directory."""
    if not svg_dir.exists() or not svg_dir.is_dir():
        raise SanitizerError(f"SVG directory not found: {svg_dir}")
    svg_files = sorted(path for path in svg_dir.glob("*.svg") if path.is_file())
    if not svg_files:
        raise SanitizerError(f"No .svg files found in {svg_dir}")

    written: list[Path] = []
    for svg_file in svg_files:
        written.append(write_llm_xml_file(svg_file, output_dir / f"{svg_file.stem}.xml"))
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rewrite SVG files into compact LLM-friendly XML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="SVG file or directory")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output XML file for a single SVG, or output directory for an SVG directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.input.is_dir():
            written = write_llm_xml_dir(args.input.resolve(), args.output.resolve())
        else:
            written = [write_llm_xml_file(args.input.resolve(), args.output.resolve())]
    except SanitizerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
