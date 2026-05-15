# Layout Template Library

There are currently no built-in layout templates.

PPT Master now uses locked SVG templates only:

1. Prepare a folder of SVG page templates.
2. Mark editable text with custom placeholders such as `{{PPTTitle}}`.
3. Mark each content page workspace with `data-ppt-workspace="main"`.
4. Run `svg_template.py inspect`, then `svg_template.py create`.

The runtime workflow reads only `design_spec.md` and `template_contract.json`.
Agents must not read template SVG source after template creation.

See `skills/ppt-master/workflows/create-template.md` for the full SVG-only creation workflow.
