# Templates Guide: Locked SVG Workflow

A PPT Master template is now a **locked SVG contract**: prepared SVG files stay
on disk, while runtime agents read only `design_spec.md` and
`template_contract.json`.

## 1. Use an Existing Template

Templates are opt-in by explicit directory path only. The path must point to a
locked SVG template directory containing:

- `design_spec.md`
- `template_contract.json`
- one or more `.svg` files

Example:

```text
Use this template: skills/ppt-master/templates/layouts/bit_locked/
```

The workflow copies the full directory into:

```text
projects/<project>/templates/<template_id>/
```

During generation, the agent must not read the template SVG files. It reads the
contract, fills placeholders, generates only workspace fragments, and runs:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py apply <template_dir> <page_stem> --data fill.json -o out.svg
```

## 2. Create a Template

The `/create-template` workflow accepts only a prepared SVG directory. It does
not import PPTX files, screenshots, PDFs, image-only references, or verbal-only
style briefs.

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py inspect <svg_dir>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py create <svg_dir> <template_id>
```

`inspect` prints compact metadata only and never prints SVG source or base64
image payloads.

## 3. SVG Requirements

Replaceable text uses custom placeholders:

```xml
{{PPTTitle}}
{{PPTSubtitle}}
{{PPTDate}}
```

Content pages must mark the editable body area:

```xml
data-ppt-workspace="main"
```

If the workspace element has no direct `x/y/width/height`, add:

```xml
data-ppt-workspace-bbox="x y width height"
```

The generated `template_contract.json` lists every page, placeholder, workspace
bbox, and SVG SHA. If a SVG changes, recreate the template contract.

## 4. Template Boundaries

- Locked SVG templates preserve the original visual shell.
- Runtime agents generate content only inside declared workspaces.
- Embedded PNG/base64 data is allowed in SVGs but stays out of prompt context.
- Old template replication modes are removed; rebuild templates from SVG.
