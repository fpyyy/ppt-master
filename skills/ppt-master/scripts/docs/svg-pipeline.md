# SVG Pipeline Tools

> Architecture rationale: see [docs/technical-design.md "Post-Processing Pipeline"](../../../../docs/technical-design.md#post-processing-pipeline).

These tools cover SVG validation, post-processing, speaker notes, recorded narration, locked template application, and PPTX export.

## Recommended Pipeline

Run these steps in order from the repository root:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/layout_compile.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_text_fit.py <project_path> --from-layout
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_layout_checker.py <project_path> --from-layout
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_text_fit.py <project_path> --fix
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_layout_checker.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/total_md_split.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/finalize_svg.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/pptx_postprocess.py <project_path>
```

Locked SVG templates add one pre-finalization step per templated page:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py apply <project_path>/templates/<template_id> <page_stem> --data <fill.json> -o <project_path>/svg_output/<slide>.svg
```

## `svg_template.py`

Create and apply locked SVG templates.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py inspect <svg_dir>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_llm_xml.py <svg_dir> -o <svg_dir>\llm_xml
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py create <svg_dir> <template_id>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py visualize-content <template_dir>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py apply <template_dir> <page_stem> --data <fill.json> -o <out.svg>
```

`inspect` reports compact metadata only; it never prints SVG source or embedded base64 image data.
`svg_llm_xml.py` writes model-readable XML with base64 images and path `d` payloads redacted.
`create` requires `title.svg`, `toc.svg`, `chapter.svg`, `content.svg`, and `ending.svg`; it copies the source SVGs, infers any missing root `viewBox` from `width`/`height`, and writes `llm_xml/`, `design_spec.md`, and `template_contract.json`.
`visualize-content` writes `debug/content_viewbox.svg` under the template directory so the `content.svg` root `viewBox` and workspace boxes can be inspected without adding a sixth top-level SVG.
`apply` replaces custom placeholders such as `{{PPTTitle}}`; it injects workspace fragments only for `content.svg`.
`apply` checks placeholder `text_fit` budgets. Entries marked
`enforce: always` are hard constraints and are still checked if
`--no-fit-check` is used for template debugging; this is intended for
direct-fill TOC / chapter section titles.

## `finalize_svg.py`

Unified post-processing entry point. This is the preferred way to run SVG cleanup.

It aggregates:
- `embed_icons.py`
- `crop_images.py`
- `fix_image_aspect.py`
- `embed_images.py`
- `flatten_tspan.py`
- `svg_rect_to_path.py`

## `svg_text_fit.py`

Detect SVG text overflow before export.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_text_fit.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_text_fit.py <project_path> --fix
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_text_fit.py <svg_file> --fix
```

Behavior:
- Measures text bounding boxes against containing rectangles, template workspaces, and the canvas.
- `--fix` wraps simple single-style text in place, but never splits Latin words into letters.
- `font-size` is never changed.
- Remaining overflow is a hard gate; repair by wrapping, expanding containers, shortening wording, or re-layout.

## `svg_layout_checker.py`

Detect structural geometry defects before export.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_layout_checker.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_layout_checker.py <svg_file>
```

Behavior:
- Recognizes `data-layout` and common group ids such as `hub-spoke`.
- Checks hub-spoke center alignment, card size, connector count, and opposite-card symmetry.
- Checks card/icon grid size alignment and timeline axis alignment.
- `--from-layout` validates deterministic compile output from `layout_v2_compiled.json` (bbox validity, overlap, and simple alignment constraints).
- Remaining structural issues are a hard gate; repair by recomputing the geometry model and re-layout.

## `layout_compile.py`

Compile `layout_v2.json` semantic content to deterministic geometry and render SVG pages.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/layout_compile.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/layout_compile.py <project_path> --strict
```

Behavior:
- Enforces LayoutSpec v2 required fields (`slide_type`, `content`, `constraints`, `capacity`, `overflow_policy`)
- Rejects free coordinate keys in semantic input
- Uses fixed internal canvas (1920x1080) and design tokens
- Applies deterministic text fitting and emits `layout_v2_compiled.json`
- Writes SVG files to `svg_output/` from compiled geometry

## `svg_to_pptx.py`

Convert project SVGs into PPTX.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path> --only native
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path> --only legacy
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path> --no-notes
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path> -t none
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path> --auto-advance 3
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path> --animation mixed --animation-duration 0.8
.\.venv\Scripts\python.exe skills/ppt-master/scripts/notes_to_audio.py <project_path> --voice zh-CN-XiaoxiaoNeural
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_to_pptx.py <project_path> --recorded-narration audio
```

Behavior:
- Default output includes the main native editable PPTX, an SVG snapshot PPTX for visual reference, and a backup copy of the Executor SVG source.
- Explicit `-o/--output` keeps the legacy side-by-side `_svg.pptx` next to the chosen path and skips `backup/`.
- Recommended source directory is `svg_final/` after `finalize_svg.py`; the converter falls back according to its CLI rules.
- Native mode is strict about unsupported visual SVG elements and reports the SVG file, element tag, and position instead of silently dropping content.
- Native output uses content-hash media filenames, so identical images are reused and different images cannot overwrite each other by sharing a basename.
- `[Content_Types].xml` is generated from the actual media extensions written into the PPTX. Unknown media extensions fail unless Python's `mimetypes` can identify them.
- Native export writes to a temporary file first and publishes the requested PPTX only after conversion succeeds. A failed conversion does not replace the main output file.
- SVG clip paths are still restricted for authored SVGs, but nested crop wrappers generated by tooling are mapped back to native picture crop / geometry when possible.
- Speaker notes are embedded automatically unless `--no-notes` is used.
- Recorded narration is opt-in. `notes_to_audio.py` generates one audio file per slide into `audio/`; `--recorded-narration audio` embeds matching audio and slide timings.
- Page transitions are controlled by `-t/--transition`; per-element entrance animations are controlled by `-a/--animation`.
- Per-element animation applies to top-level SVG `<g id="...">` groups in z-order. Page chrome is skipped automatically by id token.
- `on-click` is for live presentations only; recorded narration rejects it because the tool does not generate object-level click timings.
- Optional object-level overrides live in `<project>/animations.json` or a path passed via `--animation-config`; build and validate them with `animation_config.py scaffold|validate`.

Dependency:

```bash
.\.venv\Scripts\python.exe -m pip install python-pptx
```

## `pptx_postprocess.py`

Apply PPTX-level DrawingML fixes after export.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/pptx_postprocess.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/pptx_postprocess.py <pptx_file>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/pptx_postprocess.py <project_path> --all
.\.venv\Scripts\python.exe skills/ppt-master/scripts/pptx_postprocess.py <project_path> --no-backup
```

Behavior:
- Project mode processes the newest PPTX in `exports/` by default.
- File mode processes the specified `.pptx`.
- Numeric-only text boxes are changed from top alignment to middle alignment with `a:bodyPr anchor="ctr"`.
- A `.pptx.bak` backup is created unless `--no-backup` is passed.

## `total_md_split.py`

Split `total.md` into per-slide note files.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/total_md_split.py <project_path>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/total_md_split.py <project_path> -o <output_directory>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/total_md_split.py <project_path> -q
```

Requirements:
- Each section begins with `# `
- Heading text matches the SVG filename
- Sections are separated by `---`

## `svg_quality_checker.py`

Validate SVG technical compliance.

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py examples/project/svg_output/01_cover.svg
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py examples/project/svg_output
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py examples/project
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py examples/project --format ppt169
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py --all examples
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py examples/project --export
```

Checks include:
- `viewBox`
- banned elements
- width/height consistency
- line-break structure
- locked template contract integrity in `--template-mode`

## `svg_position_calculator.py`

Analyze and review supported chart coordinates after SVG generation.
