---
description: Generate a new PPT layout template from existing SVG reference assets only
---

# Create New Template Workflow

> **Role invoked**: [Template_Designer](../references/template-designer.md)

Generate a complete set of reusable PPT layout templates for the **global template library**.

> This workflow is for **library asset creation**, not project-level one-off customization. The output must be reusable by future PPT projects and discoverable from `templates/layouts/layouts_index.json`.

## Process Overview

```
SVG Reference Intake & Analysis -> Fact-Based Brief Proposal -> User Confirmation Gate -> Create Directory + Invoke Template_Designer -> Validate Assets -> Register Index -> Output
```

The first three steps derive the brief from facts, not guesses. **No final template directory may be created and no template SVG / `design_spec.md` may be written until `[TEMPLATE_BRIEF_CONFIRMED]` is emitted in Step 3.**

---

## Step 1: Reference Intake & Analysis

Accept SVG reference sources only. This step produces analysis artefacts only — it does **not** create the final template directory, write `design_spec.md`, or touch `layouts_index.json`.

### Accepted input

| Type | What the user supplied | Tool / read path | Replication modes available |
|------|-------------------------|------------------|------------------------------|
| **SVG reference** | `projects/<x>/svg_output/`, `templates/layouts/<existing>`, a folder containing `*.svg`, or an explicit list of `.svg` files | `ls` / file list + `Read` every `*.svg`; plus `design_spec.md` / `spec_lock.md` if present | `standard` / `fidelity` (AI visual clustering) / `mirror` (direct 1:1 copy) |

Reject every non-SVG source upfront:

- `.pptx`, `.pdf`, `.docx`, `.xlsx`, images / screenshots, URLs, and verbal-only descriptions are not valid inputs for this workflow.
- Do not run `pptx_template_import.py` or any source-to-SVG conversion helper inside this workflow.
- If the user supplies a non-SVG source, stop before Step 1 analysis and ask for exported SVG files or a directory containing SVG files.
- If the supplied directory contains no `*.svg`, stop and ask for SVG input.

SVG-specific caveats:

- **mirror** — direct 1:1 copy. The source SVGs are treated as already self-contained pages. Page-type for the `<NNN>_<page_type>.svg` filename is read from the source filename when it follows the PPT Master naming convention (`01_cover.svg` → `cover`, `03a_content_two_col.svg` → `content`); fall back to `content` otherwise.
- **fidelity** — clustering relies on the AI's visual judgement of the SVGs. Variant count and grouping are more subjective and may need iteration. If the input is already a PPT Master template (`templates/layouts/<existing>`), parse the existing variant filenames (`03a_content_two_col` etc.) as authoritative cluster hints rather than re-clustering visually.

### SVG reference analysis

`ls` the directory and `Read` every `*.svg` to extract:

- canvas size (`viewBox` on the root `<svg>`)
- recurring colors (`fill` / `stroke` values; identify the dominant 2–4 hex codes as candidate theme colors)
- fonts (`font-family` attributes on `<text>`)
- placeholder usage (existing `{{...}}` strings, if any)
- structural decoration (recurring `<rect>` bars, `<path>` motifs, embedded `<image>` references)
- image asset dependencies (`<image href="...">`; resolve relative paths against the source SVG location)
- source order and page-type hints from filenames

If a `design_spec.md` or `spec_lock.md` accompanies the SVGs, `Read` it too — it is a higher-confidence source than re-deriving from the SVG alone. Record the factual fields in your own analysis notes (no actual file written) so Step 2 can label them `[fact]`.

**Hard read gate**:

- The agent MUST finish reading every supplied `*.svg` file before moving on to Step 2
- The agent MUST list the read SVG filenames inside the Step 2 brief proposal as proof of the gate

Do **not** treat the source SVGs as direct final template assets in `standard` / `fidelity` mode — Step 4 reconstructs them as a clean, maintainable PPT Master template package. In `mirror` mode, the source SVGs are copied verbatim as described in Step 4.

---

## Step 2: Fact-Based Brief Proposal

Compose a single message that surfaces every Required brief item to the user, **labelling each value's provenance**:

- **`[fact]`** — extracted from Step 1 SVG analysis (e.g. theme color from SVG `fill` / `stroke`, canvas from root `viewBox`)
- **`[suggested]`** — AI-inferred from SVG analysis or context (e.g. tone summary, applicable scenarios)
- **`[decision]`** — pure user choice, no analysis substitute (e.g. `template_id`, `replication mode`, `category`)

Items to surface:

| Item | Required | Provenance |
|------|----------|--------------------------|
| New template ID | Yes | `[decision]` — user chooses ASCII slug; if Chinese brand name, must be filesystem-safe and match `layouts_index.json` exactly |
| Template display name | Yes | `[decision]` (may be `[suggested]` from source directory name or companion `design_spec.md`) |
| Category | Yes | `[decision]` — one of `brand` / `general` / `scenario` / `government` / `special` |
| Applicable scenarios | Yes | `[suggested]` from analysis; user confirms |
| Tone summary | Yes | `[suggested]` from analysis (e.g. `Modern, restrained, data-driven`) |
| Theme mode | Yes | `[fact]` from SVG backgrounds / dominant fills; `[decision]` if SVGs conflict or do not establish it |
| Canvas format | Yes | `[fact]` from SVG `viewBox`; `[decision]` if supplied SVGs use mixed or unsupported viewBoxes |
| Replication mode | Yes | `[decision]` — `standard`, `fidelity`, and `mirror` are available for SVG input (see Step 1 caveats) |
| Visual fidelity for fixed pages | Yes for `standard` / `fidelity`; **N/A for `mirror`** (mirror is implicitly literal) | `[decision]` — `literal` (preserve original geometry / decoration / sprite crops as-is; for cover / chapter / ending especially) or `adapted` (use the reference for tone/structure but allow design evolution). Different page types may take different settings |
| Reference source | Optional | `[fact]` — supplied SVG file list or source directory |
| Theme color | Optional | `[fact]` from dominant SVG `fill` / `stroke` or companion `design_spec.md`; `[decision]` if absent / conflicting |
| Fonts | Optional | `[fact]` from SVG `font-family` or companion `design_spec.md`; `[decision]` if absent |
| Design style | Optional | `[suggested]` from analysis |
| Assets list | Optional | `[fact]` from SVG `<image href="...">` dependencies and co-located assets; user confirms which to bundle |
| Keywords | Yes | `[suggested]` from analysis (3–5 short tags); user confirms |

Also include in this message:

- the exact `*.svg` filenames you read (proof of the hard read gate)
- a one-line summary of the shared visual structure, variant clusters, and filename-derived page-type hints you extracted

The user replies with corrections, additions, or "all good".

> **Persist the brief into `design_spec.md`**. When the Template_Designer writes `design_spec.md` in Step 4, declare a YAML frontmatter block at the top with the confirmed brief (`template_id`, `category`, `summary`, `keywords`, `primary_color`, `canvas_format`, `replication_mode`, etc.). `register_template.py` reads this in Step 6, so the brief flows directly into the index without the AI re-deriving it from prose. See Step 6 for the recommended frontmatter shape.

---

## Step 3: User Confirmation Gate

**MANDATORY interactive gate — this step BLOCKS Steps 4 onward.**

1. Echo back the finalized brief (post-corrections) in a single message
2. Emit the marker `[TEMPLATE_BRIEF_CONFIRMED]` on its own line

Skipping this gate — including silently inferring values from the reference source, opened IDE file, or prior conversation — is a workflow violation. Even if the user said "用这些 SVG 做模板" upfront, you MUST still surface Step 2 with provenance labels and obtain explicit confirmation here. The reference source informs the brief; it does not substitute for it.

**Required outcome of Step 3** (all must be true before emitting `[TEMPLATE_BRIEF_CONFIRMED]`):

- [ ] User has been shown every Required item in Step 2 with provenance labels
- [ ] User has replied with values or explicit acceptance of suggested defaults
- [ ] The template is clearly positioned as a **global library template**
- [ ] The canvas format is fixed before SVG generation
- [ ] Replication mode is consistent with SVG-only input (`standard` / `fidelity` / `mirror` all allowed for SVG, with the Step 1 caveats noted)
- [ ] The template metadata is complete enough to register into `layouts_index.json`
- [ ] Marker `[TEMPLATE_BRIEF_CONFIRMED]` emitted on its own line after the echoed brief

Step 4 MUST NOT run until `[TEMPLATE_BRIEF_CONFIRMED]` has been emitted in the current conversation.

---

## Step 4: Create Template Directory + Invoke Template_Designer

> **Precondition**: `[TEMPLATE_BRIEF_CONFIRMED]` was emitted in Step 3. If not, return to Step 3.

Create the final template directory:

```bash
mkdir -p "skills/ppt-master/templates/layouts/<template_id>"
```

> **Output location**: Global templates go to `skills/ppt-master/templates/layouts/`; project templates go to `projects/<project>/templates/`
>
> The generated directory name must match the final template ID used in `layouts_index.json`.

**Switch to the Template_Designer role** and generate per role definition. The role input is the finalized brief from Step 3 plus the analysis bundle from Step 1.

Pass the following internal package to the role:

- finalized brief from Step 3
- complete SVG file list and source order
- any companion `design_spec.md` / `spec_lock.md`
- image asset dependency map from SVG `<image href="...">`
- Step 1 analysis notes

The role uses the analysis bundle to anchor objective facts such as theme colors, fonts, reusable backgrounds, and common branding assets, then rebuilds the final SVG templates in a simplified, maintainable form.

**Apply the visual-fidelity decision from Step 3**: pages marked `literal` (typically cover / chapter / ending) must reproduce the reference's geometry, decoration, and sprite-sheet crops as-is — "simplified, maintainable form" applies only to genuinely redundant structure, not to load-bearing layout. Pages marked `adapted` may use the reference for tone and structural rhythm but evolve the design.

**Sprite-sheet preservation (do NOT simplify away)**: exported SVG assets are often sprite sheets — a single tall/large image referenced from multiple slides, each cropping a different region via nested `<svg ... viewBox="...">` wrappers around `<image width="1" height="1">`. This nesting is **load-bearing geometry**, not redundant structure. When rebuilding, preserve the exact `viewBox` crop and the outer `<svg>` placement for every image; do not flatten to a single `<image>` with direct `x/y/width/height`. Verify by sampling: if any asset's pixel dimensions don't match the on-page display aspect, it is a sprite and the wrapper must stay.

**Mirror-mode override**: when `Replication mode: mirror`, this step is a **verbatim copy** rather than a reconstruction. The Template_Designer role:

1. **Copies the source pages** into the template directory **without any modification** — no placeholder insertion, no decorative simplification, no chrome/content reorganization. The SVG that ships in the template is byte-for-byte the source page (modulo filename change and asset path rewrites).
   - Source is each supplied `*.svg` file.
2. **Renames each file** using the source-order-first convention `<NNN>_<page_type>.svg`, where `<NNN>` is the source-order index zero-padded to 3 digits and `<page_type>` is typically `cover` / `toc` / `chapter` / `content` / `ending` (fall back to `content` when the type cannot be confidently classified). Examples: `001_cover.svg`, `002_toc.svg`, `003_content.svg`, ..., `050_ending.svg`.
   - Derive `<page_type>` from the source filename when it follows the PPT Master convention (`01_cover.svg` → `cover`, `03a_content_two_col.svg` → `content`); otherwise infer from page content or fall back to `content`.
3. **Copies bundled assets** into the template directory and rewrites the `<image href="...">` paths inside each copied SVG to point at the local copies. Asset filenames may be renamed to semantic names (`brand_emblem.png` instead of `image3.png`) when it improves readability — but the rewrite must be consistent across every page.
   - Resolve relative paths in source `<image href="...">` against the source SVG location and copy each unique asset; if the source already follows PPT Master conventions (assets co-located with SVGs in the same directory), copy the whole asset set and then rewrite paths.
4. Writes `design_spec.md` per [template-designer.md](../references/template-designer.md) §1 — the **§V Page Roster description per page is the load-bearing artifact** because mirror has no placeholders to advertise the per-page contract; downstream Strategist selects pages purely from these descriptions.

Mirror mode does **not** invoke the "reconstruct into clean SVG" pathway. The sprite-sheet preservation rule still applies (because the source SVGs may already contain the original sprite wrappers — do not flatten them when copying).

**Expected outputs from this step** (full spec → [template-designer.md](../references/template-designer.md)):

1. `design_spec.md` — **personality only**. Required sections: Template Overview, Color Scheme, Signature Design Elements, Page Roster (matching the actual SVG files on disk). Skip Typography / Assets / Placeholder Overrides when they would just restate defaults. Declare brief frontmatter for `register_template.py`. **Do not** restate generic SVG constraints, layout pattern libraries, font-size ratio bands, the canonical placeholder table, or content methodology — those are sourced from `shared-standards.md` / `design_spec_reference.md` / `strategist.md` and are already in the downstream reader's context. Full scope rule and skeleton: [template-designer.md §1](../references/template-designer.md#1-must-generate-design_specmd).
2. Page roster — see [Page Roster](../references/template-designer.md#page-roster) for `standard` / `fidelity` / `mirror` mode rosters, variant naming, and TOC handling
3. Placeholder vocabulary — pages should adopt the conventional names (`{{TITLE}}`, `{{CONTENT_AREA}}`, ...) when they fit. Full reference: [Placeholder Reference](../references/template-designer.md#4-placeholder-reference-canonical-convention-overridable-per-template). When a template style legitimately needs different vocabulary (consulting → `{{KEY_MESSAGE}}`, branded cover → `{{BRAND_LOGO}}`), declare a `placeholders:` block in `design_spec.md` frontmatter so the registrar and quality checker treat it as the template's authoritative contract. **Avoid** one-off indexed families such as `{{CHAPTER_01_TITLE}}` — use the indexed TOC pattern instead.
4. Template assets (optional) — Logos / PNG / JPG / reference SVG bundled with the template package

---

## Step 5: Validate Template Assets

```bash
ls -la "skills/ppt-master/templates/layouts/<template_id>"
```

Run SVG validation on the template directory:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_quality_checker.py "skills/ppt-master/templates/layouts/<template_id>" --template-mode --format <canvas_format>
```

`--template-mode` makes the checker:

- glob `*.svg` in the template directory directly (templates do not live under `svg_output/`)
- skip `spec_lock.md` drift checks (templates do not ship a spec_lock)
- enforce roster ↔ `design_spec.md` consistency as **errors** (orphan files / missing files break `layouts_index.json`)
- emit advisory **warnings** when a page lacks a conventional placeholder — these are hints, not failures. Declare a `placeholders:` block in `design_spec.md` frontmatter to silence them when your template intentionally uses a different vocabulary

**Checklist**:

- [ ] `design_spec.md` follows the personality-only skeleton (Overview / Color / Signature / Page Roster); generic constraints (SVG rules, pattern libraries, ratio bands, canonical placeholder table) are NOT restated. §V Page Roster lists every emitted page
- [ ] Every page declared in `design_spec.md §V Page Roster` exists as an SVG file in the template directory (and vice versa — no orphan files)
- [ ] Variant filenames follow the letter-suffix convention (e.g. `03a_content_two_col.svg`); variants typically reuse the parent type's placeholder set unless the spec frontmatter declares otherwise
- [ ] If TOC exists, placeholder pattern uses the canonical indexed form
- [ ] SVG viewBox matches the chosen canvas format (for `ppt169`: `0 0 1280 720`)
- [ ] Placeholder names follow the canonical convention where applicable; templates with intentionally different vocabularies (e.g. `{{KEY_MESSAGE}}` instead of `{{PAGE_TITLE}}`) should declare a `placeholders:` frontmatter block to silence advisory warnings
- [ ] Asset files referenced by SVGs actually exist in the template package
- [ ] For `fidelity` mode: every sprite-sheet asset retains its nested `<svg viewBox=...>` crop wrapper; no image whose file aspect differs from its on-page aspect was flattened to a bare `<image>`
- [ ] For `mirror` mode: file count equals the source SVG count; filenames follow the `<NNN>_<page_type>.svg` convention; **no `{{...}}` placeholder strings appear in any copied SVG** (`grep -l "{{" templates/layouts/<id>/*.svg` should return nothing — if the source SVGs themselves contain placeholders, the user should be in `standard` mode, not `mirror`); §V Page Roster in `design_spec.md` lists every emitted file with a one-line description of what the page contains and what content slot it suits

This step is a **hard gate**. Do not register the template into the library index until validation passes.

---

## Step 6: Register Template in Library Index

Run the unified registrar; it derives the `layouts_index.json` entry and refreshes the `README.md` Quick Index from `design_spec.md` (frontmatter when present, prose fallback otherwise) plus the actual SVG file list:

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/register_template.py <template_id>
```

Outputs:

- updates `skills/ppt-master/templates/layouts/layouts_index.json` — the flat `template_id → { summary, keywords }` map
- refreshes the auto-managed Quick Index inside `skills/ppt-master/templates/layouts/README.md` (the surrounding category sections stay hand-edited)
- prints a "Template Creation Complete" card you can use directly for Step 7

The completion card's file roster is collected by globbing `*.svg` in the template directory, so `fidelity`-mode templates that include variant pages such as `03a_content_two_col` are listed automatically.

`layouts_index.json` is a **discovery index** — it lets the AI answer "what templates are available?" by listing names and paths. It is **not** consulted to trigger Step 4. Step 4 triggers on an explicit directory path supplied by the user, regardless of whether that path is registered. A template directory that has not been run through `register_template.py` still works fine when the user gives its path; it just won't appear in discovery listings.

> **Recommended for new templates**: declare a YAML frontmatter block at the top of `design_spec.md`. The registrar prefers it over the §I table and lets you set `category`, `keywords`, `summary`, etc. without relying on prose extraction:
>
> ```yaml
> ---
> template_id: my_template
> category: brand            # brand | general | scenario | government | special
> summary: Strategic consulting, executive briefings, ...
> keywords: [tag1, tag2, tag3]
> primary_color: "#005587"
> canvas_format: ppt169
> replication_mode: standard  # standard | fidelity | mirror
> # Optional: per-page placeholder overrides. Templates that legitimately
> # use a different vocabulary (e.g. consulting decks with {{KEY_MESSAGE}}
> # in place of {{PAGE_TITLE}}, or content variants with bespoke slots)
> # should declare them here so svg_quality_checker --template-mode does
> # not flag them as conventional-placeholder gaps.
> # Mirror-mode templates do not need this field — they have no placeholders.
> placeholders:
>   01_cover: ["{{TITLE}}", "{{SUBTITLE}}", "{{BRAND_LOGO}}"]
>   03_content: ["{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
>   03a_content_dual_col: []   # silences hints for this variant entirely
> ---
> ```

> To rebuild every entry at once (e.g. after editing many specs), run:
>
> ```bash
> .\.venv\Scripts\python.exe skills/ppt-master/scripts/register_template.py --rebuild-all
> ```

If you need to update the categorized sections lower in `README.md` (Brand Style Templates / General Style Templates / etc.), edit those by hand — the registrar deliberately leaves them alone so curated descriptions are preserved.

---

## Step 7: Output Confirmation

`register_template.py` already printed a "Template Creation Complete" card during Step 6 — copy it verbatim into the conversation. The card includes the template name, path, category, primary color, index status, and the full SVG file roster (auto-collected from disk, so `fidelity`-mode variant pages and TOC pages are listed correctly without manual editing).

For a standard-mode template the card looks like:

```markdown
## Template Creation Complete

**Template Name**: <template_id> (<display_name>)
**Template Path**: `templates/layouts/<template_id>/`
**Category**: <category>
**Primary Color**: <hex>
**Index Registration**: Done

### Files Included

| File | Status |
|------|--------|
| `01_cover.svg` | Done |
| `02_chapter.svg` | Done |
| `02_toc.svg` | Done |
| `03_content.svg` | Done |
| `04_ending.svg` | Done |
```

---

## Color Scheme Quick Reference

| Style | Primary Color | Use Cases |
|-------|---------------|-----------|
| Tech Blue | `#004098` | Certification, evaluation |
| McKinsey | `#005587` | Strategic consulting |
| Government Blue | `#003366` | Government projects |
| Business Gray | `#2C3E50` | General business |

---

## Notes

1. **SVG technical constraints**: See [shared-standards.md](../references/shared-standards.md) — do not restate them in the template's `design_spec.md`
2. **Color consistency**: All SVG files must use the same color scheme as `design_spec.md §II Color Scheme`
3. **Placeholder convention**: `{{}}` format only; default names listed in [Placeholder Reference](../references/template-designer.md#4-placeholder-reference-canonical-convention-overridable-per-template). Override per template via `placeholders:` frontmatter when needed.
4. **Discovery requirement**: A template directory is only discoverable after `register_template.py` has been run against it (Step 6)

> **Full role specification**: [template-designer.md](../references/template-designer.md)
