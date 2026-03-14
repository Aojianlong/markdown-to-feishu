"""
Block 格式转换器
将解析后的 Markdown 转换为飞书云文档 Block 格式
"""

from typing import List, Dict, Optional
from urllib.parse import quote
from tools.html_parser import HtmlTableParser


class BlockConverter:
    """将解析后的 Markdown 转换为飞书 Block 格式"""

    # 飞书代码语言映射（飞书支持的语言ID）
    LANGUAGE_MAP = {
        'python': 49,
        'javascript': 30,
        'java': 29,
        'go': 22,
        'cpp': 9,
        'c': 10,
        'csharp': 8,
        'php': 43,
        'ruby': 52,
        'rust': 53,
        'typescript': 63,
        'sql': 56,
        'bash': 7,
        'shell': 60,
        'json': 28,
        'xml': 66,
        'yaml': 67,
        'markdown': 39,
        'html': 24,
        'css': 12,
        'plaintext': 1,
        '': 1  # 未指定语言时使用 PlainText
    }

    # 飞书颜色映射
    COLOR_MAP = {
        'red': 1,      # 红色
        'orange': 2,   # 橙色
        'yellow': 3,   # 黄色
        'green': 4,    # 绿色
        'blue': 5,     # 蓝色
        'purple': 6,   # 紫色
        'gray': 7,     # 灰色
    }

    # 默认文档宽度（像素）
    DEFAULT_DOC_WIDTH = 800

    def __init__(self, doc_width: int = DEFAULT_DOC_WIDTH):
        """
        初始化转换器

        Args:
            doc_width: 文档宽度（像素），用于计算图片百分比宽度
        """
        self.doc_width = doc_width

    def convert_to_blocks(self, parsed_data: List[Dict],
                         image_tokens: Dict[str, Dict]) -> List[Dict]:
        """
        转换为飞书 Block 结构

        Args:
            parsed_data: 解析后的 Markdown 数据
            image_tokens: 图片路径到 token 信息的映射
                         格式: {path: {'file_token': str, 'width': int, 'height': int}}

        Returns:
            飞书 Block 列表
        """
        blocks = []

        for item in parsed_data:
            item_type = item['type']

            if item_type == 'heading':
                blocks.append(self._create_heading_block(item))
            elif item_type == 'paragraph':
                blocks.append(self._create_text_block(item))
            elif item_type == 'image':
                blocks.append(self._create_image_block(item, image_tokens))
            elif item_type == 'bullet':
                blocks.append(self._create_bullet_block(item))
            elif item_type == 'ordered':
                blocks.append(self._create_ordered_block(item))
            elif item_type == 'quote':
                blocks.append(self._create_quote_block(item))
            elif item_type == 'divider':
                blocks.append(self._create_divider_block())
            elif item_type == 'code':
                blocks.append(self._create_code_block(item))
            elif item_type == 'table':
                blocks.append(self._create_table_block(item))
            elif item_type == 'html_table':
                blocks.append(self._create_html_table_block(item))
            elif item_type == 'mermaid':
                blocks.append(self._create_mermaid_block(item))
            elif item_type == 'task':
                blocks.append(self._create_task_block(item))

        return blocks

    def _create_heading_block(self, item: Dict) -> Dict:
        """创建标题 Block"""
        level = item['level']
        if level < 1:
            level = 1
        elif level > 9:
            level = 9
        segments = item.get('segments', [{'text': item['content']}])

        # 飞书标题 block_type: 3-11 对应 H1-H9
        block_type = level + 2  # H1=3, H2=4, ..., H9=11

        return {
            "block_type": block_type,
            f"heading{level}": {
                "elements": self._convert_text_elements(segments)
            }
        }

    def _create_text_block(self, item: Dict) -> Dict:
        """创建文本 Block"""
        segments = item.get('segments', [{'text': item['content']}])

        return {
            "block_type": 2,  # 文本块
            "text": {
                "elements": self._convert_text_elements(segments)
            }
        }

    def _create_image_block(self, item: Dict, image_tokens: Dict[str, Dict] = None) -> Dict:
        """
        创建图片 Block（空占位符）

        注意: 飞书API要求先创建空的图片块,然后再上传图片到该块
        """
        return {
            "block_type": 27,  # 图片块
            "image": {}  # 空占位符
        }

    def _create_bullet_block(self, item: Dict) -> Dict:
        """创建无序列表 Block"""
        segments = item.get('segments', [{'text': item['content']}])

        return {
            "block_type": 12,  # 无序列表
            "bullet": {
                "elements": self._convert_text_elements(segments)
            }
        }

    def _create_ordered_block(self, item: Dict) -> Dict:
        """创建原生有序列表 Block (block_type 13)"""
        segments = item.get('segments', [{'text': item['content']}])

        return {
            "block_type": 13,  # 原生有序列表
            "ordered": {
                "elements": self._convert_text_elements(segments)
            }
        }

    def _create_quote_block(self, item: Dict) -> Dict:
        """
        创建引用 Block

        引用块可能包含多行文本和列表项,我们将其合并为一个多行文本块
        保留列表标记(如 "- 文本")
        """
        content = item['content']

        # 如果内容包含换行(多行引用),需要为每行创建独立的text_run
        lines = content.split('\n')
        elements = []

        for i, line in enumerate(lines):
            if line.strip():
                # 解析这一行的样式(保留列表标记)
                segments = self.parse_inline_styles(line) if hasattr(self, 'parse_inline_styles') else [{'text': line}]
                elements.extend(self._convert_text_elements(segments))
                # 添加换行(使用文本换行符)
                if i != len(lines) - 1:  # 不是最后一行
                    elements.append({"text_run": {"content": "\n"}})

        return {
            "block_type": 15,  # 引用块
            "quote": {
                "elements": elements if elements else [{"text_run": {"content": content}}]
            }
        }

    def parse_inline_styles(self, text: str) -> List[Dict]:
        """简单的样式解析(调用parser的方法)"""
        # 这里简化处理,只返回基本文本
        # 实际应该调用MarkdownParser的parse_inline_styles
        from tools.markdown_parser import MarkdownParser
        parser = MarkdownParser()
        return parser.parse_inline_styles(text)

    def _create_divider_block(self) -> Dict:
        """创建分隔线 Block"""
        return {
            "block_type": 22,  # 分隔线
            "divider": {}
        }

    def _create_code_block(self, item: Dict) -> Dict:
        """创建代码块 Block"""
        language = item.get('language', '').lower()
        language_id = self.LANGUAGE_MAP.get(language, 1)  # Default to PlainText

        return {
            "block_type": 14,  # 代码块
            "code": {
                "style": {
                    "language": language_id
                },
                "elements": [{"text_run": {"content": item['content']}}]
            }
        }

    def _create_grid_block(self, column_size: int) -> Dict:
        """
        创建分栏 Block

        Args:
            column_size: 列数 (2-5)
        """
        return {
            "block_type": 24,  # 分栏块
            "grid": {
                "column_size": column_size
            }
        }

    def _create_grid_column_block(self, width_ratio: int = None) -> Dict:
        """
        创建分栏列 Block

        Args:
            width_ratio: 当前列占整个分栏的比例 (1-99)
        """
        grid_column = {
            "block_type": 25,  # 分栏列
            "grid_column": {}
        }
        if width_ratio is not None:
            grid_column["grid_column"]["width_ratio"] = width_ratio
        return grid_column

    def _convert_text_elements(self, segments: List[Dict]) -> List[Dict]:
        """
        转换文本片段为飞书 text_run 元素

        Args:
            segments: 文本片段列表，每个片段包含 text 和样式信息

        Returns:
            飞书 text_run 元素列表
        """
        elements = []

        for segment in segments:
            text = segment.get('text', '')
            if not text:
                continue

            element = {
                "text_run": {
                    "content": text
                }
            }

            # 应用样式 - 只在有非默认样式时添加
            style = {}

            if segment.get('bold'):
                style['bold'] = True

            if segment.get('italic'):
                style['italic'] = True

            if segment.get('strikethrough'):
                style['strikethrough'] = True

            if segment.get('underline'):
                style['underline'] = True

            if segment.get('inline_code'):
                style['inline_code'] = True

            if segment.get('highlight'):
                # 飞书高亮使用背景色（黄色）
                style['background_color'] = 3  # 3 = 黄色背景

            if segment.get('color'):
                color_name = segment['color'].lower()
                if color_name in self.COLOR_MAP:
                    style['text_color'] = self.COLOR_MAP[color_name]

            # 处理链接 - 需要URL编码
            if segment.get('link'):
                url = segment['link']
                # URL编码（safe参数保留://和路径中的/）
                encoded_url = quote(url, safe=':/?#[]@!$&\'()*+,;=')
                style['link'] = {
                    'url': encoded_url
                }

            # 只在有样式时添加 text_element_style
            if style:
                element['text_run']['text_element_style'] = style

            elements.append(element)

        return elements

    def _create_table_block(self, item: Dict) -> Dict:
        """
        创建表格 Block

        使用特殊标记,在 main.py 中通过 Markdown 转换 API 处理
        """
        # 重新构建 Markdown 表格文本
        headers = item['headers']
        rows = item['rows']

        # 构建表头
        md_lines = []
        md_lines.append('| ' + ' | '.join(headers) + ' |')
        # 构建分隔线
        md_lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
        # 构建数据行
        for row in rows:
            md_lines.append('| ' + ' | '.join(row) + ' |')

        markdown_text = '\n'.join(md_lines)

        # 返回特殊标记,让 main.py 识别并使用 API 转换
        return {
            "_special_type": "markdown_table",  # 特殊标记
            "markdown": markdown_text,
            "item": item  # 保留原始数据以备用
        }

    def _create_html_table_block(self, item: Dict) -> Dict:
        """创建 HTML 表格 Block（使用特殊标记，在 main.py 中处理）"""
        parser = HtmlTableParser()
        parsed = parser.parse(item['html'])
        return {
            "_special_type": "html_table",
            "parsed": parsed
        }

    def _create_mermaid_block(self, item: Dict) -> Dict:
        """创建 Mermaid Block（fallback 代码块 + 特殊标记）"""
        return {
            "_special_type": "mermaid",
            "code": item['content'],
            "fallback_block": self._create_code_block({
                'language': 'mermaid',
                'content': item['content']
            })
        }

    def _create_task_block(self, item: Dict) -> Dict:
        """创建任务列表 Block"""
        segments = item.get('segments', [{'text': item['content']}])
        checked = item.get('checked', False)

        return {
            "block_type": 17,  # 任务块 (todo)
            "todo": {
                "elements": self._convert_text_elements(segments),
                "style": {
                    "done": checked  # true 表示已完成
                }
            }
        }


# 测试代码
if __name__ == '__main__':
    converter = BlockConverter()

    # 测试数据
    test_data = [
        {
            'type': 'heading',
            'level': 1,
            'content': '标题测试',
            'segments': [{'text': '标题测试'}]
        },
        {
            'type': 'paragraph',
            'content': '这是普通文本',
            'segments': [
                {'text': '这是'},
                {'text': '粗体', 'bold': True},
                {'text': '文本'}
            ]
        },
        {
            'type': 'image',
            'path': 'images/test.jpg',
            'width': 50
        }
    ]

    image_tokens = {
        'images/test.jpg': {
            'file_token': 'test_token_123',
            'width': 1200,
            'height': 800
        }
    }

    blocks = converter.convert_to_blocks(test_data, image_tokens)

    import json
    print("转换结果:")
    print(json.dumps(blocks, indent=2, ensure_ascii=False))
