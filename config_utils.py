"""
配置工具
统一处理 Codex skill 根目录下的配置读写。
"""

import json
import os
from pathlib import Path
from typing import Dict


SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_ROOT / "config.json"
CONFIG_EXAMPLE_PATH = SKILL_ROOT / "config.example.json"


def load_json_config(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_config(path: Path, data: Dict) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_runtime_config() -> Dict:
    """
    加载运行时配置。

    优先读取 skill 根目录下的 config.json。
    如果设置了环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET，则覆盖文件中的凭证。
    """
    config: Dict = {}

    if CONFIG_PATH.exists():
      config = load_json_config(CONFIG_PATH)

    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")

    if app_id or app_secret:
        config.setdefault("feishu", {})
        if app_id:
            config["feishu"]["app_id"] = app_id
        if app_secret:
            config["feishu"]["app_secret"] = app_secret

    return config
