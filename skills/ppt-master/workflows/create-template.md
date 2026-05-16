---
description: Create a locked SVG template from an existing SVG directory
---

# Create Locked SVG Template Workflow

> **Role invoked**: [Template_Designer](../references/template-designer.md)

Create a reusable **locked SVG** layout template for the global template
library. The input MUST be a directory containing exactly five existing SVG
files: `title.svg`, `toc.svg`, `chapter.svg`, `content.svg`, and `ending.svg`.
PPTX, image, PDF, screenshot, and verbal-only template creation are not
supported.

## Process Overview

```
SVG Directory Intake -> Script Inspection + LLM XML -> Template Style Lock -> Template ID Confirmation -> svg_template.py create -> Content ViewBox Visualization -> Validate -> Register -> Output
```

**Hard rule**: Agents MUST NOT manually read template SVG source with
`Read`, `Get-Content`, `cat`, `sed`, or similar. SVGs may contain base64 image
payloads. Use `svg_template.py inspect`, `svg_llm_xml.py`, and
`svg_template.py create`; those commands print or write only compact metadata /
redacted XML.

---

## Step 1: SVG Directory Intake

🚧 **GATE**: User supplied a directory containing exactly these top-level files:
`title.svg`, `toc.svg`, `chapter.svg`, `content.svg`, `ending.svg`.

Reject all other source types:

| User supplied | Action |
|---|---|
| SVG directory with exactly the five required SVGs | Continue |
| `.pptx`, PDF, screenshots, images, brand description, or template name only | Stop; ask for a prepared SVG directory |
| Missing / extra SVG filenames | Stop; ask the user to rename or remove files |

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py inspect <svg_dir>
```

Inspection output is the only source for:

- SVG filenames and page roles
- root `viewBox`
- discovered `{{...}}` placeholders such as `{{PPTTitle}}`
- inferred `content.svg` workspace bbox
- embedded image counts and local asset counts

**Validation**: The script rejects any top-level SVG set other than the fixed
five filenames. It also rejects workspace declarations on non-content pages.

---

## Step 1.5: LLM-Friendly XML Generation

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_llm_xml.py <svg_dir> -o <svg_dir>\llm_xml
```

This generates `llm_xml/title.xml`, `llm_xml/toc.xml`, `llm_xml/chapter.xml`,
`llm_xml/content.xml`, and `llm_xml/ending.xml`.

**Hard rule**: Read only these sanitized XML files when judging theme colors,
visual density, placeholder placement, and text budgets. Do not read raw SVG.

**Sanitization contract**:

| SVG source | XML output |
|---|---|
| base64 image payloads | `data:<mime>;base64,BASE64_IMAGE_OMITTED(...)` |
| path `d="..."` drawing commands | `VECTOR_PATH_OMITTED(...)` |
| text, fill/stroke colors, transforms, geometry | Preserved |

---

## Step 1.6: Template Style Lock Extraction

Use `llm_xml/*.xml` to determine the template's base visual system before
creating the locked template package.

| Lock Area | Source in `llm_xml` | Output |
|---|---|---|
| Base colors | `fill`, `stroke`, `stop-color`, `flood-color`, `color`, geometry scale, text elements | `bg`, `secondary_bg`, `primary`, `accent`, `secondary_accent`, `text`, `text_secondary`, `border` |
| Typography | `font-family`, `font-size`, placeholder text roles such as `{{PPTTitle}}` / `{{PageTitle}}` | `font_family`, role families, `body`, `title`, `subtitle`, `annotation`, optional `cover_title` |

**Hard rule**: The base colors and typography come from the prepared SVGs via
`llm_xml`; do not ask the user to pick a primary color or font during template
creation, and do not invent a new palette to make the template feel more
"complete."

**Script behavior**: `svg_template.py create` automatically re-generates
`llm_xml/`, extracts the style lock, and writes it into both `design_spec.md`
and `template_contract.json`.

**Validation**: If the extracted colors or fonts look wrong, correct the source
SVGs and re-run the workflow. Do not patch downstream PPT generation to work
around a bad template lock.

---

## Step 2: Template ID Confirmation

Compose a minimal confirmation from the user request plus `inspect` output.

| Field | Requirement |
|---|---|
| Template ID | Required, filesystem-safe directory name |
| Canvas format | Required; default `ppt169` unless inspect output implies otherwise |
| Source SVG directory | Required |
| Runtime model | Fixed: `locked_svg` |

**Hard rule**: Do not ask for or invent display name, category, summary,
keywords, use-case prose, or decorative metadata. The template ID is the only
human name. Base colors and typography are determined by Step 1.6 from
`llm_xml`.

**Forbidden**:

- Legacy replication mode selection
- PPTX import or screenshots
- Asking the model to read raw SVG content
- Describing embedded images from SVG source
- Saving decorative metadata that is not required by runtime

---

## Step 3: User Confirmation Gate

⚠️ **BLOCKING**: Echo the minimal template ID confirmation and wait for
explicit confirmation.
Then emit:

```text
[TEMPLATE_ID_CONFIRMED]
```

Do not create the template directory until this marker has been emitted in the
current conversation.

---

## Step 4: Create Locked Template

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py create <svg_dir> <template_id> --canvas-format <canvas_format>
```

Outputs:

| File | Purpose |
|---|---|
| `skills/ppt-master/templates/layouts/<template_id>/*.svg` | Locked SVGs copied from source; missing root `viewBox` is inferred from `width`/`height` |
| `llm_xml/*.xml` | Creation-time sanitized XML copies for theme / color / font inspection |
| `debug/content_viewbox.svg` | Visual overlay for `content.svg` root `viewBox` and declared workspaces |
| `design_spec.md` | Runtime contract pointer, page roster, and template style lock |
| `template_contract.json` | Machine-readable runtime contract, including `style_lock` |

`template_contract.json` contains:

```json
{
  "schema_version": 1,
  "engine": "locked_svg",
  "template_id": "<template_id>",
  "canvas_format": "ppt169",
  "style_lock": {
    "source": "llm_xml",
    "colors": {
      "bg": "#FFFFFF",
      "primary": "#005C30",
      "accent": "#009944",
      "text": "#111111"
    },
    "typography": {
      "font_family": "Microsoft YaHei, sans-serif",
      "title_family": "Microsoft YaHei, sans-serif",
      "body": 22,
      "title": 34
    }
  },
  "pages": [
    {
      "stem": "content",
      "file": "content.svg",
      "role": "content",
      "viewBox": "0 0 1280 720",
      "sha256": "...",
      "placeholders": [
        {
          "name": "PageTitle",
          "token": "{{PageTitle}}",
          "count": 1,
          "text_fit": {"max_cjk_chars": 22, "max_latin_chars": 40}
        }
      ],
      "workspaces": [
        {"id": "main", "bbox": [80, 150, 1120, 480], "element": "auto", "source": "auto-heuristic"}
      ]
    }
  ]
}
```

The create command registers the template automatically when writing under the
global layout library.

---

## Step 4.5: Content ViewBox Visualization

Run after `svg_template.py create`:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py visualize-content "skills/ppt-master/templates/layouts/<template_id>"
```

Default output:

```text
skills/ppt-master/templates/layouts/<template_id>/debug/content_viewbox.svg
```

**Purpose**: Generate a human-checkable SVG overlay for `content.svg`. The blue
outline marks the root `viewBox`; orange dashed boxes mark each workspace from
`template_contract.json`.

**Hard rule**: Keep the visualization under `debug/`. Do not place debug SVGs
at the template directory root; locked templates must keep exactly five
top-level SVG files.

**Hard rule**: Treat `debug/content_viewbox.svg` as a human visual artifact. Do
not read its source into prompt context; it may embed the full `content.svg` as
a data URI.

**When to inspect**:

| Condition | Action |
|---|---|
| New template created | Generate `debug/content_viewbox.svg` for optional human inspection |
| Workspace bbox looks wrong in `inspect` output | Open the debug SVG before proceeding |
| Validation-driven SVG correction touched `content.svg` or contract workspaces | Regenerate and inspect the debug SVG before refreshing SHA values |

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
- the template contains exactly `title.svg`, `toc.svg`, `chapter.svg`, `content.svg`, `ending.svg`
- only `content.svg` declares a valid workspace box
- declared custom placeholders are honored

### 5.1 Validation Failure Handling

**Hard rule**: Do not make a template pass validation by deleting SVG features
that may carry visual meaning. A zero-error report is not sufficient if the
rendered template changes.

| Failure | Action |
|---|---|
| `clip-path` on a non-image element | Use sanitized `llm_xml/*.xml` to identify the clipped content. Do not read raw SVG source. |
| Page-boundary clip where the clip rect exactly matches the root viewBox | Removing the redundant clip from the generated template copy is allowed. Regenerate `llm_xml/` afterward. |
| Clip wrapper around `<image>`, `<use>`, or an embedded image group | Preserve the crop visually. Convert it to a PPT-safe equivalent such as a pre-cropped embedded image or a direct `<image clip-path="...">` that satisfies [`shared-standards.md`](../references/shared-standards.md) §1.2. |
| Clip wrapper around arbitrary shapes / text | Stop and ask for a corrected SVG source, unless an exact geometry rewrite is available without visual change. |
| `contract_sha_mismatch` after any SVG correction | Refresh `template_contract.json` SHA values only after the visual-equivalent SVG correction is complete. |

**Forbidden - validation-only edits**:

- Do not mechanically remove `clip-path` from `<g>` wrappers.
- Do not flatten, crop, or rewrite embedded images unless the output preserves
  the original visible crop.
- Do not update `template_contract.json` hashes to bless a visually changed
  template.

**Validation**: After any correction, regenerate creation-time sanitized XML
for the template directory and re-run `svg_quality_checker.py`. Treat visual
parity with the source template as part of the validation gate.

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
