"""
Markdown 解析器
解析 Obsidian Markdown 文件，提取结构化数据
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class MarkdownParser:
    """解析 Obsidian Markdown 文件"""

    # 图片引用正则：![alt](path)
    IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')

    # HTML 字体颜色标签：<font color="red">text</font>
    FONT_COLOR_PATTERN = re.compile(r'<font\s+color="([^"]+)">([^<]+)</font>')

    # 粗体标记：**text**
    BOLD_PATTERN = re.compile(r'\*\*([^\*]+)\*\*')

    # 删除线：~~text~~
    STRIKETHROUGH_PATTERN = re.compile(r'~~([^~]+)~~')

    # 下划线：<u>text</u>
    UNDERLINE_PATTERN = re.compile(r'<u>([^<]+)</u>')

    # 高亮/标记：==text== 或 <mark>text</mark>
    HIGHLIGHT_PATTERN = re.compile(r'(==([^=]+)==|<mark>([^<]+)</mark>)')

    # 标题：# 标题
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$')

    # 无序列表：- item 或 * item
    BULLET_PATTERN = re.compile(r'^(\s*)([-\*])\s+(.+)$')

    # 有序列表：1. item
    ORDERED_PATTERN = re.compile(r'^(\s*)(\d+)\.\s+(.+)$')

    # 代码块：```language\ncode\n``` (多行)
    CODE_BLOCK_PATTERN = re.compile(r'^```(\w*)\n(.*?)\n```$', re.MULTILINE | re.DOTALL)

    # 行内代码：`code`
    INLINE_CODE_PATTERN = re.compile(r'`([^`]+)`')

    # 引用块：> text (支持前置缩进)
    QUOTE_PATTERN = re.compile(r'^(\s*)>\s+(.+)$')

    # 分隔线：--- 或 ***
    DIVIDER_PATTERN = re.compile(r'^(---|_{3,}|\*{3,})$')

    # 表格行（检测是否为表格）
    TABLE_ROW_PATTERN = re.compile(r'^\|(.+)\|$')

    # 表格分隔行（| --- | --- |）
    TABLE_SEPARATOR_PATTERN = re.compile(r'^\|[\s\-:|]+\|$')

    # 任务列表：- [ ] 或 - [x]
    TASK_LIST_PATTERN = re.compile(r'^(\s*)[-\*]\s+\[([ xX])\]\s+(.+)$')

    def parse_file(self, md_path: Path) -> List[Dict]:
        """
        解析 Markdown 文件，返回结构化数据

        Args:
            md_path: Markdown 文件路径

        Returns:
            结构化数据列表，每个元素包含 type 和对应的内容
        """
        with open(md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 预扫描 HTML 表格范围
        html_table_ranges = self._find_html_table_ranges(lines)

        result = []
        i = 0
        in_quote_block = False
        quote_lines = []
        in_code_block = False
        code_lines = []
        code_language = ''

        while i < len(lines):
            line = lines[i].rstrip('\n')

            # HTML 表格检测（优先于其他解析）
            if i in html_table_ranges:
                # 先结束引用块
                if in_quote_block:
                    result.append({
                        'type': 'quote',
                        'content': '\n'.join(quote_lines)
                    })
                    quote_lines = []
                    in_quote_block = False

                end = html_table_ranges[i]
                html = '\n'.join(l.rstrip('\n') for l in lines[i:end + 1])
                result.append({'type': 'html_table', 'html': html})
                i = end + 1
                continue

            # 检测代码块开始/结束
            if line.strip().startswith('```'):
                if not in_code_block:
                    # 开始代码块
                    in_code_block = True
                    code_language = line.strip()[3:].strip()  # 提取语言标识
                    code_lines = []
                else:
                    # 结束代码块
                    in_code_block = False
                    if code_language.lower() == 'mermaid':
                        result.append({
                            'type': 'mermaid',
                            'content': '\n'.join(code_lines)
                        })
                    else:
                        result.append({
                            'type': 'code',
                            'language': code_language,
                            'content': '\n'.join(code_lines)
                        })
                    code_lines = []
                    code_language = ''
                i += 1
                continue

            # 如果在代码块中，直接收集行
            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # 空行
            if not line.strip():
                if in_quote_block:
                    # 结束引用块
                    result.append({
                        'type': 'quote',
                        'content': '\n'.join(quote_lines)
                    })
                    quote_lines = []
                    in_quote_block = False
                i += 1
                continue

            # 分隔线
            if self.DIVIDER_PATTERN.match(line):
                result.append({'type': 'divider'})
                i += 1
                continue

            # 标题
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                content = heading_match.group(2)
                result.append({
                    'type': 'heading',
                    'level': level,
                    'content': content,
                    'segments': self.parse_inline_styles(content)
                })
                i += 1
                continue

            # 图片（可能一行有多个）
            if self.IMAGE_PATTERN.search(line):
                images = self.extract_image_info(line)
                for width, path, alt in images:
                    result.append({
                        'type': 'image',
                        'path': path,
                        'width': width,
                        'alt': alt
                    })
                i += 1
                continue

            # 引用块
            quote_match = self.QUOTE_PATTERN.match(line)
            if quote_match:
                in_quote_block = True
                content = quote_match.group(2)  # 第2组是内容(第1组是缩进)
                # 保留引用内容的原始格式(包括列表标记)
                quote_lines.append(content)
                i += 1
                continue

            # 表格（检测表格行）
            if self.TABLE_ROW_PATTERN.match(line):
                # 收集完整的表格
                table_lines = [line]
                j = i + 1
                while j < len(lines) and self.TABLE_ROW_PATTERN.match(lines[j].rstrip('\n')):
                    table_lines.append(lines[j].rstrip('\n'))
                    j += 1

                # 解析表格
                table_data = self._parse_table(table_lines)
                if table_data:
                    result.append(table_data)
                    i = j
                    continue

            # 任务列表
            task_match = self.TASK_LIST_PATTERN.match(line)
            if task_match:
                indent = len(task_match.group(1))
                checked = task_match.group(2).lower() == 'x'
                content = task_match.group(3)
                result.append({
                    'type': 'task',
                    'indent': indent,
                    'checked': checked,
                    'content': content,
                    'segments': self.parse_inline_styles(content)
                })
                i += 1
                continue

            # 无序列表
            bullet_match = self.BULLET_PATTERN.match(line)
            if bullet_match:
                indent = len(bullet_match.group(1))
                content = bullet_match.group(3)
                result.append({
                    'type': 'bullet',
                    'indent': indent,
                    'content': content,
                    'segments': self.parse_inline_styles(content)
                })
                i += 1
                continue

            # 有序列表
            ordered_match = self.ORDERED_PATTERN.match(line)
            if ordered_match:
                indent = len(ordered_match.group(1))
                number = int(ordered_match.group(2))
                content = ordered_match.group(3)
                result.append({
                    'type': 'ordered',
                    'indent': indent,
                    'number': number,
                    'content': content,
                    'segments': self.parse_inline_styles(content)
                })
                i += 1
                continue

            # 普通段落
            result.append({
                'type': 'paragraph',
                'content': line,
                'segments': self.parse_inline_styles(line)
            })
            i += 1

        # 结束时可能还有未关闭的引用块
        if in_quote_block:
            result.append({
                'type': 'quote',
                'content': '\n'.join(quote_lines)
            })

        return result

    def extract_image_info(self, line: str) -> List[Tuple[int, str, str]]:
        """
        提取图片信息

        Args:
            line: 包含图片引用的行

        Returns:
            (width, path, alt_text) 元组列表
            width 为百分比（50, 30, 100等），默认100
        """
        images = []
        for match in self.IMAGE_PATTERN.finditer(line):
            alt = match.group(1)  # 如 "w50" 或 "w30"
            path = match.group(2)

            # 提取宽度信息
            width = 100  # 默认全宽
            if alt.startswith('w'):
                try:
                    width = int(alt[1:])
                except ValueError:
                    pass

            images.append((width, path, alt))

        return images

    def parse_inline_styles(self, text: str) -> List[Dict]:
        """
        解析行内样式：粗体、斜体、删除线、下划线、高亮、HTML 颜色标签、链接等

        支持嵌套样式,如: **<font color="red">文本</font>**

        Args:
            text: 文本内容

        Returns:
            文本片段列表，每个片段包含 text 和样式信息
        """
        # 如果没有任何样式标记,直接返回
        if not any(char in text for char in ['*', '<', '=', '~', '[', '`']):
            return [{'text': text}]

        segments = []

        # 先处理粗体和斜体（注意顺序：先粗体再斜体，避免冲突）
        # 粗体：**text**
        # 斜体：*text*

        # 使用统一的样式处理方法
        segments = self._parse_bold_and_italic(text)

        return segments if segments else [{'text': text}]

    def _parse_bold_and_italic(self, text: str) -> List[Dict]:
        """
        解析粗体和斜体（需要先处理粗体，避免与斜体冲突）

        Args:
            text: 文本内容

        Returns:
            文本片段列表
        """
        segments = []

        # 先处理粗体 **text**
        bold_pattern = re.compile(r'\*\*(.+?)\*\*')

        pos = 0
        for bold_match in bold_pattern.finditer(text):
            # 添加粗体前的文本（可能包含斜体）
            if pos < bold_match.start():
                before_text = text[pos:bold_match.start()]
                # 处理这段文本中可能的斜体、颜色标签和链接
                segments.extend(self._parse_italic_colors_links(before_text, bold=False))

            # 处理粗体内的内容
            bold_content = bold_match.group(1)
            # 粗体内可能有颜色标签和链接，但不应该有斜体（已经是粗体了）
            segments.extend(self._parse_colors_and_links(bold_content, bold=True, italic=False))

            pos = bold_match.end()

        # 添加剩余文本（可能包含斜体）
        if pos < len(text):
            remaining = text[pos:]
            segments.extend(self._parse_italic_colors_links(remaining, bold=False))

        # 如果没有粗体标记,直接处理斜体、颜色和链接
        if pos == 0:
            segments = self._parse_italic_colors_links(text, bold=False)

        return segments

    def _parse_italic_colors_links(self, text: str, bold: bool = False) -> List[Dict]:
        """
        解析斜体、颜色和链接

        Args:
            text: 文本内容
            bold: 是否应用粗体样式

        Returns:
            文本片段列表
        """
        segments = []

        # 处理斜体 *text* （注意：不匹配 **）
        italic_pattern = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)')

        pos = 0
        for italic_match in italic_pattern.finditer(text):
            # 添加斜体前的文本
            if pos < italic_match.start():
                before_text = text[pos:italic_match.start()]
                # 处理这段文本中可能的颜色标签和链接
                segments.extend(self._parse_colors_and_links(before_text, bold=bold, italic=False))

            # 处理斜体内的内容
            italic_content = italic_match.group(1)
            # 斜体内可能有颜色标签和链接
            segments.extend(self._parse_colors_and_links(italic_content, bold=bold, italic=True))

            pos = italic_match.end()

        # 添加剩余文本
        if pos < len(text):
            remaining = text[pos:]
            segments.extend(self._parse_colors_and_links(remaining, bold=bold, italic=False))

        # 如果没有斜体标记,直接处理颜色和链接
        if pos == 0:
            segments = self._parse_colors_and_links(text, bold=bold, italic=False)

        return segments

    def _parse_colors_and_links(self, text: str, bold: bool = False, italic: bool = False) -> List[Dict]:
        """
        解析文本中的样式标记：颜色、链接、删除线、下划线、高亮、行内代码

        Args:
            text: 文本内容
            bold: 是否应用粗体样式
            italic: 是否应用斜体样式

        Returns:
            文本片段列表
        """
        segments = []
        pos = 0

        # 匹配所有样式标记
        color_pattern = re.compile(r'<font\s+color="([^"]+)">([^<]+)</font>')
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
        strikethrough_pattern = re.compile(r'~~([^~]+)~~')
        underline_pattern = re.compile(r'<u>([^<]+)</u>')
        highlight_pattern = re.compile(r'(==([^=]+)==|<mark>([^<]+)</mark>)')
        inline_code_pattern = re.compile(r'`([^`]+)`')

        # 收集所有匹配
        matches = []
        for m in color_pattern.finditer(text):
            matches.append(('color', m.start(), m.end(), m.group(2), m.group(1)))
        for m in link_pattern.finditer(text):
            matches.append(('link', m.start(), m.end(), m.group(1), m.group(2)))
        for m in strikethrough_pattern.finditer(text):
            matches.append(('strikethrough', m.start(), m.end(), m.group(1), None))
        for m in underline_pattern.finditer(text):
            matches.append(('underline', m.start(), m.end(), m.group(1), None))
        for m in highlight_pattern.finditer(text):
            # highlight_pattern 有两个捕获组：==text== 或 <mark>text</mark>
            content = m.group(2) if m.group(2) else m.group(3)
            matches.append(('highlight', m.start(), m.end(), content, None))
        for m in inline_code_pattern.finditer(text):
            matches.append(('code', m.start(), m.end(), m.group(1), None))

        matches.sort(key=lambda x: x[1])

        for match in matches:
            match_type, start, end, content, extra = match

            # 添加前面的纯文本
            if pos < start:
                plain_text = text[pos:start]
                if plain_text:
                    seg = {'text': plain_text}
                    if bold:
                        seg['bold'] = True
                    if italic:
                        seg['italic'] = True
                    segments.append(seg)

            # 添加样式文本
            seg = {'text': content}
            if bold:
                seg['bold'] = True
            if italic:
                seg['italic'] = True

            if match_type == 'color':
                seg['color'] = extra
            elif match_type == 'link':
                seg['link'] = extra
            elif match_type == 'strikethrough':
                seg['strikethrough'] = True
            elif match_type == 'underline':
                seg['underline'] = True
            elif match_type == 'highlight':
                seg['highlight'] = True
            elif match_type == 'code':
                seg['inline_code'] = True

            segments.append(seg)
            pos = end

        # 添加剩余文本
        if pos < len(text):
            remaining = text[pos:]
            if remaining:
                seg = {'text': remaining}
                if bold:
                    seg['bold'] = True
                if italic:
                    seg['italic'] = True
                segments.append(seg)

        # 如果没有任何匹配,返回原文本
        if not segments:
            seg = {'text': text}
            if bold:
                seg['bold'] = True
            if italic:
                seg['italic'] = True
            return [seg]

        return segments

    def _find_html_table_ranges(self, lines: List[str]) -> Dict[int, int]:
        """
        预扫描文件，找出所有 HTML <table>...</table> 的行号范围

        Returns:
            {start_line_index: end_line_index, ...}
        """
        ranges = {}
        i = 0
        while i < len(lines):
            line = lines[i].rstrip('\n').strip()
            if line.startswith('<table') and not line.startswith('```'):
                start = i
                # 找到配对的 </table>
                depth = 0
                j = i
                while j < len(lines):
                    l = lines[j].rstrip('\n').strip()
                    # 简单计数 <table 和 </table> 以支持嵌套
                    if l.startswith('<table'):
                        depth += 1
                    if '</table>' in l:
                        depth -= 1
                        if depth == 0:
                            ranges[start] = j
                            i = j + 1
                            break
                    j += 1
                else:
                    # 没找到闭合标签，跳过
                    i += 1
            else:
                i += 1
        return ranges

    def _parse_table(self, table_lines: List[str]) -> Optional[Dict]:
        """
        解析 Markdown 表格

        Args:
            table_lines: 表格的所有行

        Returns:
            表格数据字典，如果解析失败返回 None
        """
        if len(table_lines) < 2:
            return None

        # 第一行是表头
        header_line = table_lines[0]
        headers = [cell.strip() for cell in header_line.strip('|').split('|')]

        # 第二行应该是分隔线
        if not self.TABLE_SEPARATOR_PATTERN.match(table_lines[1]):
            return None

        # 其余行是数据
        rows = []
        for line in table_lines[2:]:
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            # 确保列数一致
            while len(cells) < len(headers):
                cells.append('')
            rows.append(cells[:len(headers)])

        return {
            'type': 'table',
            'headers': headers,
            'rows': rows,
            'col_count': len(headers),
            'row_count': len(rows) + 1  # +1 包括表头
        }


# 测试代码
if __name__ == '__main__':
    parser = MarkdownParser()

    # 测试图片提取
    test_line = '![w50](images/test1.jpg) ![w30](images/test2.jpg)'
    print("图片提取测试:")
    print(parser.extract_image_info(test_line))

    # 测试样式解析
    test_text = '这是**粗体**文本，还有<font color="red">红色</font>文本'
    print("\n样式解析测试:")
    print(parser.parse_inline_styles(test_text))
