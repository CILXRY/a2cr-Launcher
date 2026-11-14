"""启动器设置的读写。

设置只是一个很薄的 JSON 文件，不放在数据库里：即使文件被用户改坏，也要能
回退到默认值继续启动。所有写入都走临时文件 + 原子替换，避免断电时留下半个
JSON 让下次启动直接崩掉。
"""

import json
from copy import deepcopy
from pathlib import Path

from a2cr_launcher.core.paths import SETTINGS_FILE

# 默认设置。新增字段时给一个安全的默认值，旧配置文件会自动补齐。
DEFAULT_SETTINGS: dict = {
    "player_name": "a2Cr",
    "max_memory": "4G",
    "java_path": "",
    "theme": "dark",
    "last_instance": "",
    "window_width": 1180,
    "window_height": 760,
    "close_on_launch": False,
    "show_snapshots": False,
}

_ALLOWED_THEMES = {"dark", "light", "system"}
_MEMORY_UNITS = ("G", "M")


def _normalize_memory(value) -> str:
    """把用户输入的内存大小统一成 ``数字G`` / ``数字M``。"""
    text = str(value or "").strip().upper().replace(" ", "")
    if not text:
        return DEFAULT_SETTINGS["max_memory"]
    suffix = text[-1]
    digits = text[:-1]
    if suffix not in _MEMORY_UNITS or not digits.isdigit():
        return DEFAULT_SETTINGS["max_memory"]
    amount = int(digits)
    if amount <= 0:
        return DEFAULT_SETTINGS["max_memory"]
    # 100M 以下基本开不起游戏，直接当无效输入处理
    if suffix == "M" and amount < 512:
        return DEFAULT_SETTINGS["max_memory"]
    return f"{amount}{suffix}"


def _normalize(settings: dict) -> dict:
    """把读到的字典约束成 UI 能安全使用的类型。"""
    merged = deepcopy(DEFAULT_SETTINGS)
    if not isinstance(settings, dict):
        return merged
    merged.update({key: settings[key] for key in DEFAULT_SETTINGS if key in settings})

    merged["player_name"] = str(merged.get("player_name") or "").strip() or DEFAULT_SETTINGS["player_name"]
    merged["max_memory"] = _normalize_memory(merged.get("max_memory"))
    merged["java_path"] = str(merged.get("java_path") or "").strip()
    if merged.get("theme") not in _ALLOWED_THEMES:
        merged["theme"] = DEFAULT_SETTINGS["theme"]
    merged["last_instance"] = str(merged.get("last_instance") or "").strip()
    merged["close_on_launch"] = bool(merged.get("close_on_launch"))
    merged["show_snapshots"] = bool(merged.get("show_snapshots"))
    try:
        merged["window_width"] = max(960, int(merged.get("window_width") or DEFAULT_SETTINGS["window_width"]))
        merged["window_height"] = max(640, int(merged.get("window_height") or DEFAULT_SETTINGS["window_height"]))
    except (TypeError, ValueError):
        merged["window_width"] = DEFAULT_SETTINGS["window_width"]
        merged["window_height"] = DEFAULT_SETTINGS["window_height"]
    return merged


def load_settings() -> dict:
    """读取设置；文件不存在、损坏或没有权限时返回默认值，而不是让界面崩掉。"""
    try:
        with open(Path(SETTINGS_FILE), "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_SETTINGS)
    return _normalize(data)


def save_settings(settings: dict) -> dict:
    """原子地保存设置，并返回归一化后的结果。"""
    normalized = _normalize(settings)
    path = Path(SETTINGS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2)
    temp.replace(path)
    return normalized


def update_settings(**changes) -> dict:
    """在现有设置上合并修改，方便 UI 做“改一项就存一次”。"""
    settings = load_settings()
    settings.update({key: value for key, value in changes.items() if key in DEFAULT_SETTINGS})
    return save_settings(settings)
