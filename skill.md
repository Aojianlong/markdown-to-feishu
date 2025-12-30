---
name: obsidian-to-feishu
description: 将 Obsidian Markdown 文章（含本地图片）同步到飞书云文档
---

# Obsidian to 飞书同步

将 Obsidian Markdown 文章转换并上传到飞书云文档，自动处理图片上传和格式转换。

## 功能特性

- ✅ 自动上传本地图片到飞书云空间
- ✅ 保留图片宽度设置（w50/w30）
- ✅ 转换 Markdown 为飞书云文档格式
- ✅ 保留 HTML 样式标记（颜色、粗体等）
- ✅ 一键同步，返回飞书文档链接

## 使用方法

### 基本用法

```bash
# 同步单个文档
/obsidian-to-feishu <markdown-file-path>

# 示例
/obsidian-to-feishu "D:\obsidian\notes\Projects\article.md"
```

### 参数说明

- `<markdown-file-path>`: Obsidian Markdown 文件的完整路径
- 图片必须放在与 Markdown 文件同级的 `images/` 目录下

## 首次使用配置

在首次使用前，需要配置飞书应用凭证：

1. 创建飞书应用（https://open.feishu.cn/app）
2. 获取 App ID 和 App Secret
3. 运行配置命令：
   ```bash
   cd ~/.claude/skills/obsidian-to-feishu
   python setup.py init
   ```

详细配置步骤请参考 README.md。

## 支持的 Markdown 语法

| 语法 | 飞书转换 |
|------|---------|
| `# 标题` | 一级标题 |
| `## 标题` | 二级标题 |
| `### 标题` | 三级标题 |
| `**粗体**` | 粗体文本 |
| `<font color="red">文本</font>` | 红色文本 |
| `> 引用` | 引用块 |
| `- 列表` | 无序列表 |
| `1. 有序` | 有序列表 |
| `![w50](images/pic.jpg)` | 50% 宽度图片 |
| `![w30](images/pic.jpg)` | 30% 宽度图片 |

## 示例

输入 Markdown 文件：

```markdown
# 产品教程

这是一个**重要提示**：<font color="red">请务必阅读</font>

![w50](images/screenshot1.jpg)

## 功能说明

- 功能 1
- 功能 2
```

同步后的飞书云文档将保留所有格式和图片。

## 工作流程

1. 解析 Markdown 文件
2. 提取图片引用和宽度信息
3. 上传图片到飞书云空间
4. 转换为飞书 Block 格式
5. 创建飞书云文档
6. 返回文档链接

## 注意事项

- 图片必须放在 `images/` 目录下
- 支持 JPG、JPEG、PNG、GIF 格式
- 单张图片大小不超过 20MB
- 需要稳定的网络连接

## 技术支持

如遇问题，请检查：
- 飞书应用权限是否正确配置
- App ID 和 App Secret 是否有效
- 图片路径是否正确
- 网络连接是否正常
