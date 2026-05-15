# 模板指南：锁定 SVG 工作流

PPT Master 模板现在是 **锁定 SVG 契约**：SVG 文件保留在磁盘上，运行时智能体只读取
`design_spec.md` 和 `template_contract.json`。

## 1. 使用模板

模板只能通过明确目录路径触发。目录必须包含：

- `design_spec.md`
- `template_contract.json`
- `title.svg`、`toc.svg`、`chapter.svg`、`content.svg`、`ending.svg`

示例：

```text
使用这个模板：skills/ppt-master/templates/layouts/bit_locked/
```

工作流会把整个目录复制到：

```text
projects/<project>/templates/<template_id>/
```

生成 PPT 时，智能体不能读取模板 SVG。它只读取契约，生成占位符 JSON 和正文工作区
fragment，然后调用：

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py apply <template_dir> <page_stem> --data fill.json -o out.svg
```

## 2. 创建模板

`/create-template` 只接受已经准备好的 SVG 目录。不再支持 PPTX、截图、PDF、图片参考或口头风格描述创建模板。

```bash
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py inspect <svg_dir>
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_llm_xml.py <svg_dir> -o <svg_dir>\llm_xml
.\.venv\Scripts\python.exe skills/ppt-master/scripts/svg_template.py create <svg_dir> <template_id>
```

`inspect` 只输出精简元数据，不输出 SVG 源码或 base64 图片内容。
`svg_llm_xml.py` 会生成适合大模型阅读的 XML：base64 图片和 path 的 `d`
绘制内容会被伪代码替换，文本、颜色和几何属性会保留。

## 3. SVG 要求

可替换文字使用自定义占位符：

```xml
{{PPTTitle}}
{{PPTSubtitle}}
{{PPTDate}}
```

目录必须正好包含：

```text
title.svg
toc.svg
chapter.svg
content.svg
ending.svg
```

只有 `content.svg` 会有正文工作区。`svg_template.py create` 会自动推断该
工作区并写入 `template_contract.json`；其它四页只替换花括号占位符。

生成的 `template_contract.json` 会记录每页的文件名、占位符、工作区 bbox 和 SVG SHA。SVG 修改后需要重新创建模板契约。

## 4. 边界

- 锁定 SVG 模板保留原有视觉外壳。
- 运行时智能体只在自动推断出的 `content.svg` 工作区里生成内容。
- 标题页、目录页、章节页、结束页只替换 `{{...}}` 文本，并遵守 `text_fit` 长度预算。
- SVG 可以包含嵌入 PNG/base64，但不会进入提示词上下文。
- 旧的模板复刻模式已移除；模板统一从 SVG 创建。
