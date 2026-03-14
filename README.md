# Markdown to Feishu

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/Aojianlong/markdown-to-feishu.svg)](https://github.com/Aojianlong/markdown-to-feishu/stargazers)

一键将 Markdown 文档（含本地图片）同步到飞书云文档，保留完整格式。

可作为 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 使用，也可独立运行。

---

## 功能特性

### 两层架构

| 层级 | 处理方式 | 覆盖元素 |
|------|---------|---------|
| **Tier 1** | Python 脚本自动完成 | 标题、段落、行内样式、有序/无序列表（含多层嵌套）、代码块、引用、分隔线、图片（含并排 Grid 布局）、Markdown 表格、HTML 表格、任务列表 |
| **Tier 2** | AI 调用 MCP 工具 | Mermaid 流程图 → 飞书画板 |

### 支持的元素

| 元素 | 语法 | 说明 |
|------|------|------|
| 标题 | `# H1` - `###### H6` | H1/H2 标题前自动插入空行，改善阅读体验 |
| 段落 | 正文文本 | 支持粗体、斜体、删除线、下划线、高亮、颜色、行内代码、链接 |
| 有序列表 | `1. item` | 原生飞书列表块，支持多层嵌套（3-4 层） |
| 无序列表 | `- item` | 原生飞书列表块，支持多层嵌套 |
| 任务列表 | `- [x]` / `- [ ]` | 飞书 todo 块 |
| 代码块 | ` ```python ` | 支持 40+ 语言语法高亮 |
| 引用块 | `> text` | 飞书引用块 |
| 分隔线 | `---` / `***` | 水平分隔线 |
| 图片 | `![w50](path)` | 本地图片自动上传，支持并排 Grid 布局和宽度控制 |
| Markdown 表格 | `\| head \| head \|` | 列宽按内容长度比例自动分配 |
| HTML 表格 | `<table>` | 支持 `colspan`、嵌套列表、加粗、换行、链接，列宽按比例分配 |
| Mermaid 流程图 | ` ```mermaid ` | 先创建代码块 fallback，再通过 MCP 渲染为飞书画板 |

### 阅读体验优化

- **章节间距**：H1/H2 标题前自动插入空行，视觉分隔更清晰
- **表格列宽**：根据每列最大内容长度按比例分配宽度（总宽 1093px），避免飞书默认的窄列宽

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置飞书应用

**创建应用**：
1. 访问 [飞书开放平台](https://open.feishu.cn/app)，创建企业自建应用
2. 复制 **App ID** 和 **App Secret**

**添加权限**：

| 权限名称 | 权限标识 | 说明 |
|---------|---------|------|
| 查看、评论、编辑和管理云空间中的文档 | `docx:document` | 创建和编辑云文档 |
| 查看、编辑、上传、下载云空间的资源 | `drive:drive` | 上传图片到云空间 |

**初始化配置**：

```bash
python setup.py init    # 输入 App ID 和 App Secret
python setup.py test    # 测试连接
python setup.py show    # 查看当前配置
```

也支持环境变量：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`

### 3. 同步文档

```bash
python main.py "D:\notes\我的文章.md"
```

成功输出：
```
============================================================
[SUCCESS] 同步完成！
文档标题: 我的文章
文档链接: https://bytedance.feishu.cn/docx/xxxxx
============================================================
```

---

## 作为 Claude Code Skill 使用

将本项目放到 `~/.claude/skills/markdown-to-feishu/scripts/` 目录下即可作为 Claude Code Skill 使用。

在 Claude Code 中直接说：

```
请用 /markdown-to-feishu 同步我的文档 D:\notes\项目文档.md
```

Claude 会自动完成 Tier 1（Python 脚本）和 Tier 2（Mermaid 画板渲染）的全部操作。

---

## 图片路径规则

图片路径相对于 Markdown 文件所在目录解析：

```
你的笔记文件夹/
├── 我的文章.md
├── images/screenshot.png          # images/screenshot.png
├── 我的文章.assets/diagram.png    # Obsidian 样式
└── assets/photo.jpg               # ./assets/photo.jpg
```

- 支持格式：JPG、PNG、GIF
- 支持宽度控制：`![w50](images/pic.jpg)` → 50% 宽度
- 连续图片自动并排（Grid 布局，最多 5 列）
- 不支持远程图片 URL

---

## Mermaid 流程图（Tier 2）

脚本会将 Mermaid 代码块先作为普通代码块上传（fallback），同时输出 `---MERMAID_DATA_START---` 标记。

如果作为 Claude Code Skill 使用，Claude 会自动处理 Tier 2：
1. 在 fallback 代码块旁创建飞书画板块
2. 用 `fill_whiteboard_with_plantuml`（syntax_type=2）渲染 Mermaid
3. 成功后删除 fallback 代码块

如果独立使用，Mermaid 代码块会保留为普通代码块。

---

## 配置说明

`config.json` 结构：

```json
{
  "feishu": {
    "app_id": "cli_xxxxxxxxxx",
    "app_secret": "xxxxxxxxxxxx"
  },
  "default_image_width": 800,
  "width_mapping": {
    "w50": 50,
    "w30": 30,
    "w100": 100
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `feishu.app_id` | 飞书应用 ID | - |
| `feishu.app_secret` | 飞书应用密钥 | - |
| `default_image_width` | 文档宽度基准（px） | 800 |
| `width_mapping` | 图片宽度百分比映射 | w50=50, w30=30, w100=100 |

---

## 支持的 Markdown 语法

| 语法 | 飞书效果 | 说明 |
|------|---------|------|
| `# 标题` | 一级标题 | 支持 H1-H6 |
| `**粗体**` | **粗体** | |
| `~~删除线~~` | ~~删除线~~ | |
| `<u>下划线</u>` | 下划线 | |
| `==高亮==` | 高亮 | 黄色背景 |
| `` `行内代码` `` | `代码` | |
| `<font color="red">文本</font>` | 彩色文本 | 支持 red/orange/yellow/green/blue/purple/gray |
| `[链接](url)` | 可点击链接 | |
| `> 引用` | 引用块 | |
| `- 列表` | 无序列表 | 支持多层嵌套 |
| `1. 列表` | 有序列表 | 支持多层嵌套，保留原始序号 |
| `- [ ] 任务` | 任务列表 | |
| `\| 表格 \|` | 表格 | 列宽按内容比例分配 |
| `<table>` | HTML 表格 | 支持 colspan、嵌套列表 |
| ` ```lang ` | 代码块 | 40+ 语言高亮 |
| `---` | 分隔线 | |
| `![w50](path)` | 图片 | 支持宽度控制和并排 |
| ` ```mermaid ` | Mermaid 流程图 | Tier 2 画板渲染 |

---

## 项目结构

```
markdown-to-feishu/
├── main.py                 # 主入口，文档解析和上传编排
├── setup.py                # 配置初始化和连接测试
├── config_utils.py         # 配置加载（支持文件和环境变量）
├── config.example.json     # 配置模板
├── requirements.txt        # Python 依赖
├── skill.md                # Claude Code Skill 描述
├── tools/
│   ├── markdown_parser.py  # Markdown 解析（含 HTML 表格提取）
│   ├── block_converter.py  # 飞书 Block 格式转换
│   ├── feishu_uploader.py  # 飞书 API 封装（文档/图片/表格）
│   └── html_parser.py      # HTML 表格解析（嵌套列表、colspan）
├── LICENSE
└── README.md
```

---

## 技术细节

- **API 限流**：飞书 API 限制 3 次/秒，脚本内置延迟和自动重试
- **批量上传**：blocks 按 batch 批量创建，减少 API 调用次数
- **图片并发**：多张图片并发上传，速度提升约 60%
- **列表嵌套**：通过 descendant API 一次性创建，支持 3-4 层深度
- **HTML 表格 colspan**：通过空 cell 模拟（飞书不支持合并单元格）
- **表格列宽**：基于 PATCH `/docx/v1/documents/{doc_id}/blocks/{block_id}` 的 `update_table_property` 按列设置

---

## 许可证

MIT License
