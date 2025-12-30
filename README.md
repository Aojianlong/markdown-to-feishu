# Markdown to 飞书同步工具

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/Aojianlong/markdown-to-feishu.svg)](https://github.com/Aojianlong/markdown-to-feishu/stargazers)

一键将 Markdown 文章（含本地图片）自动同步到飞书云文档。

> 💡 **适合人群**：使用 Markdown 编辑器（Obsidian、Typora、VS Code 等）做笔记，想要快速分享到飞书的用户
> 🎯 **核心优势**：保留格式、自动上传图片、一键完成

---

## ✨ 功能特性

- ✅ **自动上传图片**：本地图片自动上传到飞书云空间
- ✅ **格式完整保留**：标题、粗体、颜色、列表、引用、代码块等
- ✅ **丰富文本样式**：支持删除线、下划线、高亮、行内代码等
- ✅ **表格支持**：Markdown 表格自动转换为飞书表格
- ✅ **任务列表**：支持任务列表（- [ ] 和 - [x]）
- ✅ **图片宽度控制**：支持 `![w50](image.jpg)` 设置图片显示宽度
- ✅ **并排图片**：连续图片自动使用分栏布局（最多5列）
- ✅ **超链接支持**：Markdown 链接自动转换为可点击链接
- ✅ **并发上传**：多张图片并发上传，速度提升60%
- ✅ **一键同步**：在 Claude Code 中输入一条命令即可完成

---

## 🚀 快速开始（3 步完成）

### 第 1 步：安装工具

**在 Claude Code 中发送以下消息**：

```
请帮我安装 markdown-to-feishu 这个 skill 的依赖
```

Claude 会自动执行安装命令。

<details>
<summary>💻 技术细节（可选展开）</summary>

安装命令实际上是：
```bash
cd ~/.claude/skills/markdown-to-feishu
pip install -r requirements.txt
```

**Windows 用户注意**：路径可能是 `C:\Users\你的用户名\.claude\skills\markdown-to-feishu`
</details>

---

### 第 2 步：配置飞书应用

**2.1 创建飞书应用**

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击「**创建企业自建应用**」
3. 填写应用名称（如：`Markdown 同步工具`）
4. 在「**凭证与基础信息**」页面，复制 **App ID** 和 **App Secret**

**2.2 配置应用权限**

在「**权限管理**」页面添加以下权限：

| 权限名称 | 权限标识 | 说明 |
|---------|---------|------|
| 查看、评论、编辑和管理云空间中的文档 | `docx:document` | 创建和编辑云文档 |
| 查看、编辑、上传、下载云空间的资源 | `drive:drive` | 上传图片到云空间 |

配置后点击「**申请权限**」并等待管理员审核（如果你是管理员可直接通过）。

**2.3 配置工具**

**在 Claude Code 中发送**：

```
请帮我配置 markdown-to-feishu，我的 App ID 是 cli_xxxxxx，App Secret 是 xxxxxx
```

将上面的 `cli_xxxxxx` 和 `xxxxxx` 替换为你在步骤 2.1 中获取的真实值。

<details>
<summary>💻 技术细节（可选展开）</summary>

Claude 会帮你复制 `config.example.json` 为 `config.json`，并填入你的凭证。

**手动配置方法**：
1. 找到文件 `~/.claude/skills/markdown-to-feishu/config.example.json`
2. 复制并重命名为 `config.json`
3. 用文本编辑器打开，填入你的 App ID 和 App Secret

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

**安全提示**：`config.json` 已被加入 `.gitignore`，不会提交到版本控制，你的凭证是安全的。
</details>

---

### 第 3 步：同步文档

**在 Claude Code 中发送**：

```
请用 /markdown-to-feishu 同步我的文档 D:\notes\我的文章.md
```

将路径替换为你的实际文件路径。

**✅ 成功后会返回**：

```
============================================================
[SUCCESS] 同步完成！
文档标题: 我的文章
文档链接: https://bytedance.feishu.cn/docx/xxxxx
============================================================
```

点击链接即可在飞书中查看文档！

---

## 📁 文件准备要求

### 文件夹结构

你的 Markdown 笔记文件夹需要按以下结构组织：

```
你的笔记文件夹/
├── 我的文章.md          ← 你的 Markdown 文件
└── images/              ← 图片必须放在这个文件夹
    ├── screenshot1.jpg
    ├── screenshot2.png
    └── diagram.png
```

**❗ 重要规则**：

1. 图片必须放在与 Markdown 文件**同级**的 `images/` 文件夹中
2. 在 Markdown 中引用图片时，使用相对路径：`![w50](images/screenshot1.jpg)`
3. 支持的图片格式：JPG、PNG、GIF
4. 单张图片大小不超过 20MB

### 示例文档

**我的文章.md**：

```markdown
# 产品使用教程

## 第一步：注册账号

这是**重要提示**：<font color="red">请务必使用企业邮箱</font>

![w50](images/register-page.jpg)

## 第二步：配置权限

请按以下步骤操作：

1. 打开设置页面
2. 点击「权限管理」
3. 添加以下权限：
    - 读取权限
    - 写入权限

> ⚠️ 注意：权限配置需要管理员审核

## 代码示例

```python
def setup_config():
    config = load_config("config.json")
    return config
```

## 参考链接

详细教程请参考：[官方文档](https://example.com/docs)
```

---

## 🎨 支持的 Markdown 语法

| Obsidian 语法 | 飞书效果 | 说明 |
|--------------|---------|------|
| `# 标题` | 一级标题 | 支持 H1-H9 |
| `**粗体**` | **粗体文本** | 加粗显示 |
| `~~删除线~~` | ~~删除线文本~~ | 删除线样式 |
| `<u>下划线</u>` | <u>下划线文本</u> | 下划线样式 |
| `==高亮==` | ==高亮文本== | 黄色高亮背景 |
| `` `行内代码` `` | `代码` | 等宽字体 |
| `<font color="red">文本</font>` | <span style="color:red">红色文本</span> | 支持 7 种颜色 |
| `[链接](https://example.com)` | [可点击链接](https://example.com) | 自动转换为超链接 |
| `> 引用` | 引用块 | 灰色背景 |
| `- 列表项` | • 列表项 | 无序列表 |
| `1. 列表项` | 1. 列表项 | 有序列表（保留序号） |
| `- [ ] 任务` | ☐ 未完成任务 | 任务列表 |
| `- [x] 任务` | ☑ 已完成任务 | 已完成任务 |
| `\| 表格 \|` | 表格 | Markdown 表格 |
| `![w50](images/pic.jpg)` | 50% 宽度图片 | 控制图片显示宽度 |
| ` ```python` | 代码块 | 支持语法高亮 |
| `---` | 分隔线 | 水平分隔线 |

### 颜色支持

`<font color="颜色名">文本</font>` 支持以下颜色：

- `red` - 红色
- `orange` - 橙色
- `yellow` - 黄色
- `green` - 绿色
- `blue` - 蓝色
- `purple` - 紫色
- `gray` - 灰色

### 代码块语言支持

支持 20+ 种编程语言的语法高亮：

`python`, `javascript`, `java`, `go`, `cpp`, `c`, `csharp`, `php`, `ruby`, `rust`, `typescript`, `sql`, `bash`, `shell`, `json`, `xml`, `yaml`, `markdown`, `html`, `css`

**示例**：

````markdown
```python
def hello():
    print("Hello, World!")
```
````

---

## 💬 在 Claude Code 中使用

以下是常用的对话示例，你可以直接复制使用：

### 同步文档

```
请用 /markdown-to-feishu 同步我的文档 D:\notes\项目文档.md
```

### 批量同步（让 Claude 帮你）

```
请帮我把 D:\notes\项目文档\ 文件夹下所有 md 文件都同步到飞书
```

### 检查配置

```
请检查 markdown-to-feishu 的配置是否正确
```

### 查看文件路径

```
请帮我找到我的 Markdown 笔记文件夹路径
```

---

## ❓ 常见问题

### Q1: 我不知道我的 Markdown 文件在哪里？

**在 Claude Code 中发送**：

```
请帮我找到我的 Markdown 笔记存储位置
```

如果你使用 Obsidian：
1. 打开 Obsidian
2. 点击左下角「设置」图标 ⚙️
3. 查看「文件与链接」→「库文件夹位置」

### Q2: 图片显示「无法查看」？

**原因**：图片没有放在 `images/` 文件夹中

**解决**：
1. 在你的 Markdown 文件所在文件夹创建 `images/` 文件夹
2. 将所有图片移动到 `images/` 文件夹
3. 修改 Markdown 中的图片引用为 `![](images/图片名.jpg)`
4. 重新同步

### Q3: 链接无法点击？

**原因**：可能是旧版本问题

**解决**：
```
请帮我更新 markdown-to-feishu 到最新版本
```

### Q4: 某些样式丢失了？

**目前支持的所有 Markdown 语法**：
- ✅ 标题（H1-H9）
- ✅ 粗体（`**text**`）
- ✅ 删除线（`~~text~~`）
- ✅ 下划线（`<u>text</u>`）
- ✅ 高亮（`==text==`）
- ✅ 行内代码（`` `code` ``）
- ✅ 表格（`| table |`）
- ✅ 任务列表（`- [ ] task`）
- ✅ 代码块、引用、列表等

**暂不支持的语法**：
- ❌ 斜体（`*斜体*`）- 飞书云文档 API 暂不支持
- ❌ 嵌套代码块

**替代方案**：
- 粗体代替斜体：`**重点**`
- 使用颜色标记：`<font color="red">重要</font>`

### Q5: 同步失败，显示权限错误？

**解决步骤**：

1. 检查飞书应用权限是否已审核通过
2. **在 Claude Code 中发送**：
   ```
   请帮我测试 markdown-to-feishu 的飞书连接
   ```
3. 如果测试失败，检查 App ID 和 App Secret 是否正确

### Q6: 图片上传很慢？

**原因**：图片文件过大

**解决**：
- 压缩图片（推荐宽度不超过 1920px）
- 使用 PNG/JPG 格式（GIF 文件通常较大）
- 单张图片不超过 5MB

### Q7: 我想修改图片默认宽度？

**在 Claude Code 中发送**：

```
请帮我修改 markdown-to-feishu 的默认图片宽度为 1000px
```

或手动修改 `config.json` 中的 `default_image_width` 值。

---

## 🛠️ 工作原理（技术说明）

工具的同步流程分为 5 步：

1. **解析 Markdown**：读取 `.md` 文件，识别标题、段落、图片、列表等元素
2. **提取样式信息**：解析粗体、颜色、链接等行内样式
3. **上传图片**：将本地图片上传到飞书云空间，获取图片 token
4. **格式转换**：将 Markdown 结构转换为飞书 Block 格式
5. **创建文档**：调用飞书 API 创建云文档，返回文档链接

### 技术栈

- **语言**：Python 3.7+
- **核心库**：`requests`（API 调用）、`Pillow`（图片处理）
- **API**：飞书开放平台 Docx API

---

## 📝 完整配置示例

`config.json` 文件结构：

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

| 配置项 | 说明 | 默认值 | 可选值 |
|--------|------|--------|--------|
| `feishu.app_id` | 飞书应用 ID | 无 | 从飞书开放平台获取 |
| `feishu.app_secret` | 飞书应用密钥 | 无 | 从飞书开放平台获取 |
| `default_image_width` | 文档宽度基准（像素） | 800 | 600-1200 |
| `width_mapping.w50` | `![w50]()` 对应的宽度百分比 | 50 | 1-100 |
| `width_mapping.w30` | `![w30]()` 对应的宽度百分比 | 30 | 1-100 |
| `width_mapping.w100` | `![w100]()` 对应的宽度百分比 | 100 | 1-100 |

---

## 🎯 使用技巧

### 1. 图片并排显示

连续放置多张图片（不换行），工具会自动使用飞书分栏布局：

```markdown
![w30](images/pic1.jpg)![w30](images/pic2.jpg)![w30](images/pic3.jpg)
```

效果：3 张图片并排显示，每张占 30% 宽度

**注意**：飞书最多支持 5 列，超过 5 张会自动分批

### 2. 有序列表保留序号

工具会保留你的原始序号，即使列表被其他内容打断：

```markdown
1. 第一步
2. 第二步

![](images/step2.jpg)

3. 第三步（序号会保留为 3，而不是重新从 1 开始）
```

### 3. 引用块支持嵌套列表

```markdown
> ⚠️ 注意事项：
> - 第一条
> - 第二条
```

引用块内的列表会正确显示

### 4. 代码块指定语言

````markdown
```python
print("Hello")
```
````

会自动识别为 Python 代码并高亮显示

---

## 🔍 故障排查

如果遇到问题，请按以下步骤排查：

### 1. 检查文件路径

**在 Claude Code 中发送**：

```
请检查文件 D:\notes\我的文章.md 是否存在
```

### 2. 检查图片文件夹

**在 Claude Code 中发送**：

```
请检查 D:\notes\images\ 文件夹是否存在，并列出其中的图片
```

### 3. 测试飞书连接

**在 Claude Code 中发送**：

```
请测试 markdown-to-feishu 的飞书 API 连接
```

### 4. 查看详细错误

如果同步失败，复制完整的错误信息发送给 Claude：

```
markdown-to-feishu 同步失败了，错误信息是：[粘贴错误信息]，请帮我分析原因
```

---

## 📌 注意事项

1. **首次使用**必须完成飞书应用配置（第 2 步）
2. **图片路径**必须使用 `images/` 文件夹（相对路径）
3. **配置文件**(`config.json`) 包含敏感信息，不要分享给他人
4. **网络连接**需要能访问 `open.feishu.cn`
5. **飞书账号**需要有创建文档的权限

---

## 📚 扩展阅读

- [飞书开放平台文档](https://open.feishu.cn/document/home/introduction)
- [Markdown 语法指南](https://www.markdownguide.org/)
- [Obsidian 官方网站](https://obsidian.md/)（如果你使用 Obsidian）
- [Typora 官方网站](https://typora.io/)（如果你使用 Typora）

---

## 🚧 未来计划

- [x] ✅ ~~支持代码块同步~~ **已完成**
- [x] ✅ ~~支持超链接~~ **已完成**
- [x] ✅ ~~支持删除线、下划线、高亮~~ **已完成**
- [x] ✅ ~~支持行内代码~~ **已完成**
- [x] ✅ ~~支持表格转换~~ **已完成**
- [x] ✅ ~~支持任务列表~~ **已完成**
- [x] ✅ ~~图片并发上传优化~~ **已完成**
- [ ] 批量同步多个文档
- [ ] 增量更新（检测文档变化）
- [ ] 双向同步（飞书 → Markdown）
- [ ] 图片自动压缩
- [ ] 支持更多 Markdown 编辑器的特殊语法

---

## 📄 许可证

MIT License

---

## 🤝 贡献与反馈

如果你遇到问题或有改进建议：

1. **在 Claude Code 中**直接描述问题，Claude 会帮你排查
2. 提交 Issue 到项目仓库
3. 提交 Pull Request 贡献代码

欢迎贡献！让这个工具更好用 🎉


