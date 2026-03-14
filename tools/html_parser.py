"""
HTML 表格解析器
将 HTML <table> 转换为飞书文档可用的结构化数据
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup, NavigableString, Tag


class HtmlTableParser:
    """解析 HTML <table> 为结构化表格数据，支持单元格内嵌套列表和富文本"""

    def parse(self, html: str) -> Dict:
        """
        解析 <table>...</table> HTML

        Args:
            html: 完整的 HTML 表格字符串

        Returns:
            {
                'row_count': int,
                'col_count': int,
                'cells': [[CellContent, ...], ...]  # row x col
            }
            其中 CellContent 是 block 列表:
            [
                {'type': 'text', 'segments': [...]},
                {'type': 'ordered', 'items': [...], 'indent': 0},
                ...
            ]
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        if not table:
            return {'row_count': 0, 'col_count': 0, 'cells': []}

        rows_data = []
        max_cols = 0

        # 收集 thead 和 tbody 中的所有行
        all_rows = []
        thead = table.find('thead')
        if thead:
            all_rows.extend(thead.find_all('tr'))
        tbody = table.find('tbody')
        if tbody:
            all_rows.extend(tbody.find_all('tr'))
        # 如果没有 thead/tbody，直接找 tr
        if not all_rows:
            all_rows = table.find_all('tr')

        for tr in all_rows:
            cells = tr.find_all(['td', 'th'])
            row = []
            for cell in cells:
                colspan = int(cell.get('colspan', 1))
                cell_content = self._parse_cell(cell)
                row.append(cell_content)
                # colspan > 1 时，填充空 cell
                for _ in range(colspan - 1):
                    row.append([{'type': 'text', 'segments': [{'text': ' '}]}])
            rows_data.append(row)
            if len(row) > max_cols:
                max_cols = len(row)

        # 补齐列数不足的行
        for row in rows_data:
            while len(row) < max_cols:
                row.append([{'type': 'text', 'segments': [{'text': ' '}]}])

        return {
            'row_count': len(rows_data),
            'col_count': max_cols,
            'cells': rows_data
        }

    def _parse_cell(self, cell: Tag) -> List[Dict]:
        """
        解析单个 <td>/<th> 的内容为 block 列表

        Returns:
            block 列表，每个 block 是 {type: 'text'|'ordered'|'bullet', ...}
        """
        blocks = []
        current_segments = []

        def flush_text():
            nonlocal current_segments
            if current_segments:
                # 合并连续空白 segment
                merged = self._merge_segments(current_segments)
                if merged:
                    blocks.append({'type': 'text', 'segments': merged})
                current_segments = []

        for child in cell.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text.strip():
                    current_segments.extend(self._parse_text_node(text))
            elif isinstance(child, Tag):
                if child.name == 'ol':
                    flush_text()
                    blocks.extend(self._parse_ol(child, depth=0))
                elif child.name == 'ul':
                    flush_text()
                    blocks.extend(self._parse_ul(child, depth=0))
                elif child.name == 'br':
                    current_segments.append({'text': '\n'})
                elif child.name == 'strong' or child.name == 'b':
                    current_segments.extend(self._parse_inline_with_style(child, bold=True))
                elif child.name == 'em' or child.name == 'i':
                    current_segments.extend(self._parse_inline_with_style(child, italic=True))
                elif child.name == 'a':
                    href = child.get('href', '')
                    text = child.get_text()
                    seg = {'text': text}
                    if href:
                        seg['link'] = href
                    current_segments.append(seg)
                elif child.name == 'p':
                    # <p> 标签 — 先 flush 前面的文本，再处理 p 内容
                    flush_text()
                    p_segments = self._parse_inline_children(child)
                    if p_segments:
                        blocks.append({'type': 'text', 'segments': p_segments})
                elif child.name == 'code':
                    current_segments.append({'text': child.get_text(), 'inline_code': True})
                else:
                    # 其他标签，提取文本
                    text = child.get_text()
                    if text.strip():
                        current_segments.append({'text': text})

        flush_text()

        # 如果没有任何 block，至少返回一个空文本 block
        if not blocks:
            blocks.append({'type': 'text', 'segments': [{'text': ' '}]})

        return blocks

    def _parse_ol(self, ol: Tag, depth: int = 0) -> List[Dict]:
        """递归解析 <ol>，返回有序列表 block 列表"""
        items = []
        for li in ol.find_all('li', recursive=False):
            # 提取 li 的直接文本内容（不包括子 ol/ul）
            segments = self._parse_li_content(li)
            items.append({
                'type': 'ordered',
                'indent': depth,
                'segments': segments
            })
            # 处理嵌套的 ol/ul
            for sub_list in li.find_all(['ol', 'ul'], recursive=False):
                if sub_list.name == 'ol':
                    items.extend(self._parse_ol(sub_list, depth=depth + 1))
                else:
                    items.extend(self._parse_ul(sub_list, depth=depth + 1))
        return items

    def _parse_ul(self, ul: Tag, depth: int = 0) -> List[Dict]:
        """递归解析 <ul>，返回无序列表 block 列表"""
        items = []
        for li in ul.find_all('li', recursive=False):
            segments = self._parse_li_content(li)
            items.append({
                'type': 'bullet',
                'indent': depth,
                'segments': segments
            })
            for sub_list in li.find_all(['ol', 'ul'], recursive=False):
                if sub_list.name == 'ol':
                    items.extend(self._parse_ol(sub_list, depth=depth + 1))
                else:
                    items.extend(self._parse_ul(sub_list, depth=depth + 1))
        return items

    def _parse_li_content(self, li: Tag) -> List[Dict]:
        """解析 <li> 的直接文本内容（不含子列表）"""
        segments = []
        for child in li.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text.strip():
                    segments.append({'text': text.strip()})
            elif isinstance(child, Tag):
                if child.name in ('ol', 'ul'):
                    # 跳过子列表，由外层递归处理
                    continue
                elif child.name == 'strong' or child.name == 'b':
                    segments.extend(self._parse_inline_with_style(child, bold=True))
                elif child.name == 'em' or child.name == 'i':
                    segments.extend(self._parse_inline_with_style(child, italic=True))
                elif child.name == 'a':
                    href = child.get('href', '')
                    text = child.get_text()
                    seg = {'text': text}
                    if href:
                        seg['link'] = href
                    segments.append(seg)
                elif child.name == 'code':
                    segments.append({'text': child.get_text(), 'inline_code': True})
                elif child.name == 'br':
                    segments.append({'text': '\n'})
                else:
                    text = child.get_text()
                    if text.strip():
                        segments.append({'text': text})

        if not segments:
            segments = [{'text': ' '}]
        return segments

    def _parse_inline_with_style(self, tag: Tag, bold: bool = False, italic: bool = False) -> List[Dict]:
        """解析带样式的行内标签（如 <strong>），支持内部嵌套"""
        segments = []
        for child in tag.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text:
                    seg = {'text': text}
                    if bold:
                        seg['bold'] = True
                    if italic:
                        seg['italic'] = True
                    segments.append(seg)
            elif isinstance(child, Tag):
                if child.name == 'a':
                    href = child.get('href', '')
                    text = child.get_text()
                    seg = {'text': text}
                    if href:
                        seg['link'] = href
                    if bold:
                        seg['bold'] = True
                    if italic:
                        seg['italic'] = True
                    segments.append(seg)
                elif child.name == 'br':
                    segments.append({'text': '\n'})
                elif child.name == 'em' or child.name == 'i':
                    segments.extend(self._parse_inline_with_style(child, bold=bold, italic=True))
                elif child.name == 'strong' or child.name == 'b':
                    segments.extend(self._parse_inline_with_style(child, bold=True, italic=italic))
                else:
                    text = child.get_text()
                    if text:
                        seg = {'text': text}
                        if bold:
                            seg['bold'] = True
                        if italic:
                            seg['italic'] = True
                        segments.append(seg)
        return segments

    def _parse_inline_children(self, tag: Tag) -> List[Dict]:
        """解析标签的所有行内子元素"""
        segments = []
        for child in tag.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text.strip():
                    segments.append({'text': text})
            elif isinstance(child, Tag):
                if child.name == 'strong' or child.name == 'b':
                    segments.extend(self._parse_inline_with_style(child, bold=True))
                elif child.name == 'em' or child.name == 'i':
                    segments.extend(self._parse_inline_with_style(child, italic=True))
                elif child.name == 'a':
                    href = child.get('href', '')
                    text = child.get_text()
                    seg = {'text': text}
                    if href:
                        seg['link'] = href
                    segments.append(seg)
                elif child.name == 'br':
                    segments.append({'text': '\n'})
                elif child.name == 'code':
                    segments.append({'text': child.get_text(), 'inline_code': True})
                else:
                    text = child.get_text()
                    if text.strip():
                        segments.append({'text': text})
        return segments

    def _parse_text_node(self, text: str) -> List[Dict]:
        """解析纯文本节点"""
        text = text.strip()
        if text:
            return [{'text': text}]
        return []

    def _merge_segments(self, segments: List[Dict]) -> List[Dict]:
        """合并连续的纯文本 segment，去除开头结尾的空换行"""
        if not segments:
            return []

        # 去除开头的纯换行
        while segments and segments[0].get('text', '').strip() == '' and len(segments[0]) == 1:
            segments = segments[1:]

        # 去除结尾的纯换行
        while segments and segments[-1].get('text', '').strip() == '' and len(segments[-1]) == 1:
            segments = segments[:-1]

        if not segments:
            return [{'text': ' '}]

        return segments
