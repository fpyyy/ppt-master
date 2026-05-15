# Layout Template Library

There are currently no built-in layout templates.

PPT Master now uses locked SVG templates only:

1. Prepare exactly five SVG page templates: `title.svg`, `toc.svg`, `chapter.svg`, `content.svg`, `ending.svg`.
2. Mark editable text with custom placeholders such as `{{PPTTitle}}`.
3. Run `svg_llm_xml.py` to create sanitized XML for theme / color inspection.
4. Run `svg_template.py inspect`, then `svg_template.py create`.

`svg_template.py create` infers the `content.svg` workspace automatically.
The runtime workflow reads only `design_spec.md` and `template_contract.json`.
Agents must not read template SVG source after template creation.

See `skills/ppt-master/workflows/create-template.md` for the full SVG-only creation workflow.

## Quick Template Index

<!-- quick-index:begin -->
| Template Name | Engine | Pages | Contract |
|---------------|--------|-------|----------|
| `BIT-template` | locked_svg | `chapter.svg`, `content.svg`, `ending.svg`, `title.svg`, `toc.svg` | `template_contract.json` |
<!-- quick-index:end -->
