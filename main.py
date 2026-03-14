"""
Obsidian to 飞书同步工具
主流程脚本 - 重构版本
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List
from urllib.parse import unquote, urlparse

from tools.markdown_parser import MarkdownParser
from tools.feishu_uploader import FeishuUploader
from tools.block_converter import BlockConverter
from config_utils import load_runtime_config


def load_config() -> Dict:
    """加载配置文件"""
    config = load_runtime_config()

    if not config:
        print("错误：配置文件不存在！")
        print("请先运行: python scripts/setup.py init")
        sys.exit(1)

    try:
        # 通过一次序列化校验配置对象可被 JSON 正常表示
        json.dumps(config, ensure_ascii=False)
    except json.JSONDecodeError as e:
        print(f"错误：配置文件格式无效: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误：无法读取配置文件: {e}")
        sys.exit(1)

    # 验证配置
    validation_errors = validate_config(config)
    if validation_errors:
        print("错误：配置验证失败：")
        for error in validation_errors:
            print(f"  - {error}")
        sys.exit(1)

    return config


def resolve_local_image_path(md_path: Path, raw_path: str) -> Path:
    """根据 Markdown 文件目录解析本地图片路径。"""
    normalized = unquote(raw_path.strip())
    parsed = urlparse(normalized)

    if parsed.scheme and len(parsed.scheme) > 1:
        raise ValueError(f"暂不支持远程图片路径: {raw_path}")

    candidate = Path(normalized)
    if candidate.is_absolute():
        return candidate

    return (md_path.parent / candidate).resolve()


def preflight_local_images(md_path: Path, parsed_data: List[Dict]) -> Dict[int, Dict]:
    """预检 Markdown 中引用的本地图片，避免先建空块再失败。"""
    results = {}

    for index, item in enumerate(parsed_data):
        if item.get('type') != 'image':
            continue

        raw_path = item.get('path', '')

        try:
            resolved_path = resolve_local_image_path(md_path, raw_path)
        except ValueError as e:
            results[index] = {
                'ok': False,
                'raw_path': raw_path,
                'error': str(e)
            }
            continue

        if not resolved_path.exists():
            results[index] = {
                'ok': False,
                'raw_path': raw_path,
                'resolved_path': str(resolved_path),
                'error': f"图片不存在: {resolved_path}"
            }
            continue

        if not resolved_path.is_file():
            results[index] = {
                'ok': False,
                'raw_path': raw_path,
                'resolved_path': str(resolved_path),
                'error': f"路径不是文件: {resolved_path}"
            }
            continue

        results[index] = {
            'ok': True,
            'raw_path': raw_path,
            'path': resolved_path
        }

    return results


def validate_config(config: Dict) -> List[str]:
    """
    验证配置文件

    Args:
        config: 配置字典

    Returns:
        错误列表，如果为空则验证通过
    """
    errors = []

    # 验证必需字段
    if 'feishu' not in config:
        errors.append("缺少 'feishu' 配置节")
        return errors  # 无法继续验证

    feishu_config = config['feishu']

    if 'app_id' not in feishu_config:
        errors.append("缺少 'feishu.app_id'")
    elif not feishu_config['app_id'] or feishu_config['app_id'] == 'your_app_id_here':
        errors.append("'feishu.app_id' 未配置或仍为示例值")

    if 'app_secret' not in feishu_config:
        errors.append("缺少 'feishu.app_secret'")
    elif not feishu_config['app_secret'] or feishu_config['app_secret'] == 'your_app_secret_here':
        errors.append("'feishu.app_secret' 未配置或仍为示例值")

    # 验证可选字段的类型和范围
    if 'default_image_width' in config:
        width = config['default_image_width']
        if not isinstance(width, int) or width < 100 or width > 2000:
            errors.append("'default_image_width' 必须是 100-2000 之间的整数")

    if 'width_mapping' in config:
        mapping = config['width_mapping']
        if not isinstance(mapping, dict):
            errors.append("'width_mapping' 必须是字典")
        else:
            for key, value in mapping.items():
                if not isinstance(value, int) or value < 1 or value > 100:
                    errors.append(f"'width_mapping.{key}' 必须是 1-100 之间的整数")

    return errors


def sync_to_feishu(md_file_path: str) -> str:
    """
    主流程：同步 Obsidian 文档到飞书

    Args:
        md_file_path: Markdown 文件路径

    Returns:
        飞书云文档 URL

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件路径无效
    """
    # 加载配置
    config = load_config()
    app_id = config['feishu']['app_id']
    app_secret = config['feishu']['app_secret']

    # 解析和验证路径
    md_path = Path(md_file_path).resolve()  # 解析为绝对路径

    # 验证文件存在
    if not md_path.exists():
        raise FileNotFoundError(f"文件不存在: {md_file_path}")

    # 验证是文件而非目录
    if not md_path.is_file():
        raise ValueError(f"路径不是文件: {md_file_path}")

    # 验证文件扩展名
    if md_path.suffix.lower() != '.md':
        raise ValueError(f"文件必须是 .md 格式: {md_file_path}")

    print(f"开始同步文档: {md_path.name}")
    print("-" * 60)

    # Step 1: 解析 Markdown
    print("[1/4] 解析 Markdown 文件...")
    parser = MarkdownParser()
    parsed_data = parser.parse_file(md_path)
    print(f"[OK] 解析完成，共 {len(parsed_data)} 个元素")

    image_preflight = preflight_local_images(md_path, parsed_data)
    failed_images = [
        (index, info) for index, info in image_preflight.items()
        if not info['ok']
    ]
    if failed_images:
        print(f"[WARNING] 图片预检发现 {len(failed_images)} 个问题，上传时会跳过这些图片以避免生成空块：")
        for index, info in failed_images[:10]:
            print(f"  - 第 {index + 1} 项 {info['raw_path']}: {info['error']}")
        if len(failed_images) > 10:
            print(f"  - 其余 {len(failed_images) - 10} 个问题已省略")

    # Step 2: 创建飞书文档
    uploader = FeishuUploader(app_id, app_secret)
    print("\n[2/4] 创建飞书云文档...")
    doc_title = md_path.stem
    doc_info = uploader.create_document(doc_title)
    document_id = doc_info['document_id']
    doc_url = doc_info['url']
    print(f"[OK] 文档创建成功，ID: {document_id}")

    # 尝试设置文档权限（可能需要额外配置 drive:drive 权限）
    # 如果失败，用户需要手动在飞书中设置权限
    try:
        uploader.set_document_permission(document_id)
    except Exception as e:
        print(f"  [WARNING] 权限设置失败: {e}")
        print(f"  [INFO] 文档已创建，请手动在飞书中设置权限")

    # Step 3: 转换为 Block 格式（图片块为空占位符）
    print("\n[3/4] 转换为飞书格式...")
    converter = BlockConverter(doc_width=config.get('default_image_width', 800))
    blocks = converter.convert_to_blocks(parsed_data, {})  # 不再需要image_tokens
    print(f"[OK] 转换完成，共 {len(blocks)} 个 Block")

    # Step 4: 逐个添加内容到文档
    print("\n[4/4] 添加内容到文档...")

    # 生成飞书文档URL
    if not doc_url:
        doc_url = f"https://bytedance.feishu.cn/docx/{document_id}"

    try:
        total_items = len(parsed_data)
        processed = 0

        # 分批处理，但需要特殊处理图片和有序列表
        batch = []
        batch_start_idx = 0

        def get_validated_image_path(image_index: int, image_item: Dict) -> Path | None:
            """读取图片预检结果，仅对当前要处理的图片做一次判断。"""
            info = image_preflight.get(image_index)
            if not info:
                print(f"    [X] 缺少图片预检结果: {image_item.get('path', '')}")
                return None

            if not info['ok']:
                print(f"    [SKIP] 跳过图片 {image_item.get('path', '')}: {info['error']}")
                return None

            return info['path']

        # 收集 mermaid 数据（用于 Tier 2 输出）
        mermaid_blocks_data = []

        def calc_col_widths(all_rows, total_width=1093):
            """根据每列最大内容长度按比例计算列宽"""
            col_count = len(all_rows[0]) if all_rows else 0
            if col_count == 0:
                return []
            max_lens = [0] * col_count
            for row in all_rows:
                for i, cell in enumerate(row):
                    if i < col_count:
                        cell_len = len(str(cell)) if cell else 0
                        max_lens[i] = max(max_lens[i], cell_len)
            # 保底每列至少算 1 个字符
            max_lens = [max(1, l) for l in max_lens]
            total_len = sum(max_lens)
            widths = [max(50, int(total_width * l / total_len)) for l in max_lens]
            return widths

        def should_flush_batch(current_item):
            """判断是否需要提交当前批次"""
            if not batch:
                return False

            if len(batch) >= 50:
                return True

            current_type = current_item['type']

            # 特殊类型需要先提交当前批次
            if current_type in ('image', 'table', 'html_table', 'mermaid', 'ordered', 'bullet'):
                return True

            return False

        for idx, (item, block) in enumerate(zip(parsed_data, blocks)):
            # 判断是否需要提交当前批次
            if batch and should_flush_batch(item):
                print(f"  添加批次 ({batch_start_idx+1}-{batch_start_idx+len(batch)})...")
                uploader.add_blocks_to_document(document_id, batch)
                processed += len(batch)
                batch = []
                batch_start_idx = idx
                time.sleep(0.3)

            # === 章节标题前插入空行（H1/H2）===
            if item['type'] == 'heading' and item.get('level', 99) <= 2 and idx > 0:
                empty_block = {
                    "block_type": 2,
                    "text": {
                        "elements": [{"text_run": {"content": " "}}]
                    }
                }
                batch.append(empty_block)

            # === 列表组处理（有序/无序）===
            if item['type'] in ('ordered', 'bullet'):
                # 收集连续的列表项（可以混合 ordered 和 bullet，但实际上
                # 应该按连续的同类型分组；这里我们按"连续的列表类型"分组）
                list_group = [(idx, item, block)]
                j = idx + 1
                while j < len(parsed_data) and parsed_data[j]['type'] in ('ordered', 'bullet'):
                    list_group.append((j, parsed_data[j], blocks[j]))
                    j += 1

                # 按连续的同类型子组拆分（ordered 和 bullet 不混合）
                sub_groups = []
                current_sub = [list_group[0]]
                for k in range(1, len(list_group)):
                    if list_group[k][1]['type'] == current_sub[-1][1]['type']:
                        current_sub.append(list_group[k])
                    else:
                        sub_groups.append(current_sub)
                        current_sub = [list_group[k]]
                sub_groups.append(current_sub)

                for sub_group in sub_groups:
                    list_type = sub_group[0][1]['type']
                    list_items = []
                    for _, li_item, li_block in sub_group:
                        list_items.append({
                            'type': li_item['type'],
                            'indent': li_item.get('indent', 0),
                            'segments': li_item.get('segments', [{'text': li_item.get('content', ' ')}]),
                            'block': li_block
                        })

                    print(f"  [{sub_group[0][0]+1}-{sub_group[-1][0]+1}/{total_items}] 创建嵌套{list_type}列表 ({len(list_items)} 项)...")
                    try:
                        uploader.create_nested_list(document_id, list_items, converter)
                        processed += len(list_items)
                        print(f"    [OK] 列表创建成功")
                    except Exception as e:
                        print(f"    [X] 列表创建失败: {e}")
                        # fallback: 逐个添加为扁平块
                        print(f"    [FALLBACK] 尝试逐个添加...")
                        flat_blocks = [li_block for _, _, li_block in sub_group]
                        try:
                            uploader.add_blocks_to_document(document_id, flat_blocks)
                            processed += len(flat_blocks)
                            print(f"    [OK] 扁平列表添加成功")
                        except Exception as e2:
                            print(f"    [X] 扁平列表也失败: {e2}")

                    time.sleep(0.3)

                # 标记后续列表项为已处理
                for skip_idx, _, _ in list_group[1:]:
                    if skip_idx < len(parsed_data):
                        parsed_data[skip_idx] = {'type': 'skip'}

                batch_start_idx = j

            # === 图片处理 ===
            elif item['type'] == 'image':
                consecutive_images = [(idx, item)]
                j = idx + 1
                while j < len(parsed_data) and parsed_data[j]['type'] == 'image':
                    consecutive_images.append((j, parsed_data[j]))
                    j += 1

                valid_consecutive_images = []
                invalid_count = 0
                for image_index, image_item in consecutive_images:
                    image_path = get_validated_image_path(image_index, image_item)
                    if image_path is None:
                        invalid_count += 1
                        continue
                    valid_consecutive_images.append((image_index, image_item, image_path))

                if invalid_count:
                    print(f"  [INFO] 连续图片组中有 {invalid_count} 张图片预检失败，已跳过")

                if len(valid_consecutive_images) > 1:
                    print(f"  [{idx+1}-{j}/{total_items}] 处理并排图片组 ({len(valid_consecutive_images)}张有效图片)")
                    MAX_GRID_COLUMNS = 5
                    total_images = len(valid_consecutive_images)

                    if total_images <= MAX_GRID_COLUMNS:
                        img_batches = [valid_consecutive_images]
                    else:
                        num_rows = (total_images + MAX_GRID_COLUMNS - 1) // MAX_GRID_COLUMNS
                        base_count = total_images // num_rows
                        extra_count = total_images % num_rows
                        img_batches = []
                        start_idx = 0
                        for row in range(num_rows):
                            count = base_count + (1 if row < extra_count else 0)
                            img_batches.append(valid_consecutive_images[start_idx:start_idx + count])
                            start_idx += count

                    for batch_idx, img_batch in enumerate(img_batches):
                        if len(img_batch) == 1:
                            img_idx, img_item, image_path = img_batch[0]
                            img_block = converter._create_image_block(img_item, {})
                            blocks_info = uploader.add_blocks_to_document(document_id, [img_block])
                            if not blocks_info:
                                print(f"      [X] 创建图片块失败")
                                continue
                            image_block_id = blocks_info[0]['block_id']
                            try:
                                uploader.upload_image_to_block(image_path, document_id, image_block_id)
                                print(f"      [OK] 单张图片上传成功")
                                processed += 1
                            except Exception as e:
                                print(f"      [X] 上传失败: {e}")
                                uploader.delete_block(document_id, image_block_id)
                            time.sleep(0.2)
                            continue

                        print(f"    处理第{batch_idx+1}/{len(img_batches)}组 ({len(img_batch)}张)")
                        grid_block = converter._create_grid_block(column_size=len(img_batch))
                        grid_blocks_info = uploader.add_blocks_to_document(document_id, [grid_block])
                        if not grid_blocks_info:
                            print(f"      [X] 创建Grid块失败")
                            continue

                        grid_block_info = grid_blocks_info[0]
                        grid_column_ids = grid_block_info.get('children', [])
                        if len(grid_column_ids) != len(img_batch):
                            print(f"      [X] GridColumn数量不匹配")
                            continue

                        print(f"      [OK] Grid块创建成功，包含{len(grid_column_ids)}个分栏列")
                        time.sleep(0.2)

                        image_upload_tasks = []
                        for img_idx, ((_, img_item, image_path), column_id) in enumerate(zip(img_batch, grid_column_ids)):
                            empty_image_block = converter._create_image_block(img_item, {})
                            image_blocks_info = uploader.add_blocks_to_document(
                                document_id, [empty_image_block], parent_id=column_id
                            )
                            if not image_blocks_info:
                                print(f"        [X] 创建图片块失败")
                                continue
                            image_block_id = image_blocks_info[0]['block_id']
                            image_upload_tasks.append((image_path, document_id, image_block_id))

                        if image_upload_tasks:
                            print(f"      [INFO] 并发上传 {len(image_upload_tasks)} 张图片...")
                            results = uploader.upload_images_batch_parallel(image_upload_tasks, max_workers=3)
                            success_count = sum(1 for r in results if r['success'])
                            fail_count = len(results) - success_count
                            print(f"      [OK] 上传完成: {success_count} 成功, {fail_count} 失败")
                            processed += success_count
                            for result in results:
                                if not result['success']:
                                    print(f"        [X] {Path(result['path']).name}: {result['error']}")

                        time.sleep(0.2)

                elif len(valid_consecutive_images) == 1:
                    valid_index, valid_item, image_path = valid_consecutive_images[0]
                    print(f"  [{idx+1}/{total_items}] 处理图片: {valid_item['path']}")
                    image_block = [blocks[valid_index]]
                    blocks_info = uploader.add_blocks_to_document(document_id, image_block)
                    if blocks_info:
                        image_block_id = blocks_info[0]['block_id']
                        try:
                            uploader.upload_image_to_block(image_path, document_id, image_block_id)
                            print(f"    [OK] 图片上传成功")
                            processed += 1
                        except Exception as e:
                            print(f"    [X] 上传失败: {e}")
                            uploader.delete_block(document_id, image_block_id)
                    else:
                        print(f"    [X] 创建图片块失败")
                    time.sleep(0.3)
                else:
                    print(f"  [{idx+1}-{j}/{total_items}] 当前连续图片组全部跳过")

                batch_start_idx = j
                for skip_idx, _ in consecutive_images[1:]:
                    if skip_idx < len(parsed_data):
                        parsed_data[skip_idx] = {'type': 'skip'}

            elif item['type'] == 'skip':
                continue

            # === Markdown 表格处理 ===
            elif item['type'] == 'table':
                print(f"  [{idx+1}/{total_items}] 处理表格...")
                if block.get('_special_type') == 'markdown_table':
                    table_data = block['item']
                    headers = table_data['headers']
                    rows = table_data['rows']
                    try:
                        table_block_id = uploader.create_table_with_content(document_id, headers, rows)
                        if table_block_id:
                            print(f"    [OK] 表格添加成功 ({len(headers)} 列 × {len(rows)+1} 行)")
                            try:
                                col_widths = calc_col_widths([headers] + rows)
                                uploader.update_table_column_widths(
                                    document_id, table_block_id, len(headers),
                                    col_widths=col_widths
                                )
                                print(f"    [OK] 表格列宽已调整 ({col_widths})")
                            except Exception as e:
                                print(f"    [WARN] 列宽调整失败（不影响内容）: {e}")
                            processed += 1
                        else:
                            print(f"    [X] 表格创建失败")
                    except Exception as e:
                        print(f"    [X] 表格处理失败: {e}")
                else:
                    print(f"    [X] 不支持的表格格式")
                batch_start_idx = idx + 1
                time.sleep(0.5)

            # === HTML 表格处理 ===
            elif item['type'] == 'html_table':
                print(f"  [{idx+1}/{total_items}] 处理 HTML 表格...")
                if block.get('_special_type') == 'html_table':
                    parsed_table = block['parsed']
                    try:
                        table_block_id = uploader.create_rich_table(
                            document_id, parsed_table, converter
                        )
                        if table_block_id:
                            print(f"    [OK] HTML 表格添加成功 ({parsed_table['col_count']} 列 × {parsed_table['row_count']} 行)")
                            try:
                                # 从 HTML 表格的 cells 数据计算每列内容长度
                                html_rows = []
                                for row in parsed_table.get('cells', []):
                                    text_row = []
                                    for cell in row:
                                        cell_text = ''
                                        for block_item in (cell if isinstance(cell, list) else []):
                                            for seg in block_item.get('segments', []):
                                                cell_text += seg.get('text', '')
                                        text_row.append(cell_text)
                                    html_rows.append(text_row)
                                col_widths = calc_col_widths(html_rows)
                                uploader.update_table_column_widths(
                                    document_id, table_block_id, parsed_table['col_count'],
                                    col_widths=col_widths
                                )
                                print(f"    [OK] 表格列宽已调整 ({col_widths})")
                            except Exception as e:
                                print(f"    [WARN] 列宽调整失败（不影响内容）: {e}")
                            processed += 1
                        else:
                            print(f"    [X] HTML 表格创建失败")
                    except Exception as e:
                        print(f"    [X] HTML 表格处理失败: {e}")
                batch_start_idx = idx + 1
                time.sleep(0.5)

            # === Mermaid 处理 ===
            elif item['type'] == 'mermaid':
                print(f"  [{idx+1}/{total_items}] 处理 Mermaid 图...")
                if block.get('_special_type') == 'mermaid':
                    # 先插入 fallback 代码块
                    fallback_block = block['fallback_block']
                    try:
                        fb_info = uploader.add_blocks_to_document(document_id, [fallback_block])
                        fallback_block_id = fb_info[0]['block_id'] if fb_info else None
                        print(f"    [OK] Mermaid 代码块已插入 (fallback)")
                        processed += 1

                        # 收集 mermaid 数据供 Tier 2 处理
                        mermaid_blocks_data.append({
                            'code': block['code'],
                            'fallback_block_id': fallback_block_id
                        })
                    except Exception as e:
                        print(f"    [X] Mermaid 代码块插入失败: {e}")
                batch_start_idx = idx + 1
                time.sleep(0.3)

            else:
                # 普通块：添加到批次
                batch.append(block)

        # 提交最后一批
        if batch:
            print(f"  添加批次 ({batch_start_idx+1}-{batch_start_idx+len(batch)})...")
            uploader.add_blocks_to_document(document_id, batch)
            processed += len(batch)

        print(f"[OK] 内容添加完成 ({processed}/{total_items})")

    except Exception as e:
        print(f"[WARNING] 添加内容时出错: {e}")
        print(f"[INFO] 文档已创建，部分内容可能未能添加。")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"[SUCCESS] 同步完成！")
    print(f"文档标题: {doc_title}")
    print(f"文档链接: {doc_url}")
    print("=" * 60)

    # 输出结构化 JSON（包含 mermaid 数据供 Tier 2 处理）
    if mermaid_blocks_data:
        output = {
            "status": "success",
            "document_id": document_id,
            "url": doc_url,
            "title": doc_title,
            "mermaid_blocks": mermaid_blocks_data
        }
        print("\n---MERMAID_DATA_START---")
        print(json.dumps(output, ensure_ascii=False))
        print("---MERMAID_DATA_END---")

    return doc_url


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python scripts/main.py <markdown-file-path>")
        print("\n示例:")
        print('  python scripts/main.py "D:\\obsidian\\notes\\article.md"')
        sys.exit(1)

    md_file_path = sys.argv[1]

    try:
        doc_url = sync_to_feishu(md_file_path)
    except Exception as e:
        print(f"\n[ERROR] 同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
