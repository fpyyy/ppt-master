---
template_id: "ai-template"
canvas_format: "ppt169"
template_engine: "locked_svg"
template_contract: "template_contract.json"
placeholder_style: "custom"
placeholders:
  title: ["{{PPTTitle}}", "{{PresenterNames}}", "{{TeacherNames}}", "{{TodayDateTime}}"]
  toc: ["{{SectionNumber1}}", "{{SectionNumber2}}", "{{SectionNumber3}}", "{{SectionNumber4}}", "{{SectionNumber5}}", "{{SectionTitle1}}", "{{SectionTitle2}}", "{{SectionTitle3}}", "{{SectionTitle4}}", "{{SectionTitle5}}"]
  chapter: ["{{SectionNumber}}", "{{SectionTitle}}"]
  content: ["{{PageTitle}}"]
  ending: ["{{PresenterNames}}", "{{TeacherNames}}"]
---

# ai-template - Locked SVG Template

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
| `content.svg` | content | `{{PageTitle}}` | `main` 1088x522 |
| `ending.svg` | ending | `{{PresenterNames}}`, `{{TeacherNames}}` | None |
