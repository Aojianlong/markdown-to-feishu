"""
Obsidian to 飞书同步工具
主流程脚本 - 重构版本
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List

from tools.markdown_parser import MarkdownParser
from tools.feishu_uploader import FeishuUploader
from tools.block_converter import BlockConverter


def load_config() -> Dict:
    """加载配置文件"""
    config_path = Path(__file__).parent / 'config.json'

    if not config_path.exists():
        print("错误：配置文件不存在！")
        print("请先运行: python setup.py init")
        sys.exit(1)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
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

    images_dir = md_path.parent / "images"

    print(f"开始同步文档: {md_path.name}")
    print("-" * 60)

    # Step 1: 解析 Markdown
    print("[1/4] 解析 Markdown 文件...")
    parser = MarkdownParser()
    parsed_data = parser.parse_file(md_path)
    print(f"[OK] 解析完成，共 {len(parsed_data)} 个元素")

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

        def should_flush_batch(current_item, last_item_in_batch):
            """判断是否需要提交当前批次"""

            # 如果批次为空,不需要提交
            if not batch or not last_item_in_batch:
                return False

            # API 限制：单次最多添加 50 个块
            if len(batch) >= 50:
                return True

            # 如果遇到图片，必须先提交批次
            if current_item['type'] == 'image':
                return True

            # 如果遇到表格，必须先提交批次
            if current_item['type'] == 'table':
                return True

            current_type = current_item['type']
            last_type = last_item_in_batch['type']

            # 如果上一项是有序列表
            if last_type == 'ordered':
                # 当前项也是有序列表且同级别,继续累积
                if current_type == 'ordered':
                    current_indent = current_item.get('indent', 0)
                    last_indent = last_item_in_batch.get('indent', 0)
                    if current_indent == last_indent:
                        return False  # 继续累积同级别的有序列表

                # 当前项不是有序列表,或者缩进不同,提交批次
                return True

            # 其他情况根据具体需求判断
            # 一般策略:累积到一定数量再提交,或遇到图片/特殊元素
            return False

        for idx, (item, block) in enumerate(zip(parsed_data, blocks)):
            last_item_in_batch = parsed_data[idx - 1] if idx > 0 and batch else None

            # 判断是否需要提交当前批次
            if batch and should_flush_batch(item, last_item_in_batch):
                print(f"  添加批次 ({batch_start_idx+1}-{batch_start_idx+len(batch)})...")
                uploader.add_blocks_to_document(document_id, batch)
                processed += len(batch)
                batch = []
                batch_start_idx = idx
                time.sleep(0.3)  # 避免API限流

            if item['type'] == 'image':
                # 检查是否是连续图片组(用于并排显示)
                consecutive_images = [item]
                consecutive_indices = [idx]

                # 向前查找连续的图片
                j = idx + 1
                while j < len(parsed_data) and parsed_data[j]['type'] == 'image':
                    consecutive_images.append(parsed_data[j])
                    consecutive_indices.append(j)
                    j += 1

                # 如果有多张连续图片,使用Grid分栏布局(最多5列)
                if len(consecutive_images) > 1:
                    print(f"  [{idx+1}-{j}/{total_items}] 处理并排图片组 ({len(consecutive_images)}张)")

                    # 飞书Grid最多支持5列,需要智能分批处理
                    MAX_GRID_COLUMNS = 5
                    total_images = len(consecutive_images)

                    # 计算最佳分批方案
                    if total_images <= MAX_GRID_COLUMNS:
                        # 5张及以下,单行显示
                        img_batches = [consecutive_images]
                    else:
                        # 超过5张,分成多行,尽量均匀分布
                        # 计算需要多少行
                        num_rows = (total_images + MAX_GRID_COLUMNS - 1) // MAX_GRID_COLUMNS

                        # 计算每行的图片数量(尽量均匀)
                        base_count = total_images // num_rows  # 每行基础数量
                        extra_count = total_images % num_rows  # 多余的图片数

                        img_batches = []
                        start_idx = 0
                        for row in range(num_rows):
                            # 前面的行多分配1张(如果有多余的)
                            count = base_count + (1 if row < extra_count else 0)
                            img_batches.append(consecutive_images[start_idx:start_idx + count])
                            start_idx += count

                    for batch_idx, img_batch in enumerate(img_batches):
                        # 如果批次只有1张图片,按单张处理
                        if len(img_batch) == 1:
                            img_item = img_batch[0]
                            img_block = converter._create_image_block(img_item, {})

                            blocks_info = uploader.add_blocks_to_document(document_id, [img_block])
                            if not blocks_info:
                                print(f"      [X] 创建图片块失败")
                                continue

                            image_block_id = blocks_info[0]['block_id']
                            image_path = images_dir / img_item['path'].replace('images/', '')

                            if not image_path.exists():
                                print(f"      [X] 图片不存在: {image_path}")
                                continue

                            try:
                                uploader.upload_image_to_block(image_path, document_id, image_block_id)
                                print(f"      [OK] 单张图片上传成功")
                            except Exception as e:
                                print(f"      [X] 上传失败: {e}")

                            time.sleep(0.2)
                            continue

                        print(f"    处理第{batch_idx+1}/{len(img_batches)}组 ({len(img_batch)}张)")

                        # 步骤1: 创建Grid块
                        grid_block = converter._create_grid_block(column_size=len(img_batch))
                        grid_blocks_info = uploader.add_blocks_to_document(document_id, [grid_block])

                        if not grid_blocks_info:
                            print(f"      [X] 创建Grid块失败")
                            continue

                        # 步骤2: 从响应中提取Grid块的ID和自动生成的GridColumn子块ID
                        grid_block_info = grid_blocks_info[0]
                        grid_block_id = grid_block_info['block_id']
                        grid_column_ids = grid_block_info.get('children', [])

                        if len(grid_column_ids) != len(img_batch):
                            print(f"      [X] GridColumn数量不匹配: 预期{len(img_batch)}, 实际{len(grid_column_ids)}")
                            continue

                        print(f"      [OK] Grid块创建成功，包含{len(grid_column_ids)}个分栏列")
                        time.sleep(0.2)

                        # 步骤3: 在每个GridColumn下创建图片块
                        image_upload_tasks = []  # 收集需要上传的图片任务

                        for img_idx, (img_item, column_id) in enumerate(zip(img_batch, grid_column_ids)):
                            # 3.1 在GridColumn下创建空图片块
                            empty_image_block = converter._create_image_block(img_item, {})
                            image_blocks_info = uploader.add_blocks_to_document(
                                document_id,
                                [empty_image_block],
                                parent_id=column_id  # 指定GridColumn ID作为父块
                            )

                            if not image_blocks_info:
                                print(f"        [X] 创建图片块失败")
                                continue

                            image_block_id = image_blocks_info[0]['block_id']
                            image_path = images_dir / img_item['path'].replace('images/', '')

                            if not image_path.exists():
                                print(f"        [X] 图片不存在: {image_path}")
                                continue

                            # 收集上传任务
                            image_upload_tasks.append((image_path, document_id, image_block_id))

                        # 步骤4: 并发上传所有图片
                        if image_upload_tasks:
                            print(f"      [INFO] 并发上传 {len(image_upload_tasks)} 张图片...")

                            results = uploader.upload_images_batch_parallel(
                                image_upload_tasks,
                                max_workers=3
                            )

                            # 统计结果
                            success_count = sum(1 for r in results if r['success'])
                            fail_count = len(results) - success_count

                            print(f"      [OK] 上传完成: {success_count} 成功, {fail_count} 失败")

                            # 显示失败的图片
                            for result in results:
                                if not result['success']:
                                    print(f"        [X] {Path(result['path']).name}: {result['error']}")

                        time.sleep(0.2)  # Grid之间保留延迟

                    processed += len(consecutive_images)
                    batch_start_idx = j

                    # 标记后续图片为已处理
                    for skip_idx in consecutive_indices[1:]:
                        if skip_idx < len(parsed_data):
                            parsed_data[skip_idx] = {'type': 'skip'}

                else:
                    # 单张图片,按原逻辑处理
                    print(f"  [{idx+1}/{total_items}] 处理图片: {item['path']}")

                    # 1. 创建空图片块
                    image_block = [block]
                    blocks_info = uploader.add_blocks_to_document(document_id, image_block)

                    if not blocks_info:
                        print(f"    [X] 创建图片块失败")
                        batch_start_idx = idx + 1
                        continue

                    image_block_id = blocks_info[0]['block_id']

                    # 2. 上传图片到该块
                    image_path = images_dir / item['path'].replace('images/', '')
                    if not image_path.exists():
                        print(f"    [X] 图片不存在: {image_path}")
                        batch_start_idx = idx + 1
                        continue

                    try:
                        uploader.upload_image_to_block(image_path, document_id, image_block_id)
                        print(f"    [OK] 图片上传成功")
                        processed += 1
                    except Exception as e:
                        print(f"    [X] 上传失败: {e}")

                    batch_start_idx = idx + 1
                    time.sleep(0.3)  # 避免API限流
            elif item['type'] == 'skip':
                # 跳过已在Grid中处理的图片
                continue
            elif item['type'] == 'table':
                # 表格：先提交批次，然后创建表格块并填充内容
                if batch:
                    print(f"  添加批次 ({batch_start_idx+1}-{batch_start_idx+len(batch)})...")
                    uploader.add_blocks_to_document(document_id, batch)
                    processed += len(batch)
                    batch = []
                    batch_start_idx = idx
                    time.sleep(0.3)

                print(f"  [{idx+1}/{total_items}] 处理表格...")

                # 检查是否是特殊标记的表格块
                if block.get('_special_type') == 'markdown_table':
                    table_data = block['item']
                    headers = table_data['headers']
                    rows = table_data['rows']

                    try:
                        # 使用新方法创建带内容的表格
                        table_block_id = uploader.create_table_with_content(
                            document_id, headers, rows
                        )

                        if table_block_id:
                            print(f"    [OK] 表格添加成功 ({len(headers)} 列 × {len(rows)+1} 行)")
                            processed += 1
                        else:
                            print(f"    [X] 表格创建失败")
                    except Exception as e:
                        print(f"    [X] 表格处理失败: {e}")

                    batch_start_idx = idx + 1
                    time.sleep(0.5)  # 表格操作较多，延迟稍长
                else:
                    # 旧格式的表格块（不应该出现）
                    print(f"    [X] 不支持的表格格式")
                    batch_start_idx = idx + 1
            else:
                # 非图片、非表格块：添加到批次
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

    print("\n" + "=" * 60)
    print(f"[SUCCESS] 同步完成！")
    print(f"文档标题: {doc_title}")
    print(f"文档链接: {doc_url}")
    print("=" * 60)

    return doc_url


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python main.py <markdown-file-path>")
        print("\n示例:")
        print('  python main.py "D:\\obsidian\\notes\\article.md"')
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
