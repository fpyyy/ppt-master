> See [`../workflows/create-template.md`](../workflows/create-template.md) for the locked SVG template workflow.

# Role: Template_Designer

Role definition for creating reusable locked SVG templates from an existing SVG
directory. Trigger only through the `/create-template` workflow.

## Core Mission

Convert prepared five-page SVG directories into a locked template package. The
role does not redesign or read raw SVG source. Visual checks are limited to
parity after validation-driven corrections.

---

## 1. Input Contract

| Input | Requirement |
|---|---|
| Source directory | Directory containing exactly `title.svg`, `toc.svg`, `chapter.svg`, `content.svg`, `ending.svg` |
| Confirmation | Confirmed template ID and canvas format |
| Inspection output | Output from `svg_template.py inspect` |
| Sanitized XML | Output from `svg_llm_xml.py`; raw paths and base64 images omitted |

**Hard rule**: Do not read SVG files directly. They may contain base64 images.
Use only `svg_template.py inspect` output and sanitized XML for metadata.

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
| Required files | `title.svg`, `toc.svg`, `chapter.svg`, `content.svg`, `ending.svg` |
| Replaceable text | Use custom `{{...}}` placeholders, e.g. `{{PPTTitle}}` |
| Content workspace | Auto-inferred by `svg_template.py create`; no manual marking required |
| Non-content pages | Placeholder replacement only; no workspace fragments |
| Canvas | All pages in a template use one root `viewBox` |
| Embedded images | Allowed, but never surfaced in prompt context |
| Non-image clipping | Follow [`create-template`](../workflows/create-template.md) §5.1; preserve visual crop or stop |

**Hard rule**: Only `content.svg` may have a workspace in
`template_contract.json`. The script infers `main` automatically when no
explicit marker exists.

**Forbidden - validation-only edits**:

- Do not mechanically remove `clip-path` from groups to satisfy the checker.
- Do not refresh contract SHA values after a visual change.
- Do not alter embedded-image crops unless the final template preserves the
  same visible region.
- Do not read `debug/content_viewbox.svg` source into prompt context; it is a
  human visual artifact and may contain data URIs.

---

## 3. Generated Files

Run `svg_template.py create`. It writes the complete template package.

| File | Notes |
|---|---|
| `*.svg` | Copied from the source directory; missing root `viewBox` is inferred from `width`/`height` |
| `llm_xml/*.xml` | Sanitized XML for theme and color inspection |
| `debug/content_viewbox.svg` | Visual overlay for `content.svg` root `viewBox` and workspace boxes |
| `design_spec.md` | Minimal runtime contract pointer and page roster |
| `template_contract.json` | Machine-readable contract for runtime use |

`design_spec.md` frontmatter MUST include:

```yaml
template_engine: locked_svg
template_contract: template_contract.json
placeholder_style: custom
```

**Forbidden - decorative metadata**:

- Do not ask for display name, category, summary, keywords, or primary color.
- Do not save those fields in newly generated locked template specs.
- Use `template_id` as the only human-facing template name.

`template_contract.json` MUST include:

| Field | Notes |
|---|---|
| `schema_version` | `1` |
| `engine` | `locked_svg` |
| `template_id` | Directory / index key |
| `canvas_format` | e.g. `ppt169` |
| `pages[]` | `stem`, `file`, `role`, `viewBox`, `sha256`, `placeholders[]`, `workspaces[]` |
| `placeholders[].text_fit` | Estimated locked-page length budget for replacement text |
| `workspaces[].source` | `auto-heuristic`, `auto-labelled`, or `declared` |

---

## 4. Runtime Consumption

Locked SVG templates are consumed by contract, not by prompt context.

| Runtime actor | Reads |
|---|---|
| Strategist | `design_spec.md`, `template_contract.json` |
| Executor | `spec_lock.md`, `template_contract.json` |
| `svg_template.py apply` | Template SVG file, fill JSON, content workspace fragment |

**Forbidden - runtime SVG visibility**:

- Do not ask the agent to read template SVG files during PPT generation.
- Do not batch-read layout SVGs for locked templates.
- Do not infer icons, images, or decorative details from template SVGs.
- Do not inject workspace fragments into `title`, `toc`, `chapter`, or `ending`.

---

## 5. Validation

Run:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py "skills/ppt-master/templates/layouts/<template_id>" --template-mode --format <canvas_format>
```

**Validation**: zero errors before registration or handoff. The checker
verifies the fixed five-file roster, contract presence, SHA consistency,
workspace geometry, and non-content placeholder-only behavior.

---

## Template_Designer Phase Complete

```markdown
## Template_Designer Phase Complete

- [x] SVG metadata inspected via `svg_template.py inspect`
- [x] Sanitized XML generated via `svg_llm_xml.py`
- [x] Locked template created via `svg_template.py create`
- [x] Content viewBox overlay generated via `svg_template.py visualize-content`
- [x] `template_contract.json` generated with `engine: locked_svg`
- [x] `design_spec.md` points to the contract
- [x] Template validation passed with zero errors
- [ ] **Next**: Use the explicit template directory path in SKILL.md Step 3
```
