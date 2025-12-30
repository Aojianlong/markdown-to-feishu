"""
飞书 API 封装
处理飞书认证、图片上传、文档创建等操作
"""

import requests
import json
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed


class FeishuUploader:
    """处理飞书 API 交互"""

    # API 端点
    AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    UPLOAD_IMAGE_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
    CREATE_DOC_URL = "https://open.feishu.cn/open-apis/docx/v1/documents"
    # 创建块的子块API
    CREATE_BLOCKS_URL = "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/children"
    # 更新块API
    UPDATE_BLOCK_URL = "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}"
    # 文档权限设置API
    SET_PERMISSION_URL = "https://open.feishu.cn/open-apis/drive/v2/permissions/{token}/public"
    # Markdown/HTML 转换为块API
    CONVERT_MARKDOWN_URL = "https://open.feishu.cn/open-apis/docx/v1/documents/blocks/batch_convert"

    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书上传器

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用 Secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.token = None
        self.token_expire_time = 0
        self._token_lock = threading.Lock()  # 线程锁保护 token 刷新

    def get_tenant_token(self) -> str:
        """
        获取 tenant_access_token（线程安全）

        Returns:
            访问令牌
        """
        # 快速检查（无锁）
        if self.token and time.time() < self.token_expire_time:
            return self.token

        # 请求新 token（需要锁）
        with self._token_lock:
            # 双重检查（其他线程可能已刷新）
            if self.token and time.time() < self.token_expire_time:
                return self.token

            # 请求新 token
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }

            response = requests.post(self.AUTH_URL, json=payload)
            response.raise_for_status()

            data = response.json()
            if data.get('code') != 0:
                raise Exception(f"获取 token 失败: {data.get('msg')}")

            self.token = data['tenant_access_token']
            # 提前 10 分钟过期，避免边界情况
            self.token_expire_time = time.time() + data['expire'] - 600

            return self.token

    def _prepare_image_upload(self, image_path: Path) -> tuple:
        """
        准备图片上传的通用逻辑

        Args:
            image_path: 图片文件路径

        Returns:
            (width, height, mime_type) 元组
        """
        # 获取图片尺寸
        try:
            with Image.open(image_path) as img:
                width, height = img.size
        except Exception as e:
            print(f"警告：无法获取图片尺寸 {image_path}: {e}")
            width, height = 800, 600  # 默认尺寸

        # 根据图片扩展名确定MIME类型
        ext = image_path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')

        return width, height, mime_type

    def upload_image(self, image_path: Path, parent_node: str = None) -> Dict[str, str]:
        """
        上传图片到飞书

        Args:
            image_path: 图片文件路径
            parent_node: 父节点 ID（通常是文档 ID）

        Returns:
            包含 file_token 和图片尺寸的字典
        """
        token = self.get_tenant_token()
        width, height, mime_type = self._prepare_image_upload(image_path)

        # 准备上传
        headers = {
            "Authorization": f"Bearer {token}"
        }

        # 读取图片文件
        with open(image_path, 'rb') as f:
            # 构建请求数据
            data_fields = {
                'file_name': image_path.name,
                'parent_type': 'docx_image',
                'size': str(image_path.stat().st_size)
            }

            # 如果提供了 parent_node，则添加到请求中
            if parent_node:
                data_fields['parent_node'] = parent_node

            response = requests.post(
                self.UPLOAD_IMAGE_URL,
                headers=headers,
                data=data_fields,
                files={'file': (image_path.name, f, mime_type)}
            )

        # 检查HTTP状态码
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"  HTTP {response.status_code} - API response: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"  HTTP {response.status_code} - Raw response: {response.text}")
            response.raise_for_status()

        data = response.json()

        if data.get('code') != 0:
            error_msg = data.get('msg', 'Unknown error')
            error_code = data.get('code')
            print(f"  API Error - Code: {error_code}, Message: {error_msg}")
            print(f"  Full response: {json.dumps(data, ensure_ascii=False)}")
            raise Exception(f"上传图片失败: {error_msg} (code: {error_code})")

        return {
            'file_token': data['data']['file_token'],
            'width': width,
            'height': height
        }

    def create_document(self, title: str, folder_token: Optional[str] = None) -> Dict[str, str]:
        """
        创建飞书云文档

        Args:
            title: 文档标题
            folder_token: 文件夹 token（可选，默认创建到根目录）

        Returns:
            包含 document_id 和 url 的字典

        Raises:
            Exception: API 调用失败
            KeyError: API 响应格式不符合预期
        """
        token = self.get_tenant_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "title": title
        }

        if folder_token:
            payload['folder_token'] = folder_token

        response = requests.post(
            self.CREATE_DOC_URL,
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        data = response.json()

        if data.get('code') != 0:
            raise Exception(f"创建文档失败: {data.get('msg')}")

        print(f"  Debug - API response: {json.dumps(data, ensure_ascii=False, indent=2)}")

        # 验证响应结构
        try:
            document_id = data['data']['document']['document_id']
            url = data['data']['document'].get('url', '')
        except KeyError as e:
            raise KeyError(f"API 响应格式异常，缺少字段: {e}") from e

        return {
            'document_id': document_id,
            'url': url
        }

    def set_document_permission(self, document_id: str, permission: str = "tenant_editable"):
        """
        设置文档权限为组织内可编辑

        Args:
            document_id: 文档 ID
            permission: 权限类型
                - tenant_editable: 组织内获得链接的人可编辑（推荐）
                - tenant_readable: 组织内获得链接的人可阅读

        Returns:
            设置结果
        """
        token = self.get_tenant_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = self.SET_PERMISSION_URL.format(token=document_id)

        # 关键修正：type 需要作为 URL 查询参数传入，而不是请求体
        doc_type = "docx"  # 因为我们创建的是新版文档
        url = f"{url}?type={doc_type}"

        # 按照API正确格式构建 payload
        # link_share_entity 是顶级字段（控制链接分享权限）
        # security_entity 是可选枚举字段（控制副本/打印/下载权限）
        if permission == "tenant_editable":
            # 组织内获得链接的人可编辑
            payload = {
                "link_share_entity": "tenant_editable",  # 顶级字段
                "security_entity": "anyone_can_view"     # 允许阅读者创建副本/打印/下载
            }
        elif permission == "tenant_readable":
            # 组织内获得链接的人可阅读
            payload = {
                "link_share_entity": "tenant_readable",  # 顶级字段
                "security_entity": "anyone_can_view"
            }
        else:
            # 默认：组织内可编辑
            payload = {
                "link_share_entity": "tenant_editable",
                "security_entity": "anyone_can_view"
            }

        try:
            response = requests.patch(url, headers=headers, json=payload)

            if response.status_code != 200:
                # 输出错误信息
                try:
                    error_data = response.json()
                    print(f"  [WARNING] 设置文档权限失败: {error_data.get('msg', 'Unknown error')}")
                except:
                    print(f"  [WARNING] 设置文档权限失败 - HTTP {response.status_code}")
                return False

            result = response.json()
            if result.get('code') == 0:
                print(f"  [OK] 文档权限已设置为：组织内可编辑")
                return True
            else:
                print(f"  [WARNING] 设置权限失败: {result.get('msg')}")
                return False
        except Exception as e:
            print(f"  [WARNING] 设置权限时出错: {e}")
            return False


    def add_blocks_to_document(self, document_id: str, blocks: List[Dict], parent_id: str = None) -> List[str]:
        """
        向文档添加内容块

        Args:
            document_id: 文档 ID
            blocks: Block 列表
            parent_id: 父块 ID (可选，默认添加到文档根节点)

        Returns:
            创建的 block_id 列表
        """
        token = self.get_tenant_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 如果没有指定parent_id，直接使用document_id作为block_id（文档树根节点）
        # 否则使用指定的parent_id作为父块
        block_id = parent_id if parent_id else document_id

        url = self.CREATE_BLOCKS_URL.format(
            document_id=document_id,
            block_id=block_id
        )

        payload = {
            "children": blocks
        }

        response = requests.post(url, headers=headers, json=payload)

        # 添加错误调试
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"  HTTP {response.status_code} - API response: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"  HTTP {response.status_code} - Raw response: {response.text}")

        response.raise_for_status()

        data = response.json()

        if data.get('code') != 0:
            raise Exception(f"添加内容失败: {data.get('msg')}")

        # 返回创建的块的完整信息（包括block_id和children）
        blocks_info = []
        if 'data' in data and 'children' in data['data']:
            blocks_info = data['data']['children']

        return blocks_info

    def upload_image_to_block(self, image_path: Path, document_id: str, block_id: str) -> Dict[str, str]:
        """
        上传图片到指定的图片块并绑定

        Args:
            image_path: 图片文件路径
            document_id: 文档 ID
            block_id: 图片块 ID

        Returns:
            包含 file_token 和图片尺寸的字典
        """
        token = self.get_tenant_token()
        width, height, mime_type = self._prepare_image_upload(image_path)

        # 准备上传
        headers = {
            "Authorization": f"Bearer {token}"
        }

        # 读取图片文件
        with open(image_path, 'rb') as f:
            # 构建请求数据 - 上传到特定的图片块
            data_fields = {
                'file_name': image_path.name,
                'parent_type': 'docx_image',
                'parent_node': block_id,  # 关键: 指定图片块ID
                'size': str(image_path.stat().st_size)
            }

            response = requests.post(
                self.UPLOAD_IMAGE_URL,
                headers=headers,
                data=data_fields,
                files={'file': (image_path.name, f, mime_type)}
            )

        # 检查HTTP状态码
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"  HTTP {response.status_code} - API response: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"  HTTP {response.status_code} - Raw response: {response.text}")
            response.raise_for_status()

        data = response.json()

        if data.get('code') != 0:
            error_msg = data.get('msg', 'Unknown error')
            error_code = data.get('code')
            print(f"  API Error - Code: {error_code}, Message: {error_msg}")
            print(f"  Full response: {json.dumps(data, ensure_ascii=False)}")
            raise Exception(f"上传图片失败: {error_msg} (code: {error_code})")

        file_token = data['data']['file_token']

        # 关键步骤：调用更新块接口，将file_token绑定到图片块
        self.bind_image_to_block(document_id, block_id, file_token, width, height)

        return {
            'file_token': file_token,
            'width': width,
            'height': height
        }

    def bind_image_to_block(self, document_id: str, block_id: str, file_token: str, width: int, height: int):
        """
        将上传的图片token绑定到图片块

        Args:
            document_id: 文档ID
            block_id: 图片块ID
            file_token: 上传后获得的文件token
            width: 图片宽度
            height: 图片高度
        """
        token = self.get_tenant_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = self.UPDATE_BLOCK_URL.format(
            document_id=document_id,
            block_id=block_id
        )

        # 使用replace_image操作绑定图片
        payload = {
            "replace_image": {
                "token": file_token
            }
        }

        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"  绑定图片失败 - HTTP {response.status_code}: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"  绑定图片失败 - HTTP {response.status_code}: {response.text}")
            response.raise_for_status()

        result = response.json()
        if result.get('code') != 0:
            raise Exception(f"绑定图片到块失败: {result.get('msg')}")

    def upload_images_batch_parallel(
        self,
        upload_tasks: List[Tuple[Path, str, str]],
        max_workers: int = 3
    ) -> List[Dict[str, Any]]:
        """
        并发上传多张图片

        Args:
            upload_tasks: [(image_path, document_id, block_id), ...]
            max_workers: 最大并发线程数（建议 3-5，避免 API 限流）

        Returns:
            结果列表，与输入顺序一致
            [{'success': True/False, 'data': result, 'error': str, 'path': str}, ...]
        """
        if not upload_tasks:
            return []

        # 结果列表（保持顺序）
        results = [None] * len(upload_tasks)

        def upload_single(index: int, image_path: Path, document_id: str, block_id: str) -> Dict[str, Any]:
            """上传单张图片的包装函数"""
            try:
                result = self.upload_image_to_block(
                    image_path, document_id, block_id
                )
                return {
                    'index': index,
                    'success': True,
                    'data': result,
                    'path': str(image_path),
                    'error': None
                }
            except Exception as e:
                return {
                    'index': index,
                    'success': False,
                    'data': None,
                    'error': str(e),
                    'path': str(image_path)
                }

        # 并发上传
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    upload_single, idx, *task
                ): idx for idx, task in enumerate(upload_tasks)
            }

            # 收集结果
            for future in as_completed(futures):
                result = future.result()
                results[result['index']] = result

        return results

    def convert_markdown_to_blocks(self, markdown_text: str) -> List[Dict]:
        """
        使用飞书 API 将 Markdown 文本转换为 Block 结构

        Args:
            markdown_text: Markdown 格式的文本

        Returns:
            飞书 Block 列表
        """
        token = self.get_tenant_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        payload = {
            "text": markdown_text,
            "format": "markdown"  # 指定为 Markdown 格式
        }

        response = requests.post(self.CONVERT_MARKDOWN_URL, headers=headers, json=payload)

        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"  转换 Markdown 失败 - HTTP {response.status_code}: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"  转换 Markdown 失败 - HTTP {response.status_code}: {response.text}")
            response.raise_for_status()

        result = response.json()
        if result.get('code') != 0:
            raise Exception(f"转换 Markdown 失败: {result.get('msg')}")

        # 返回转换后的块列表
        blocks = result.get('data', {}).get('blocks', [])

        # 需要移除 merge_info 字段（只读属性）
        for block in blocks:
            if 'table' in block and 'merge_info' in block['table']:
                del block['table']['merge_info']
            # 递归处理子块
            if 'children' in block:
                for child in block['children']:
                    if 'table' in child and 'merge_info' in child['table']:
                        del child['table']['merge_info']

        return blocks

    def create_table_with_content(self, document_id: str, headers: List[str], rows: List[List[str]]) -> Optional[str]:
        """
        使用创建嵌套块接口创建带内容的表格

        Args:
            document_id: 文档 ID
            headers: 表头列表
            rows: 数据行列表

        Returns:
            表格块 ID，失败返回 None
        """
        col_count = len(headers)
        row_count = len(rows) + 1  # +1 for header row

        # 合并表头和数据行
        all_rows = [headers] + rows

        # 构建表格块结构（包含所有单元格和内容）
        # 1. 为每个单元格生成临时 ID
        cell_temp_ids = []
        for row_idx in range(row_count):
            for col_idx in range(col_count):
                cell_temp_ids.append(f"cell_{row_idx}_{col_idx}")

        # 2. 构建表格块
        table_block = {
            "block_id": "table_temp_id",  # 表格的临时 ID
            "block_type": 31,  # 表格块
            "table": {
                "property": {
                    "row_size": row_count,
                    "column_size": col_count
                }
            },
            "children": cell_temp_ids  # 单元格列表
        }

        # 3. 构建所有单元格块（每个单元格包含一个文本块作为子块）
        cell_blocks = []
        for row_idx in range(row_count):
            for col_idx in range(col_count):
                cell_temp_id = f"cell_{row_idx}_{col_idx}"
                text_temp_id = f"text_{row_idx}_{col_idx}"

                # 获取单元格内容
                cell_content = all_rows[row_idx][col_idx] if col_idx < len(all_rows[row_idx]) else ""

                # 单元格块
                cell_block = {
                    "block_id": cell_temp_id,
                    "block_type": 32,  # 表格单元格块
                    "table_cell": {},
                    "children": [text_temp_id]  # 单元格内的文本块
                }
                cell_blocks.append(cell_block)

                # 文本块（单元格的子块）
                text_block = {
                    "block_id": text_temp_id,
                    "block_type": 2,  # 文本块
                    "text": {
                        "elements": [{
                            "text_run": {"content": cell_content if cell_content else " "}  # 空内容用空格代替
                        }]
                    }
                }
                cell_blocks.append(text_block)

        # 4. 合并所有块（表格块 + 所有单元格块 + 所有文本块）
        all_blocks = [table_block] + cell_blocks

        # 5. 调用创建嵌套块 API
        token = self.get_tenant_token()
        headers_dict = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        # 使用 descendant 接口（创建嵌套块）
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/descendant"

        payload = {
            "children_id": ["table_temp_id"],  # 只需要第一级子块的 ID
            "index": -1,  # 添加到末尾
            "descendants": all_blocks  # 所有嵌套块
        }

        print(f"  创建嵌套表格块: {row_count} 行 × {col_count} 列 = {len(cell_temp_ids)} 个单元格")

        response = requests.post(url, headers=headers_dict, json=payload)

        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"  HTTP {response.status_code} - API response: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"  HTTP {response.status_code}: {response.text}")
            raise Exception(f"创建嵌套表格失败: HTTP {response.status_code}")

        result = response.json()
        if result.get('code') != 0:
            raise Exception(f"创建嵌套表格失败: {result.get('msg')}")

        # 获取实际的表格块 ID
        block_id_relations = result.get('data', {}).get('block_id_relations', [])
        table_block_id = None
        for relation in block_id_relations:
            if relation.get('temporary_block_id') == 'table_temp_id':  # 注意：字段名是 temporary_block_id
                table_block_id = relation.get('block_id')
                break

        if not table_block_id:
            print(f"  警告：无法从 block_id_relations 获取表格块 ID")
            # 尝试从 children 中获取
            children = result.get('data', {}).get('children', [])
            if children and len(children) > 0:
                table_block_id = children[0].get('block_id')
                print(f"  从 children 获取到表格块 ID: {table_block_id}")

        print(f"  表格块创建成功，ID: {table_block_id}")
        return table_block_id

    def create_document_with_content(self, title: str, blocks: List[Dict]) -> str:
        """
        创建文档并添加内容（便捷方法）

        Args:
            title: 文档标题
            blocks: Block 列表

        Returns:
            文档 URL
        """
        # 创建文档
        doc_info = self.create_document(title)
        document_id = doc_info['document_id']
        url = doc_info['url']

        # 添加内容
        # 注意：飞书 API 一次最多添加 500 个 block，需要分批
        batch_size = 500
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            self.add_blocks_to_document(document_id, batch)
            time.sleep(0.5)  # 避免 API 限流

        return url


# 测试代码
if __name__ == '__main__':
    import os

    # 从环境变量读取（仅供测试）
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')

    if app_id and app_secret:
        uploader = FeishuUploader(app_id, app_secret)

        # 测试获取 token
        try:
            token = uploader.get_tenant_token()
            print(f"Token 获取成功: {token[:20]}...")
        except Exception as e:
            print(f"Token 获取失败: {e}")
    else:
        print("请设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET 进行测试")
