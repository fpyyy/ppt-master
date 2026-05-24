---
template_id: "bit-template"
canvas_format: "ppt169"
template_engine: "locked_svg"
template_contract: "template_contract.json"
placeholder_style: "custom"
style_lock: true
style_lock_source: "llm_xml"
primary_color: "#005C30"
summary: "BIT green academic locked SVG template with fixed five-section TOC."
keywords: ["BIT", "academic", "defense", "green", "five-section-toc"]
category: "academic"
use_cases: "Thesis defense, academic report, course presentation, formal project review"
design_tone: "formal academic, BIT green, structured, serif-led"
placeholders:
  title: ["{{PPTTitle}}", "{{PresenterNames}}", "{{TeacherNames}}", "{{TodayDateTime}}"]
  toc: ["{{SectionNumber1}}", "{{SectionNumber2}}", "{{SectionNumber3}}", "{{SectionNumber4}}", "{{SectionNumber5}}", "{{SectionTitle1}}", "{{SectionTitle2}}", "{{SectionTitle3}}", "{{SectionTitle4}}", "{{SectionTitle5}}"]
  chapter: ["{{SectionNumber}}", "{{SectionTitle}}"]
  content: ["{{PageTitle}}"]
  ending: ["{{PresenterNames}}", "{{TeacherNames}}"]
toc_contract:
  stem: "toc"
  slot_count: 5
  item_type: "section"
  count_match_required: true
  compatible_item_counts: [5]
  number_placeholders: ["{{SectionNumber1}}", "{{SectionNumber2}}", "{{SectionNumber3}}", "{{SectionNumber4}}", "{{SectionNumber5}}"]
  title_placeholders: ["{{SectionTitle1}}", "{{SectionTitle2}}", "{{SectionTitle3}}", "{{SectionTitle4}}", "{{SectionTitle5}}"]
  mismatch_action: "Omit the TOC page from page_layouts and redesign it as a free structural page using this template's style lock."
---

# bit-template - Locked SVG Template

## I. Runtime Contract

- Contract file: `template_contract.json`
- Template engine: `locked_svg`
- Runtime fill command: `svg_template.py apply <template_dir> <page_stem> --data <fill.json> -o <out.svg>`
- Runtime agents read `template_contract.json`, not template SVG source.

## II. Page Roster

| File | Role | Placeholders | Workspaces |
|---|---|---|---|
| `title.svg` | title | `{{PPTTitle}}`, `{{PresenterNames}}`, `{{TeacherNames}}`, `{{TodayDateTime}}` | None |
| `toc.svg` | toc | `{{SectionNumber1}}`, `{{SectionNumber2}}`, `{{SectionNumber3}}`, `{{SectionNumber4}}`, `{{SectionNumber5}}`, `{{SectionTitle1}}`, `{{SectionTitle2}}`, `{{SectionTitle3}}`, `{{SectionTitle4}}`, `{{SectionTitle5}}` | None |
| `chapter.svg` | chapter | `{{SectionNumber}}`, `{{SectionTitle}}` | None |
| `content.svg` | content | `{{PageTitle}}` | `main` x=96, y=104, 1088x542 |
| `ending.svg` | ending | `{{PresenterNames}}`, `{{TeacherNames}}` | None |

## III. Runtime Fill Rules

- Section numbering is locked to plain Arabic digits `1`, `2`, `3`, `4`, `5`.
- `{{SectionNumber1}}` through `{{SectionNumber5}}` in `toc.svg` MUST use `1` through `5` respectively.
- `{{SectionNumber}}` in `chapter.svg` MUST use the matching chapter digit `1` through `5`.
- Do not use leading zeros (`01`, `02`), Chinese numerals, Roman numerals, prefixes, suffixes, or punctuation for section numbers.
- The `content.svg` workspace `main` is fixed at x=`96`, y=`104`, width=`1088`, height=`542`.

### TOC Slot Contract

| Field | Value |
|---|---|
| TOC stem | `toc` |
| Item type | section |
| Slot count | 5 |
| Number placeholders | `{{SectionNumber1}}` through `{{SectionNumber5}}` |
| Title placeholders | `{{SectionTitle1}}` through `{{SectionTitle5}}` |
| Compatible outline count | exactly 5 sections |

**Hard rule**: Use `toc.svg` only when the deck outline has exactly 5 TOC
items. If the outline has 1, 2, 3, 4, or 6+ items, do not fill blank slots,
duplicate sections, invent filler sections, or squeeze extra items into the
locked TOC page. Omit the TOC page from `page_layouts` and redesign it as a
free structural page using this template's colors and typography.

**Safe replanning directions**:

| Actual item count | Layout direction |
|---|---|
| 1 | Single centered section statement with subtitle |
| 2 | Two balanced columns or two strong horizontal bands |
| 3 | Three-column row, vertical stack, or triangular grouping |
| 4 | 2x2 grid or four-step vertical list with enlarged spacing |
| 6+ | Two-column agenda, grouped chapter clusters, or compact timeline |

## IV. Template Style Lock

**Hard rule**: Downstream PPT generation MUST copy these colors and typography values into the project `design_spec.md` and `spec_lock.md`. Do not replace them during the Eight Confirmations unless the user explicitly asks to override the locked template style.

- Source: `llm_xml/*.xml` generated at template creation time
- Runtime scope: generated workspace content, charts, icons, and free-design pages in the same deck

### Colors

| Lock Key | Value | Runtime Usage |
|---|---|---|
| `bg` | `#FFFFFF` | Page background / implicit canvas |
| `secondary_bg` | `#A13F0B` | Cards, bands, low-emphasis panels |
| `primary` | `#005C30` | Template brand color; titles, icons, section marks |
| `accent` | `#009944` | Data highlights and high-emphasis callouts |
| `secondary_accent` | `#A13F0B` | Secondary emphasis and gradient companion |
| `text` | `#057748` | Main text |
| `text_secondary` | `#3F3F3F` | Captions, labels, annotations |
| `border` | `#A13F0B` | Dividers and outlines |

### Typography

| Lock Key | Value |
|---|---|
| `font_family` | `Times New Roman,Microsoft YaHei,serif` |
| `title_family` | `Times New Roman,Microsoft YaHei,serif` |
| `body_family` | `Times New Roman,Microsoft YaHei,serif` |
| `emphasis_family` | `Times New Roman,Microsoft YaHei,serif` |
| `code_family` | `Consolas, "Courier New", monospace` |
| `body` | `28px` |
| `title` | `48px` |
| `cover_title` | `59px` |
| `subtitle` | `35px` |
| `annotation` | `24px` |
| `minimum_text` | `24px` |

Runtime minimum: generated workspace body text, annotations, captions, and chart labels MUST NOT be smaller than `24px` in SVG (`18pt` in PowerPoint).

### Extraction Evidence

Observed palette:

| HEX | Uses | Fill | Stroke | Text |
|---|---:|---:|---:|---:|
| `#FFFFFF` | 45 | 40 | 5 | 26 |
| `#057748` | 6 | 6 | 0 | 1 |
| `#A13F0B` | 61 | 28 | 33 | 0 |
| `#3F3F3F` | 1 | 1 | 0 | 1 |
| `#A2A2A2` | 1 | 1 | 0 | 1 |
| `#A6A6A6` | 17 | 17 | 0 | 0 |
| `#DAB293` | 2 | 2 | 0 | 0 |
| `#009944` | 2 | 2 | 0 | 0 |
| `#005C30` | 2 | 2 | 0 | 0 |
| `#CAE5CD` | 1 | 1 | 0 | 0 |
| `#89C997` | 1 | 1 | 0 | 0 |
| `#13AE67` | 1 | 1 | 0 | 0 |

Observed fonts:

| Font Family | Weighted Uses | Observed Sizes |
|---|---:|---|
| `Times New Roman,Microsoft YaHei,serif` | 370 | `48px`, `32px`, `59px`, `16px`, `21px`, `37px` |
