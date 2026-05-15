> See [`../workflows/create-template.md`](../workflows/create-template.md) for the locked SVG template workflow.

# Role: Template_Designer

Role definition for creating reusable locked SVG templates from an existing SVG
directory. Trigger only through the `/create-template` workflow.

## Core Mission

Convert prepared SVG files into a locked template package. The role does not
redesign, visually inspect, or rewrite SVG source.

---

## 1. Input Contract

| Input | Requirement |
|---|---|
| Source directory | Directory containing one or more `.svg` files |
| Brief | Confirmed template ID, display name, category, summary, keywords, primary color, canvas format |
| Inspection output | Output from `svg_template.py inspect` |

**Hard rule**: Do not read SVG files directly. They may contain base64 images.
Use only `svg_template.py inspect` output for metadata.

**Forbidden - legacy sources**:

- `.pptx` template import
- screenshots / image references
- PDF or verbal-only template creation
- legacy replication mode selection

---

## 2. SVG Authoring Requirements

Templates are authored outside this role. This role only verifies that the
existing SVG files expose a runtime contract.

| Feature | Requirement |
|---|---|
| Replaceable text | Use custom `{{...}}` placeholders, e.g. `{{PPTTitle}}` |
| Content workspace | Use `data-ppt-workspace="main"` on the editable body area |
| Workspace bbox | Use direct `x/y/width/height` or `data-ppt-workspace-bbox="x y width height"` |
| Canvas | All pages in a template use one root `viewBox` |
| Embedded images | Allowed, but never surfaced in prompt context |

**Hard rule**: Content pages must declare at least one workspace. The runtime
agent will generate only the workspace fragment, then `svg_template.py apply`
injects it into the locked SVG.

---

## 3. Generated Files

Run `svg_template.py create`. It writes the complete template package.

| File | Notes |
|---|---|
| `*.svg` | Copied verbatim from the source directory |
| `design_spec.md` | Template personality and runtime pointer |
| `template_contract.json` | Machine-readable contract for runtime use |

`design_spec.md` frontmatter MUST include:

```yaml
template_engine: locked_svg
template_contract: template_contract.json
placeholder_style: custom
```

`template_contract.json` MUST include:

| Field | Notes |
|---|---|
| `schema_version` | `1` |
| `engine` | `locked_svg` |
| `template_id` | Directory / index key |
| `canvas_format` | e.g. `ppt169` |
| `pages[]` | `stem`, `file`, `role`, `viewBox`, `sha256`, `placeholders[]`, `workspaces[]` |

---

## 4. Runtime Consumption

Locked SVG templates are consumed by contract, not by prompt context.

| Runtime actor | Reads |
|---|---|
| Strategist | `design_spec.md`, `template_contract.json` |
| Executor | `spec_lock.md`, `template_contract.json` |
| `svg_template.py apply` | Template SVG file, fill JSON, workspace fragments |

**Forbidden - runtime SVG visibility**:

- Do not ask the agent to read template SVG files during PPT generation.
- Do not batch-read layout SVGs for locked templates.
- Do not infer icons, images, or decorative details from template SVGs.

---

## 5. Validation

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py "skills/ppt-master/templates/layouts/<template_id>" --template-mode --format <canvas_format>
```

**Validation**: zero errors before registration or handoff. The checker
verifies roster consistency, contract presence, SHA consistency, and workspace
geometry.

---

## Template_Designer Phase Complete

```markdown
## Template_Designer Phase Complete

- [x] SVG metadata inspected via `svg_template.py inspect`
- [x] Locked template created via `svg_template.py create`
- [x] `template_contract.json` generated with `engine: locked_svg`
- [x] `design_spec.md` points to the contract
- [x] Template validation passed with zero errors
- [ ] **Next**: Use the explicit template directory path in SKILL.md Step 3
```
