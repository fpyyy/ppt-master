---
template_id: bit_standard
display_name: 北理工标准版
category: scenario
summary: Beijing Institute of Technology standard academic defense template with BIT green, rust accents, campus imagery, and reusable PPT Master placeholders.
keywords: [BIT, defense, academic, university, green]
primary_color: "#006C39"
canvas_format: ppt169
replication_mode: standard
use_cases: 北京理工大学毕业答辩、论文开题、中期汇报、课题汇报、学院正式展示
design_tone: Formal, restrained, campus-branded academic defense style
placeholders:
  01_cover: ["{{TITLE}}", "{{SUBTITLE}}", "{{AUTHOR}}", "{{ADVISOR}}", "{{DATE}}"]
  02_toc: ["{{TOC_ITEM_1_TITLE}}", "{{TOC_ITEM_2_TITLE}}", "{{TOC_ITEM_3_TITLE}}", "{{TOC_ITEM_4_TITLE}}", "{{TOC_ITEM_5_TITLE}}"]
  02_chapter: ["{{CHAPTER_NUM}}", "{{CHAPTER_TITLE}}"]
  03_content: ["{{PAGE_TITLE}}", "{{CONTENT_AREA}}"]
  04_ending: ["{{THANK_YOU}}", "{{ENDING_SUBTITLE}}", "{{CONTACT_INFO}}"]
---

# 北理工标准版 - Design Specification

## I. Template Overview

- Use cases: 北京理工大学毕业设计答辩、论文开题、中期汇报、学术课题汇报、学院/高校正式展示。
- Tone: 校园品牌感、正式、克制、学术答辩风格。
- Theme mode: mixed. Cover, chapter, TOC, and ending pages preserve the source deck's branded green field and campus chrome; the content page adapts that language into a clean reusable workspace.

At a glance, this template is identified by BIT green, rust accent bars, curved white structural panels, campus image crops, centered BIT wordmark treatment, and restrained academic typography.

## II. Color Scheme

- Primary BIT Green: `#006C39` for full-page fields, headers, page chrome, and section anchors.
- Bright Green: `#008244` for subtle green depth and gradients.
- Rust Accent: `#A13F0B` for dividers, chapter numbers, and small emphasis bars.
- Warm Gray: `#A2A2A2` for secondary headings and quiet academic decoration.
- Text Black: `#000000` for primary body text on white.
- Background White: `#FFFFFF` for readable academic content space.

## III. Typography

- Primary stack: `Microsoft YaHei, Arial, sans-serif`.
- Numeric accent stack: `Century Gothic, Arial, sans-serif`.
- Body baseline: 22 px, with page titles typically 30-36 px and cover/chapter titles 44-56 px.

## IV. Signature Design Elements

- Curved white panel over a deep green field for formal cover and chapter pages.
- Rust accent layer used as a thin bar, section number circle, or offset shape behind white panels.
- Cropped campus panorama header on TOC/chapter surfaces, preserving the reference deck's institutional feel.
- BIT wordmark and logo assets bundled in the template package for fixed brand chrome.
- Adapted content page with a compact BIT header, broad white work area, and understated footer.

## V. Page Roster

| File | Role | Description |
|---|---|---|
| `01_cover.svg` | Cover | Literal reference-inspired cover with green background, left white curved panel, BIT label, right-side campus/building imagery, title/subtitle, author/advisor/date placeholders. |
| `02_toc.svg` | Table of contents | Literal reference-inspired catalog page using campus panorama crop, green overlay, rust divider, BIT wordmark, and five numbered chapter slots. |
| `02_chapter.svg` | Chapter | Literal reference-inspired chapter opening with top campus banner, rust divider, large rust chapter number circle, and chapter title. |
| `03_content.svg` | Content | Adapted reusable content page with BIT header, page title, flexible content area, and footer fields. |
| `04_ending.svg` | Ending | Literal reference-inspired closing page with full green field, white line motif, BIT white logo, thank-you title, subtitle, and contact fields. |

## VI. Assets

- `campus_panorama.png`: original PPTX panorama image used in cropped header bands.
- `bit_wordmark.png`: source BIT wordmark used in TOC and chapter chrome.
- `cover_building.png`: cover-side building/symbolic image from the original PPTX.
- `cover_emblem.png`: secondary cover emblem image from the original PPTX.
- `bit_logo_white.png`: white BIT logo used on the ending page.
- `header_logo.png`: compact header logo used on content and minimal pages.
