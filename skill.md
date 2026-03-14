---
name: markdown-to-feishu
description: 将本地 Markdown 文档上传为飞书云文档，并自动上传本地图片。用于用户提供 Markdown 文件路径，希望同步到飞书、保留基础格式和图片时。适合 Obsidian、本地知识库和由 $feishu-to-markdown 导出的 Markdown 回传场景。
---

# Markdown to Feishu

## Overview

两层架构：

| 层级 | 处理方式 | 覆盖元素 |
|------|---------|---------|
| **Tier 1** | Python 脚本自动完成 | 标题、段落、行内样式、原生有序列表（含嵌套）、原生无序列表（含嵌套）、代码块、引用、分隔线、图片（含并排Grid布局）、Markdown 表格、HTML 表格（含单元格内嵌套列表）、任务列表 |
| **Tier 2** | AI 调用 MCP 工具 | Mermaid 流程图 → 飞书画板 |

## Supported Elements

- **标题**: H1-H6 → 飞书标题 block（一级标题前自动插入空行分隔章节）
- **段落**: 含粗体、斜体、删除线、下划线、高亮、颜色、行内代码、链接
- **有序列表**: 原生 block_type 13，支持多层嵌套
- **无序列表**: 原生 block_type 12，支持多层嵌套
- **任务列表**: `- [x]` / `- [ ]` → 飞书 todo block
- **代码块**: 支持 40+ 语言高亮
- **引用块**: `>` 引用
- **分隔线**: `---` / `***`
- **图片**: 本地图片自动上传，支持并排 Grid 布局（`![w50](path)` 控制宽度）
- **Markdown 表格**: `| head | head |` 格式，列宽自动均匀分布
- **HTML 表格**: `<table>` 标签，支持单元格内 `<ol>`/`<ul>` 嵌套列表、`<strong>` 加粗、`<br/>` 换行、`<a>` 链接、`colspan`，列宽自动均匀分布
- **Mermaid 流程图**: 代码块 fallback + Tier 2 画板渲染

## First Use

需要飞书开放平台的 `App ID` 和 `App Secret`。

```powershell
# 初始化配置
python "${SKILL_DIR}\scripts\setup.py" init
# 测试连接
python "${SKILL_DIR}\scripts\setup.py" test
# 查看配置
python "${SKILL_DIR}\scripts\setup.py" show
```

也支持环境变量覆盖：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`

依赖安装（首次使用）：
```powershell
pip install -r "${SKILL_DIR}\requirements.txt"
```

## Usage

### Tier 1: Python 脚本（自动）

```powershell
python "${SKILL_DIR}\scripts\main.py" "D:\path\to\document.md"
```

脚本自动处理所有 Tier 1 元素，输出飞书文档链接。

### Tier 2: Mermaid 画板（AI 辅助）

**如果**脚本输出中包含 `---MERMAID_DATA_START---` 标记，则文档中有 Mermaid 流程图需要渲染为画板。

步骤：

1. 解析 `---MERMAID_DATA_START---` 和 `---MERMAID_DATA_END---` 之间的 JSON
2. JSON 格式：`{"document_id": "...", "mermaid_blocks": [{"code": "...", "fallback_block_id": "..."}]}`
3. 对每个 mermaid block：
   a. 调用 `batch_create_feishu_blocks` 在文档中创建画板块（whiteboard 类型）
   b. 调用 `fill_whiteboard_with_plantuml` 填充 mermaid 代码（`syntax_type: 2` 表示 Mermaid 语法）
   c. 成功后，可选删除 fallback 代码块（`fallback_block_id`）
   d. 如果失败，保留 fallback 代码块不动，告知用户

**如果**脚本输出中没有 MERMAID_DATA 标记，则无需 Tier 2 操作。

## Workflow

```
1. 运行 Python 脚本 → 创建飞书文档 + 上传所有 Tier 1 内容
2. 检查输出是否包含 MERMAID_DATA
3. 如有 → 执行 Tier 2 MCP 操作
4. 返回飞书文档链接给用户
```

## Image Path Rules

图片路径按 Markdown 文件所在目录解析：

- `images/xxx.png`（同级 images 目录）
- `文档标题.assets/xxx.png`（Obsidian 样式）
- `./assets/xxx.png`（相对路径）
- 绝对路径

不支持远程图片 URL。

## Notes

- 飞书 API 限流：3 次/秒，脚本已内置延迟和重试
- HTML 表格 `colspan` 通过空 cell 模拟（飞书不支持合并单元格）
- 有序列表嵌套通过 descendant API 一次性创建，支持 3-4 层深度
- 如果用户的 Markdown 来自 `$feishu-to-markdown`，本地图片引用可直接复用
