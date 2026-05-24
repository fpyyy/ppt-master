> See [`image-base.md`](./image-base.md) for the common framework. For the web sourcing path, see [`image-searcher.md`](./image-searcher.md).

# Image_Generator Reference Manual

Role definition for the **AI image generation path**: convert each `Acquire Via: ai` row into an optimized prompt, generate the image, and save it to `project/images/`.

**Trigger**: resource list rows with `Acquire Via: ai`. The role is loaded only when at least one such row exists.

---

## 1. Unified Prompt Structure

### 1.1 Standard Output Format

Every image must be emitted into `image_prompts.md` in the following block format:

```markdown
### Image N: {filename}

| Attribute | Value |
| --------- | ----- |
| Purpose   | {which page / what function} |
| Type      | {Background / Illustration / Photography / Diagram / Decorative} |
| Dimensions | {width}x{height} ({aspect ratio}) |
| Original description | {Reference field from the resource list} |

**Prompt**:
{subject description}, {global scientific schematic style anchor}, {neutral paper palette directive}, {composition directive}, {avoid directive}

**Alt Text**:
> {Description for accessibility and image captions}
```

### 1.2 Prompt Components

| Component | Description | Example |
|-----------|-------------|---------|
| Subject description | Core content | `Abstract geometric shapes`, `Team collaboration scene` |
| Style directive | Global AI-image visual style | `paper-style scientific schematic illustration, clean vector-style, flat, non-photorealistic` |
| Color directive | Neutral paper-figure palette, not template colors | `white or light neutral background, muted scientific accent colors only when semantically useful` |
| Composition directive | Layout ratio | `16:9 aspect ratio`, `centered composition` |
| Avoid directive | Global negative style constraints | `avoid photorealistic skin texture, realistic portrait details, 3D rendering, cinematic lighting, commercial poster styling` |

### 1.3 Global AI Visual Style

**Hard rule**: Every `Acquire Via: ai` prompt MUST use the same visual style, regardless of template, deck style, industry, or `design_spec.md` theme.

| Prompt part | Required wording / behavior |
|---|---|
| Style anchor | `paper-style scientific schematic illustration; clean vector-style; flat; non-photorealistic; academic figure aesthetic; suitable for a computer vision research paper; minimal; thin lines; soft gradients; clear visual hierarchy` |
| Avoid list | `avoid photorealistic skin texture, realistic portrait details, 3D rendering, cinematic lighting, commercial poster styling` |
| Human faces | Use simplified silhouettes, outlines, masks, landmarks, or abstract facial regions; do not request realistic portraits or realistic skin. |
| Scientific tone | Prefer paper-figure diagram language over commercial / poster / marketing language. |

**Forbidden — style inheritance**:
- Do not derive AI-image style from the selected template.
- Do not use `design_spec.md` visual theme, brand tone, industry palette, or locked template style to alter the AI-image style anchor.
- Do not request photorealistic photography, 3D / isometric rendering, cinematic lighting, commercial poster composition, or realistic portrait details for `Acquire Via: ai`.

### 1.4 Color Non-Inheritance Method

**Hard rule**: Do not constrain AI-generated images to the template's theme colors or HEX values.

| Source | AI prompt behavior |
|---|---|
| Locked template colors | Do not include them in image prompts. |
| `design_spec.md` theme palette | Do not include it in image prompts. |
| User explicitly asks for an image color | Include only that user-requested color. |
| Scientific semantic color | Allowed when it clarifies meaning, e.g. muted red/blue heatmap, subtle green signal line. |

**Default palette directive**: `neutral paper-figure palette on white or light neutral background, muted scientific accents only where semantically useful`.

**Forbidden — template color leakage**:
- Do not write prompt fragments like `BIT green #005C30`, `brand blue`, `matching the template palette`, or `color grading matching {color scheme}` unless the user explicitly requested that color for the AI image itself.
- Do not make multi-image coherence depend on template colors.

### 1.5 Canvas Format & Aspect Ratio

| Canvas Format | Background Aspect Ratio | Recommended Resolution |
|--------------|------------------------|----------------------|
| PPT 16:9 | 16:9 | 1920x1080 or 2560x1440 |
| PPT 4:3 | 4:3 | 1600x1200 |
| Xiaohongshu (RED) | 3:4 | 1242x1660 |
| WeChat Moments | 1:1 | 1080x1080 |
| Story | 9:16 | 1080x1920 |

> Supported aspect ratios: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9` (Gemini also supports `1:4`, `1:8`, `4:1`, `8:1`)

### 1.6 Multi-Image Coherence Strategy

When generating multiple images for a single deck, visual coherence is critical. Use a **Deck Style Anchor** — a shared prefix of 15-25 words prepended to every image prompt.

**Construction**: Use the global style anchor (§1.3) + neutral paper palette directive (§1.4) + avoid directive (§1.3).

**Example**:
```
Deck Style Anchor:
"paper-style scientific schematic illustration, clean vector-style, flat, non-photorealistic, academic figure aesthetic, thin lines, soft gradients, clear visual hierarchy"

Image 1 prompt: [Deck Style Anchor], abstract technology network showing connected nodes...
Image 2 prompt: [Deck Style Anchor], team of professionals collaborating at a desk...
Image 3 prompt: [Deck Style Anchor], growth chart with upward trending line...
```

**Exception**: Background images may add `background`, `backdrop`, and `negative space for text overlay`, but they still keep the global scientific schematic style and neutral paper palette.

**Hard rule - no text-fill handoff**: Only Background images may reserve negative space for later slide text. Diagram, Illustration, Photography, and Decorative Pattern rows MUST NOT ask for blank boxes, empty nodes, unlabeled frameworks, or areas intended for Executor to fill with semantic labels.

**Rule**: Define the Deck Style Anchor once in the prompt document header (Section 4), then reference it in every individual prompt.

---

## 2. Image Type Classification & Handling

### Type Determination Flow

1. Full-page / large-area backdrop → **Background** (2.1)
2. Real scenes / people / products → **Photography** (2.2)
3. Flat / illustration / cartoon style → **Illustration** (2.3)
4. Process / architecture / relationships → **Diagram** (2.4)
5. Partial decoration / texture → **Decorative Pattern** (2.5)

### 2.1 Background

**Identifying characteristics**: Full-page background for covers or chapter pages; must support text overlay

| Key Point | Description |
|-----------|-------------|
| Emphasize background nature | Add `background`, `backdrop` |
| Reserve text area | `negative space in center for text overlay` |
| Avoid strong subjects | Use abstract, gradient, geometric elements |
| Low-contrast details | `subtle`, `soft`, `muted` |

**Template**: `Abstract {theme element} background, paper-style scientific schematic illustration, clean vector-style, flat, non-photorealistic, neutral paper-figure palette on white or light neutral background, subtle soft gradients, clean negative space for text overlay, {aspect ratio} aspect ratio, avoid photorealistic skin texture, realistic portrait details, 3D rendering, cinematic lighting, commercial poster styling`

### 2.2 Photography

**Identifying characteristics**: Real scenes, people, products, architecture requested through `Acquire Via: ai`

| Key Point | Description |
|-----------|-------------|
| Convert to schematic | Use paper-style schematic illustration, not photography |
| People handling | Use simplified silhouettes, facial landmarks, or abstract figures |
| Background handling | Use white or light neutral paper background |
| Avoid realism | Do not request realistic skin, portrait detail, lens effects, or cinematic light |

**Template**: `{subject description}, paper-style scientific schematic illustration, clean vector-style, flat, non-photorealistic, academic figure aesthetic, white or light neutral paper background, minimal thin lines, soft gradients, clear visual hierarchy, avoid photorealistic skin texture, realistic portrait details, 3D rendering, cinematic lighting, commercial poster styling`

### 2.3 Illustration

**Identifying characteristics**: Flat design, vector style, cartoon, concept diagrams

| Key Point | Description |
|-----------|-------------|
| Specify style | `paper-style scientific schematic illustration`, `clean vector-style`, `flat`, `non-photorealistic` |
| Simplify details | `simplified`, `clean lines`, `minimal details` |
| Palette | Neutral paper-figure palette; do not use template colors |
| Background choice | `white background` or light neutral background |

**Template**: `{subject description}, paper-style scientific schematic illustration, clean vector-style, flat, non-photorealistic, academic figure aesthetic, suitable for a computer vision research paper, minimal thin lines, soft gradients, clear visual hierarchy, white or light neutral paper background, avoid photorealistic skin texture, realistic portrait details, 3D rendering, cinematic lighting, commercial poster styling`

### 2.4 Diagram

**Identifying characteristics**: Flowcharts, architecture diagrams, concept relationship maps, data visualizations

| Key Point | Description |
|-----------|-------------|
| Clear structure | `clear structure`, `organized layout`, `logical flow` |
| Connection representation | `arrows indicating flow`, `connecting lines` |
| Academic / professional feel | `academic figure aesthetic`, `suitable for a computer vision research paper` |
| Light background | `white background` or `light gray background` |
| Final visible text | Include all node labels, legends, callouts, step names, and relationship words in the prompt |

**Hard rule - raster-final diagrams**: A generated diagram is the final artwork. The prompt MUST request a complete labeled diagram, not a background. Do not create or accept a prompt whose plan depends on SVG/PPT text being added later.

| Prompt must include | Prompt must not include |
|---|---|
| Final visible label text from the source or design spec | `blank`, `unlabeled`, `empty boxes`, `placeholder text`, `space for labels` |
| Connection words / arrow meanings when they appear on the slide | `without text`, `text-free`, `labels added later` |
| Legible typography and spelling requirements | `background framework`, `diagram base`, `template to fill` |

**Template**: `{diagram type} diagram showing {content description}, with final readable labels: {label list}, {component description} connected by {connection method}, paper-style scientific schematic illustration, clean vector-style, flat, non-photorealistic, academic figure aesthetic, suitable for a computer vision research paper, minimal thin lines, soft gradients, clear visual hierarchy, white or light neutral paper background, avoid photorealistic skin texture, realistic portrait details, 3D rendering, cinematic lighting, commercial poster styling`

### 2.5 Decorative Pattern

**Identifying characteristics**: Partial decoration, textures, borders, divider elements

| Key Point | Description |
|-----------|-------------|
| Repeatability | `seamless`, `tileable`, `repeatable` (if needed) |
| Understated support | `subtle`, `understated`, `supporting element` |
| Transparency-friendly | `transparent background` or `isolated element` |
| Small-size readability | Consider legibility at small dimensions |

**Template**: `{pattern type} decorative pattern, paper-style scientific schematic illustration, clean vector-style, flat, non-photorealistic, neutral paper-figure palette, white or light neutral background, minimal thin lines, soft gradients, clear visual hierarchy, suitable for {purpose}, avoid 3D rendering, cinematic lighting, commercial poster styling`

---

## 3. Generation Workflow

### 3.1 Prompt Generation Phase

For each image with `Acquire Via: ai` and `Status: Pending`:

1. **Determine type** → Background / Photography / Illustration / Diagram / Decorative
2. **Understand purpose** → Which page? What function?
3. **Analyze the Reference field** → User's intent description
4. **Apply type-specific key points** → Reference §2's table for that type
5. **Generate optimized prompt** → Use the §1.1 standard output format
6. **Save prompt document** → **Must** write to `project/images/image_prompts.md`

**Per-row Diagram validation**: Before invoking Codex `imagegen`, verify every `Type: Diagram` prompt names the final visible labels. If the row only describes a blank structure, rewrite the prompt to include labels from `design_spec.md`; if labels are unavailable, mark the row `Needs-Manual` and do not generate a blank base image.

> `image_prompts.md` is human-readable; each `### Image N:` block is paste-ready for ChatGPT / Gemini / Midjourney. See §3.2 Offline Manual Mode for the handoff.

### 3.2 Image Generation Phase

> Prerequisite: §3.1 must be complete; `images/image_prompts.md` must exist.

#### Codex Imagegen Path (Default and Only Automated Path)

AI-generated rows use exactly one automated implementation: the Codex `imagegen` skill.

| Trigger | Mode | Mechanism |
|---|---|---|
| `Acquire Via: ai` + `Status: Pending` | Codex `imagegen` | Agent invokes Codex image generation from `image_prompts.md`; final files are placed at `project/images/<filename>` |
| Codex `imagegen` unavailable or fails after retry | Offline Manual Mode | Agent keeps prompts in `image_prompts.md`; user generates externally and places files at `project/images/<filename>` |

**Hard rule**: Do not run `scripts/image_gen.py`, do not check `IMAGE_BACKEND`, and do not present backend choices. Custom image backends are not part of the PPT Master image acquisition path.

**Execution contract**:
- Invoke Codex `imagegen` once per pending ai row using that row's prompt block
- Move or copy the selected output into `project/images/<filename-from-resource-list>`
- Match the requested aspect ratio and dimensions as closely as the Codex tool allows
- Update the row status to `Generated` only after the expected file exists
- For `Type: Diagram`, accept only the single-image contract: complete labeled image in `project/images/<filename>`; never hand off an unlabeled generated base for Executor text overlay

**Generation pacing (mandatory)**:
- Generate one image at a time; wait for file confirmation before the next
- Retry a failed Codex generation once with a targeted prompt adjustment

> All modes share one output contract: file at `project/images/<filename>`. Step 6 SVG references are mode-agnostic.

#### Offline Manual Mode

**Trigger**: Codex `imagegen` is unavailable or fails after one retry.

**Workflow** (no user prompting; system enters this mode automatically):

1. Verify `images/image_prompts.md` was generated in §3.1
2. Set `Status: Needs-Manual` on every affected ai row per [`image-base.md`](./image-base.md) §6
3. Continue to Step 6 — SVG references `images/<filename>` optimistically; Step 7 entry verifies presence
4. Print one consolidated handoff to the user:
   - Filenames awaiting manual generation
   - Pointer to `images/image_prompts.md`: each `### Image N:` block is a paste-ready prompt for ChatGPT / Gemini / Midjourney
   - Target placement: `project/images/<filename>` matching the resource list exactly
   - Resume command: re-run Step 7 once all expected files exist

**User-initiated**: When Strategist Step 4 captured "user wants manual generation" up front, Codex generation is skipped from the start; the workflow above runs as a planned mode.

> The pipeline tolerates `Needs-Manual` rows end-to-end. The user can leave the project, generate offline at their own pace, then resume Step 7.

#### AI-specific Failure Handling (extends image-base.md §6)

If Codex `imagegen` fails:

1. Do not halt. Retry once with a targeted prompt adjustment.
2. If the retry fails or Codex `imagegen` is unavailable, mark the row `Needs-Manual`.
3. Report to user: filename, prompt used, error message.
4. Fall through to **Offline Manual Mode** above.

> If the alternate platform watermarks outputs (e.g. Gemini web), the repository includes `scripts/gemini_watermark_remover.py`.

#### Guardrails (All Modes)

**Hard rule**:

- Do not claim an image is generated without an actual file at the expected path
- `Needs-Manual` is set after a failed attempt OR on entering Offline Manual Mode — not as a way to skip work that automation could have done
- Status transitions are evidence-driven: `Pending` → `Generated` (file exists) or `Pending` → `Needs-Manual` (no automation, or attempt failed once)
- Custom backend routing is forbidden for PPT Master image acquisition: no `IMAGE_BACKEND`, no provider selection, no `scripts/image_gen.py`

---

## 4. Prompt Document Template

Use the following structure when creating `project/images/image_prompts.md`:

```markdown
# Image Generation Prompts

> Project: {project_name}
> Generated: {date}
> AI image color rule: Do not inherit template or design-spec colors; use a neutral paper-figure palette unless the user explicitly requests image colors.
> Deck Style Anchor: {15–25 word prefix per §1.6}

---

## Image List Overview

| # | Filename | Type | Dimensions | Status |
|---|----------|------|-----------|--------|
| 1 | cover_bg.png | Background | 1920x1080 | Pending |

---

## Detailed Prompts

### Image 1: cover_bg.png

| Attribute | Value |
|-----------|-------|
| Purpose | Cover background |
| Type | Background |
| Dimensions | 1920x1080 (16:9) |
| Original description | Modern tech abstract background |

**Prompt**:
[Deck Style Anchor], abstract technical background with flowing signal lines, neutral paper-figure palette on white or light neutral background, no template HEX colors...

**Alt Text**:
> Scientific schematic background with flowing signal lines and a neutral paper-figure style

---

## Usage Instructions

1. Copy the "Prompt" above into an AI image generation tool
2. Recommended platforms: gpt-image-2 / Midjourney / DALL-E 3 / Gemini / Stable Diffusion
3. Rename generated images to the corresponding filenames
4. Place in the `images/` directory
```

---

## 5. Common Issues

### Default Inference When No `Reference` Provided

| Purpose | Default Inference |
|---------|------------------|
| Cover background | Abstract gradient background, reserve central text area |
| Chapter page background | Clean geometric pattern, monochrome focus |
| Team introduction page | Team collaboration scene illustration (flat style) |
| Data display page | Clean geometric pattern or solid color background |
| Product showcase | Product photography style, white or gradient background |

### When Images Are Unsatisfactory

Diagnose the problem category and apply a targeted prompt fix:

| Problem | Diagnosis | Prompt Adjustment |
|---------|-----------|-------------------|
| Wrong style | Image looks photorealistic, 3D-rendered, cinematic, or poster-like | Strengthen style directive with the full global style anchor and avoid list from §1.3 |
| Wrong colors | Image inherited template or brand colors | Remove template / design-spec HEX codes; use neutral paper-figure palette |
| Wrong composition | Subject is off-center or layout doesn't fit the slide | Adjust composition directive: add `centered composition`, `rule of thirds`, or `wide negative space on left` |
| Wrong subject | Image depicts something different from what was described | Rewrite subject description with more specificity and concrete details |
| Low quality | Image is blurry, cluttered, or visually ambiguous | Add `minimal thin lines, soft gradients, clear visual hierarchy, academic figure aesthetic` |

**Variant workflow**:
1. Keep the original prompt as "Variant A" in `image_prompts.md`
2. Create modified prompt as "Variant B" with targeted fixes from the table above
3. If needed, create "Variant C" with a different stylistic approach
4. Label all variants clearly so the user can compare results

---

## 6. Forbidden

- Generating prompts for `web` rows — those go through [`image-searcher.md`](./image-searcher.md)
- Brand names or HEX codes in AI prompts unless explicitly requested by the user for the image itself
- Mixed Deck Style Anchors across images in the same deck (breaks coherence)
- Placing an image without updating `image_prompts.md` and the resource list status
