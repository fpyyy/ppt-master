---
description: Create a locked SVG template from an existing SVG directory
---

# Create Locked SVG Template Workflow

> **Role invoked**: [Template_Designer](../references/template-designer.md)

Create a reusable **locked SVG** layout template for the global template
library. The input MUST be a directory of existing SVG files. PPTX, image,
PDF, screenshot, and verbal-only template creation are not supported.

## Process Overview

```
SVG Directory Intake -> Script Inspection -> Brief Confirmation -> svg_template.py create -> Validate -> Register -> Output
```

**Hard rule**: Agents MUST NOT manually read template SVG source with
`Read`, `Get-Content`, `cat`, `sed`, or similar. SVGs may contain base64 image
payloads. Use `svg_template.py inspect` and `svg_template.py create`; those
commands print only compact metadata.

---

## Step 1: SVG Directory Intake

🚧 **GATE**: User supplied a directory containing one or more `.svg` files.

Reject all other source types:

| User supplied | Action |
|---|---|
| SVG directory | Continue |
| `.pptx`, PDF, screenshots, images, brand description, or template name only | Stop; ask for a prepared SVG directory |

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py inspect <svg_dir>
```

Inspection output is the only source for:

- SVG filenames and page roles
- root `viewBox`
- discovered `{{...}}` placeholders such as `{{PPTTitle}}`
- declared workspaces, especially `data-ppt-workspace="main"`
- embedded image counts and local asset counts

**Validation**: Content pages must declare at least one workspace. Prefer:

```xml
data-ppt-workspace="main"
```

If the workspace element has no direct `x/y/width/height`, it MUST declare:

```xml
data-ppt-workspace-bbox="x y width height"
```

---

## Step 2: Brief Proposal

Compose a concise brief from the user request plus `inspect` output.

| Field | Requirement |
|---|---|
| Template ID | Required, filesystem-safe directory name |
| Display name | Required |
| Category | `brand` / `general` / `scenario` / `government` / `special` |
| Summary | One-line use case and visual identity |
| Keywords | 3-5 short lookup tags |
| Primary color | Required; use user-provided value or a conservative default |
| Canvas format | Required; default `ppt169` unless inspect output implies otherwise |
| Source SVG directory | Required |
| Runtime model | Fixed: `locked_svg` |

**Forbidden**:

- Legacy replication mode selection
- PPTX import or screenshots
- Asking the model to visually inspect SVG content
- Describing embedded images from SVG source

---

## Step 3: User Confirmation Gate

⚠️ **BLOCKING**: Echo the finalized brief and wait for explicit confirmation.
Then emit:

```text
[TEMPLATE_BRIEF_CONFIRMED]
```

Do not create the template directory until this marker has been emitted in the
current conversation.

---

## Step 4: Create Locked Template

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py create <svg_dir> <template_id> --display-name "<display_name>" --category <category> --summary "<summary>" --keywords "<k1,k2,k3>" --primary-color "<hex>" --canvas-format <canvas_format>
```

Outputs:

| File | Purpose |
|---|---|
| `skills/ppt-master/templates/layouts/<template_id>/*.svg` | Locked source SVGs copied verbatim |
| `design_spec.md` | Human-readable template personality + runtime contract pointer |
| `template_contract.json` | Machine-readable runtime contract |

`template_contract.json` contains:

```json
{
  "schema_version": 1,
  "engine": "locked_svg",
  "template_id": "<template_id>",
  "canvas_format": "ppt169",
  "pages": [
    {
      "stem": "03_content",
      "file": "03_content.svg",
      "role": "content",
      "viewBox": "0 0 1280 720",
      "sha256": "...",
      "placeholders": [
        {"name": "PPTTitle", "token": "{{PPTTitle}}", "count": 1}
      ],
      "workspaces": [
        {"id": "main", "bbox": [80, 120, 1120, 500], "element": "rect"}
      ]
    }
  ]
}
```

The create command registers the template automatically when writing under the
global layout library.

---

## Step 5: Validate

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py "skills/ppt-master/templates/layouts/<template_id>" --template-mode --format <canvas_format>
```

Validation must pass with zero errors. The checker verifies:

- `design_spec.md` roster matches SVG files
- `template_contract.json` exists and declares `engine: locked_svg`
- contract page list matches SVG files
- contract SHA values match the copied SVG files
- content pages declare valid workspace boxes
- declared custom placeholders are honored

---

## Step 6: Output

Report the card printed by `svg_template.py create` / `register_template.py`
and include the template path:

```text
skills/ppt-master/templates/layouts/<template_id>/
```

When using this template in a project, the agent reads only
`design_spec.md` and `template_contract.json`; template SVG files stay out of
the runtime context.
