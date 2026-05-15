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
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py apply <template_dir> <page_stem> --data fill.json -o out.svg

Examples:
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py inspect reference/AI-template
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py create reference/AI-template bit_locked --display-name "BIT Locked"
    .\\.venv\\Scripts\\python.exe skills/ppt-master/scripts/svg_template.py apply skills/ppt-master/templates/layouts/bit_locked 03_content --data fill.json -o projects/demo/svg_output/03_content.svg

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
LAYOUTS_DIR = SKILL_DIR / "templates" / "layouts"

PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z][A-Za-z0-9_]*)\}\}")
SVG_CLOSE_RE = re.compile(r"</svg\s*>\s*$", re.IGNORECASE)
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


class TemplateError(RuntimeError):
    """Raised for user-facing template failures."""


@dataclass
class Workspace:
    workspace_id: str
    bbox: tuple[float, float, float, float]
    element: str


@dataclass
class SvgSummary:
    source: Path
    file_name: str
    stem: str
    role: str
    view_box: str
    sha256: str
    placeholders: dict[str, int]
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


def _infer_role(stem: str) -> str:
    lowered = stem.lower()
    if "cover" in lowered or lowered.startswith("01"):
        return "cover"
    if "toc" in lowered or "catalog" in lowered:
        return "toc"
    if "chapter" in lowered or "section" in lowered:
        return "chapter"
    if "ending" in lowered or "closing" in lowered or "thanks" in lowered:
        return "ending"
    return "content"


def _find_workspaces(root: ET.Element, svg_file: Path) -> list[Workspace]:
    workspaces: list[Workspace] = []
    for elem in root.iter():
        workspace_id = elem.attrib.get("data-ppt-workspace")
        if not workspace_id:
            continue
        bbox = _element_bbox(elem)
        if bbox is None:
            raise TemplateError(
                f"{svg_file.name}: workspace {workspace_id!r} has no geometry. "
                "Add x/y/width/height or data-ppt-workspace-bbox=\"x y width height\"."
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


def _read_svg_summary(svg_file: Path) -> SvgSummary:
    text = svg_file.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise TemplateError(f"{svg_file.name}: invalid XML: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise TemplateError(f"{svg_file.name}: root element must be <svg>")
    view_box = root.attrib.get("viewBox", "").strip()
    if not view_box:
        raise TemplateError(f"{svg_file.name}: missing root viewBox")

    placeholders: dict[str, int] = {}
    for match in PLACEHOLDER_RE.finditer(text):
        placeholders[match.group(1)] = placeholders.get(match.group(1), 0) + 1

    workspaces = _find_workspaces(root, svg_file)
    role = _infer_role(svg_file.stem)
    if role == "content" and not workspaces:
        raise TemplateError(
            f"{svg_file.name}: content pages must declare data-ppt-workspace=\"main\" "
            "or another explicit workspace."
        )

    local_assets, embedded_count = _collect_local_assets(root, svg_file)
    digest = hashlib.sha256(svg_file.read_bytes()).hexdigest()
    return SvgSummary(
        source=svg_file,
        file_name=svg_file.name,
        stem=svg_file.stem,
        role=role,
        view_box=view_box,
        sha256=digest,
        placeholders=placeholders,
        workspaces=workspaces,
        local_assets=local_assets,
        embedded_image_count=embedded_count,
    )


def _scan_svg_dir(svg_dir: Path) -> list[SvgSummary]:
    if not svg_dir.is_dir():
        raise TemplateError(f"SVG directory not found: {svg_dir}")
    svg_files = sorted(path for path in svg_dir.glob("*.svg") if path.is_file())
    if not svg_files:
        raise TemplateError(f"No .svg files found in {svg_dir}")
    return [_read_svg_summary(path) for path in svg_files]


def _contract_page(summary: SvgSummary) -> dict[str, Any]:
    return {
        "stem": summary.stem,
        "file": summary.file_name,
        "role": summary.role,
        "viewBox": summary.view_box,
        "sha256": summary.sha256,
        "placeholders": [
            {"name": name, "token": f"{{{{{name}}}}}", "count": count}
            for name, count in sorted(summary.placeholders.items())
        ],
        "workspaces": [
            {
                "id": workspace.workspace_id,
                "bbox": [_format_float(part) for part in workspace.bbox],
                "element": workspace.element,
            }
            for workspace in summary.workspaces
        ],
    }


def build_contract(
    template_id: str,
    summaries: list[SvgSummary],
    *,
    canvas_format: str,
) -> dict[str, Any]:
    """Build the compact template contract from SVG summaries."""
    view_boxes = {summary.view_box for summary in summaries}
    if len(view_boxes) != 1:
        raise TemplateError(
            "All SVG pages in one locked template must use the same viewBox. "
            f"Found: {', '.join(sorted(view_boxes))}"
        )
    return {
        "schema_version": 1,
        "engine": "locked_svg",
        "template_id": template_id,
        "canvas_format": canvas_format,
        "pages": [_contract_page(summary) for summary in summaries],
    }


def _keywords_list(raw: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;]", raw) if part.strip()]


def _render_design_spec(
    *,
    template_id: str,
    display_name: str,
    category: str,
    summary: str,
    keywords: list[str],
    primary_color: str,
    canvas_format: str,
    pages: list[SvgSummary],
) -> str:
    placeholders = {
        page.stem: [f"{{{{{name}}}}}" for name in sorted(page.placeholders)]
        for page in pages
    }
    frontmatter = {
        "template_id": template_id,
        "display_name": display_name,
        "category": category,
        "summary": summary,
        "keywords": keywords,
        "primary_color": primary_color,
        "canvas_format": canvas_format,
        "template_engine": "locked_svg",
        "template_contract": "template_contract.json",
        "placeholder_style": "custom",
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
            f"# {display_name} - Locked SVG Template Specification",
            "",
            "## I. Template Overview",
            "",
            f"- Summary: {summary}",
            f"- Category: {category}",
            "- Engine: locked SVG. Runtime agents must read `template_contract.json`, not SVG files.",
            "",
            "## II. Color Scheme",
            "",
            f"- Primary color: `{primary_color}`",
            "",
            "## III. Signature Design Elements",
            "",
            "- Visual identity is locked inside the SVG files. Do not describe or re-read SVG source during deck generation.",
            "- Replace only declared `{{...}}` placeholders and inject generated content into declared workspaces.",
            "",
            "## IV. Runtime Contract",
            "",
            "- Contract file: `template_contract.json`",
            "- Template engine: `locked_svg`",
            "- Runtime fill command: `svg_template.py apply <template_dir> <page_stem> --data <fill.json> -o <out.svg>`",
            "",
            "## V. Page Roster",
            "",
            *roster,
            "",
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
            f"{workspace.workspace_id}={workspace.bbox[0]:g},{workspace.bbox[1]:g},{workspace.bbox[2]:g},{workspace.bbox[3]:g}"
            for workspace in summary.workspaces
        ) or "none"
        print(
            f"- {summary.file_name}: role={summary.role}; viewBox={summary.view_box}; "
            f"placeholders={placeholders}; workspaces={workspaces}; "
            f"embedded_images={summary.embedded_image_count}; local_assets={len(summary.local_assets)}"
        )
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
        shutil.copy2(summary.source, template_dir / summary.file_name)
    _copy_referenced_assets(summaries, template_dir)

    contract = build_contract(
        args.template_id,
        summaries,
        canvas_format=args.canvas_format,
    )
    (template_dir / "template_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    keywords = _keywords_list(args.keywords)
    display_name = args.display_name or args.template_id
    summary = args.summary or f"Locked SVG template generated from {args.svg_dir.name}."
    design_spec = _render_design_spec(
        template_id=args.template_id,
        display_name=display_name,
        category=args.category,
        summary=summary,
        keywords=keywords,
        primary_color=args.primary_color,
        canvas_format=args.canvas_format,
        pages=summaries,
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
    inspect_parser.set_defaults(func=cmd_inspect)

    create_parser = subparsers.add_parser(
        "create",
        help="Create a locked SVG template from a directory of SVG files.",
    )
    create_parser.add_argument("svg_dir", type=Path)
    create_parser.add_argument("template_id")
    create_parser.add_argument("--display-name", default="")
    create_parser.add_argument("--category", default="brand")
    create_parser.add_argument("--summary", default="")
    create_parser.add_argument("--keywords", default="locked-svg,template")
    create_parser.add_argument("--primary-color", default="#000000")
    create_parser.add_argument("--canvas-format", default="ppt169")
    create_parser.add_argument("--output-dir", type=Path)
    create_parser.add_argument("--force", action="store_true")
    create_parser.add_argument("--no-register", action="store_true")
    create_parser.set_defaults(func=cmd_create)

    apply_parser = subparsers.add_parser(
        "apply",
        help="Fill one locked SVG page from JSON placeholder/workspace data.",
    )
    apply_parser.add_argument("template_dir", type=Path)
    apply_parser.add_argument("page_stem")
    apply_parser.add_argument("--data", required=True, type=Path)
    apply_parser.add_argument("-o", "--output", required=True, type=Path)
    apply_parser.add_argument("--strict", action="store_true")
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
