# PPT Master Toolset

This directory contains user-facing scripts for conversion, project setup, SVG processing, export, recorded narration, and image generation.

## Directory Layout

- Top-level `scripts/`: runnable entry scripts
- `scripts/source_to_md/`: source-document → Markdown converters (`pdf_to_md.py`, `doc_to_md.py`, `excel_to_md.py`, `ppt_to_md.py`, `web_to_md.py`)
- `scripts/image_backends/`: internal provider implementations used by `image_gen.py`
- `scripts/tts_backends/`: internal TTS provider implementations used by `notes_to_audio.py`
- `scripts/svg_finalize/`: internal post-processing helpers used by `finalize_svg.py`
- `scripts/docs/`: topic-focused script documentation
- `scripts/assets/`: static assets consumed by scripts

## Quick Start

Typical end-to-end workflow:

```bash
.\.venv\Scripts\python.exe scripts/source_to_md/pdf_to_md.py <file.pdf>
# or
.\.venv\Scripts\python.exe scripts/source_to_md/ppt_to_md.py <deck.pptx>
.\.venv\Scripts\python.exe scripts/source_to_md/excel_to_md.py <workbook.xlsx>
.\.venv\Scripts\python.exe scripts/project_manager.py init <project_name> --format ppt169
.\.venv\Scripts\python.exe scripts/project_manager.py import-sources <project_path> <source_files...> --move
.\.venv\Scripts\python.exe scripts/total_md_split.py <project_path>
.\.venv\Scripts\python.exe scripts/finalize_svg.py <project_path>
.\.venv\Scripts\python.exe scripts/animation_config.py scaffold <project_path>  # optional object-level animation overrides
.\.venv\Scripts\python.exe scripts/svg_to_pptx.py <project_path>
```

Repository update:

```bash
.\.venv\Scripts\python.exe scripts/update_repo.py
```

## Script Index

| Area | Primary scripts | Documentation |
|------|-----------------|---------------|
| Conversion | `source_to_md/pdf_to_md.py`, `source_to_md/doc_to_md.py`, `source_to_md/excel_to_md.py`, `source_to_md/ppt_to_md.py`, `source_to_md/web_to_md.py` | [docs/conversion.md](./docs/conversion.md) |
| Project management | `project_manager.py`, `batch_validate.py`, `generate_examples_index.py`, `error_helper.py` | [docs/project.md](./docs/project.md) |
| SVG pipeline | `finalize_svg.py`, `svg_to_pptx.py`, `total_md_split.py`, `svg_quality_checker.py`, `animation_config.py`, `notes_to_audio.py` | [docs/svg-pipeline.md](./docs/svg-pipeline.md) |
| Locked templates | `svg_template.py`, `register_template.py` | [docs/project.md](./docs/project.md) |
| Spec maintenance | `update_spec.py` | [docs/update_spec.md](./docs/update_spec.md) |
| Image tools | `image_gen.py`, `analyze_images.py`, `gemini_watermark_remover.py` | [docs/image.md](./docs/image.md) |
| Repo maintenance | `update_repo.py` | README install/update section |
| Troubleshooting | validation, preview, export, dependency issues | [docs/troubleshooting.md](./docs/troubleshooting.md) |

## High-Frequency Commands

Conversion:

```bash
.\.venv\Scripts\python.exe scripts/source_to_md/pdf_to_md.py <file.pdf>
.\.venv\Scripts\python.exe scripts/source_to_md/ppt_to_md.py <deck.pptx>
.\.venv\Scripts\python.exe scripts/source_to_md/doc_to_md.py <file.docx>
.\.venv\Scripts\python.exe scripts/source_to_md/excel_to_md.py <workbook.xlsx>
.\.venv\Scripts\python.exe scripts/source_to_md/web_to_md.py <url>
```

Project setup:

```bash
.\.venv\Scripts\python.exe scripts/project_manager.py init <project_name> --format ppt169
.\.venv\Scripts\python.exe scripts/project_manager.py import-sources <project_path> <source_files...> --move
.\.venv\Scripts\python.exe scripts/project_manager.py validate <project_path>
```

Locked SVG templates:

```bash
.\.venv\Scripts\python.exe scripts/svg_template.py inspect <svg_dir>
.\.venv\Scripts\python.exe scripts/svg_template.py create <svg_dir> <template_id>
.\.venv\Scripts\python.exe scripts/svg_template.py apply <template_dir> <page_stem> --data fill.json -o out.svg
```

Post-processing and export:

```bash
.\.venv\Scripts\python.exe scripts/total_md_split.py <project_path>
.\.venv\Scripts\python.exe scripts/finalize_svg.py <project_path>
.\.venv\Scripts\python.exe scripts/svg_to_pptx.py <project_path>
```

Image generation:

```bash
.\.venv\Scripts\python.exe scripts/image_gen.py "A modern futuristic workspace"
.\.venv\Scripts\python.exe scripts/image_gen.py --list-backends
.\.venv\Scripts\python.exe scripts/analyze_images.py <project_path>/images
```

Repository update:

```bash
.\.venv\Scripts\python.exe scripts/update_repo.py
.\.venv\Scripts\python.exe scripts/update_repo.py --skip-pip
```

## Recommendations

- Keep one user-facing entry point per workflow at the top level of `scripts/`
- Move provider-specific or helper internals into subdirectories
- Prefer the unified entry points `project_manager.py`, `finalize_svg.py`, and `image_gen.py`
- Prefer `svg_final/` over `svg_output/` when exporting

## Related Docs

- [Conversion Tools](./docs/conversion.md)
- [Project Tools](./docs/project.md)
- [SVG Pipeline Tools](./docs/svg-pipeline.md)
- [Image Tools](./docs/image.md)
- [Troubleshooting](./docs/troubleshooting.md)
- [Skill Entry](../SKILL.md)

_Last updated: 2026-04-09_
