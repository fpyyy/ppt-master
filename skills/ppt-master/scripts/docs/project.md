# Project and Template Tools

These scripts manage PPT Master project folders and locked SVG templates.

## `project_manager.py`

Create, inspect, validate, and import sources into project folders.

```bash
.\.venv\Scripts\python.exe scripts/project_manager.py init <project_name> --format ppt169
.\.venv\Scripts\python.exe scripts/project_manager.py import-sources <project_path> <source_files...> --move
.\.venv\Scripts\python.exe scripts/project_manager.py validate <project_path>
.\.venv\Scripts\python.exe scripts/project_manager.py info <project_path>
```

## `svg_template.py`

Create and fill locked SVG templates.

```bash
.\.venv\Scripts\python.exe scripts/svg_template.py inspect <svg_dir>
.\.venv\Scripts\python.exe scripts/svg_template.py create <svg_dir> <template_id>
.\.venv\Scripts\python.exe scripts/svg_template.py apply <template_dir> <page_stem> --data fill.json -o out.svg
```

Notes:

- `inspect` prints compact metadata only: filenames, viewBox, placeholders, workspaces, and image counts.
- `inspect` and `create` may read SVG files internally, but they never print SVG source or base64 payloads.
- `create` copies SVG files verbatim, writes `design_spec.md`, writes `template_contract.json`, and registers templates created under `skills/ppt-master/templates/layouts/`.
- `apply` replaces custom `{{...}}` placeholders and injects workspace fragments into declared `data-ppt-workspace` areas.
- Runtime agents read `template_contract.json`, not template SVG files.

## `register_template.py`

Register or rebuild the global layout template index.

```bash
.\.venv\Scripts\python.exe scripts/register_template.py <template_id>
.\.venv\Scripts\python.exe scripts/register_template.py --rebuild-all
```

Locked SVG templates must include:

- `design_spec.md` with `template_engine: locked_svg`
- `template_contract.json`
- one or more `.svg` files listed in the contract

## `batch_validate.py`

Validate multiple projects or examples in one pass.

```bash
.\.venv\Scripts\python.exe scripts/batch_validate.py examples
```

## `generate_examples_index.py`

Rebuild `examples/README.md` automatically.

```bash
.\.venv\Scripts\python.exe scripts/generate_examples_index.py
.\.venv\Scripts\python.exe scripts/generate_examples_index.py examples
```

## `error_helper.py`

Show standardized fixes for common project errors.

```bash
.\.venv\Scripts\python.exe scripts/error_helper.py
.\.venv\Scripts\python.exe scripts/error_helper.py missing_readme
.\.venv\Scripts\python.exe scripts/error_helper.py missing_readme project_path=my_project
```
