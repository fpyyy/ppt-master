---
template_id: BIT
display_name: BIT
category: brand
summary: Beijing Institute of Technology thesis defense and academic report template with BIT green, rust accents, and campus-branded page chrome.
keywords: [BIT, thesis-defense, academic, university, green]
primary_color: "#006C39"
canvas_format: ppt169
replication_mode: fidelity
use_cases: 北理工毕业答辩、论文开题、中期汇报、学术研究汇报、校园品牌展示
design_tone: Campus-branded, formal, restrained, academic defense style
placeholders:
  01_cover: ["{{TITLE}}", "{{SUBTITLE}}", "{{AUTHOR}}", "{{ADVISOR}}", "{{DATE}}"]
  02_toc: ["{{TOC_ITEM_1_TITLE}}", "{{TOC_ITEM_2_TITLE}}", "{{TOC_ITEM_3_TITLE}}", "{{TOC_ITEM_4_TITLE}}", "{{TOC_ITEM_5_TITLE}}"]
  02_chapter: ["{{CHAPTER_NUM}}", "{{CHAPTER_TITLE}}"]
  03_content: ["{{PAGE_TITLE}}", "{{CONTENT_AREA}}"]
  04_ending: ["{{THANK_YOU}}", "{{ENDING_SUBTITLE}}", "{{CONTACT_INFO}}"]
---

# BIT - Design Specification

## I. Template Overview

- Use cases: 北理工毕业答辩、论文开题、中期汇报、学术研究汇报、校园品牌展示。
- Tone: 校园品牌感、正式、克制、学术答辩风。
- Theme mode: mixed. Cover and ending use full green brand fields; TOC, chapter, and content pages combine white workspace with green campus chrome.

At a glance, this template is identified by Beijing Institute of Technology green, a rust accent bar, left-side curved white panels, centered BIT wordmark treatment, and restrained academic typography.

## II. Color Scheme

- Primary BIT Green: `#006C39` for full-page fields, headers, page chrome, and key anchors.
- Bright Green: `#008244` for subtle gradients and brand depth.
- Rust Accent: `#A13F0B` for dividers, section numbers, and small emphasis bars.
- Warm Gray: `#A2A2A2` for secondary headings and muted academic decoration.
- Text Black: `#000000` for primary body text on white.
- Background White: `#FFFFFF` for readable academic content space.

## III. Typography

- Primary stack: `Microsoft YaHei, Arial, sans-serif`.
- Numeric accent stack: `Century Gothic, Arial, sans-serif`.
- Body baseline: 22 px, with page titles typically 30-36 px and cover/chapter titles 44-56 px.

## IV. Signature Design Elements

- Curved white left panel over a deep green field for cover and branded section pages.
- Rust accent layer used as a thin bar or offset shape behind white content panels.
- Cropped campus panorama header on TOC and chapter pages, preserving the original PPTX crop wrapper geometry.
- BIT wordmark assets bundled in the template package for fixed brand chrome.
- Minimal gray academic motif on the alternate chapter page, adapted from the source deck's decorative bottom linework.

## V. Page Roster

| File | Role | Description |
|---|---|---|
| `01_cover.svg` | Cover | Literal-inspired cover with green background, left white curved panel, BIT label, right-side campus/building imagery, title/subtitle, author/advisor/date placeholders. |
| `02_toc.svg` | Table of contents | Literal-inspired catalog page using the source campus panorama crop, green overlay, rust divider, BIT wordmark, and five numbered chapter slots. |
| `02a_chapter_full.svg` | Chapter variant | Full chapter opening based on the source large-number chapter page; top campus banner, rust divider, large rust number circle, and chapter title. |
| `02b_chapter_minimal.svg` | Chapter variant | Minimal chapter/title divider adapted from the source one-line page with a quiet gray academic motif along the bottom. |
| `03_content.svg` | Content | Adapted reusable content page with BIT header, page title, key message strip, flexible content area, and footer fields. |
| `04_ending.svg` | Ending | Literal-inspired closing page with full green field, white line motif, BIT white logo, thank-you title, subtitle, and contact fields. |

## VI. Assets

- `campus_panorama.png`: original PPTX panorama image used in cropped header bands.
- `bit_wordmark.png`: source BIT wordmark used in TOC and chapter chrome.
- `cover_building.png`: cover-side building/symbolic image from the original PPTX.
- `cover_emblem.png`: secondary cover emblem image from the original PPTX.
- `bit_logo_white.png`: white BIT logo used on the ending page.
- `header_logo.png`: compact header logo used on content and minimal pages.
