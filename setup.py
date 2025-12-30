"""
配置管理脚本
用于初始化、测试飞书连接
"""

import sys
import json
import getpass
from pathlib import Path

from tools.feishu_uploader import FeishuUploader


CONFIG_PATH = Path(__file__).parent / 'config.json'


def init_config():
    """初始化配置"""
    print("=" * 60)
    print("Obsidian to 飞书同步工具 - 初始化配置")
    print("=" * 60)

    print("\n📌 第一步：创建飞书应用")
    print("1. 访问飞书开放平台: https://open.feishu.cn/app")
    print("2. 点击「创建企业自建应用」")
    print("3. 填写应用名称（如：Obsidian 同步工具）")
    print("4. 在「凭证与基础信息」页面获取 App ID 和 App Secret")

    print("\n📌 第二步：配置应用权限")
    print("在「权限管理」页面添加以下权限：")
    print("  - docx:document - 创建、编辑云文档")
    print("  - drive:drive - 上传文件到云空间")
    print("配置后点击「申请权限」并等待管理员审核")

    print("\n" + "=" * 60)
    input("按 Enter 键继续配置...")

    # 获取用户输入
    print("\n请输入飞书应用凭证：")
    app_id = input("App ID: ").strip()
    app_secret = getpass.getpass("App Secret (输入时不会显示): ").strip()

    if not app_id or not app_secret:
        print("❌ App ID 和 App Secret 不能为空！")
        sys.exit(1)

    # 创建配置
    config = {
        "feishu": {
            "app_id": app_id,
            "app_secret": app_secret
        },
        "default_image_width": 800,
        "width_mapping": {
            "w50": 50,
            "w30": 30,
            "w100": 100
        }
    }

    # 保存配置
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n✅ 配置已保存到:", CONFIG_PATH)

    # 测试连接
    print("\n正在测试连接...")
    test_connection(quiet=True)


def test_connection(quiet=False):
    """测试飞书连接"""
    if not quiet:
        print("=" * 60)
        print("测试飞书 API 连接")
        print("=" * 60)

    # 检查配置文件
    if not CONFIG_PATH.exists():
        print("❌ 配置文件不存在！")
        print("请先运行: python setup.py init")
        sys.exit(1)

    # 加载配置
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    app_id = config['feishu']['app_id']
    app_secret = config['feishu']['app_secret']

    # 测试获取 token
    try:
        uploader = FeishuUploader(app_id, app_secret)
        token = uploader.get_tenant_token()

        print("\n✅ 连接成功！")
        print(f"Token: {token[:20]}...")
        print("\n配置信息:")
        print(f"  App ID: {app_id}")
        print(f"  图片默认宽度: {config.get('default_image_width', 800)}px")

        return True

    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print("\n请检查:")
        print("  1. App ID 和 App Secret 是否正确")
        print("  2. 应用权限是否已审核通过")
        print("  3. 网络连接是否正常")

        return False


def show_config():
    """显示当前配置"""
    print("=" * 60)
    print("当前配置")
    print("=" * 60)

    if not CONFIG_PATH.exists():
        print("❌ 配置文件不存在！")
        print("请先运行: python setup.py init")
        return

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("\n飞书配置:")
    print(f"  App ID: {config['feishu']['app_id']}")
    print(f"  App Secret: {'*' * 20}")

    print("\n图片设置:")
    print(f"  默认宽度: {config.get('default_image_width', 800)}px")
    print(f"  宽度映射: {config.get('width_mapping', {})}")


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python setup.py init   - 初始化配置")
        print("  python setup.py test   - 测试连接")
        print("  python setup.py show   - 显示配置")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'init':
        init_config()
    elif command == 'test':
        test_connection()
    elif command == 'show':
        show_config()
    else:
        print(f"未知命令: {command}")
        print("可用命令: init, test, show")
        sys.exit(1)


if __name__ == '__main__':
    main()
