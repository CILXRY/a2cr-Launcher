"""界面用的小工具：时间、路径、文本格式化。

这些函数不依赖 Flet，方便在冒烟测试里单独验证。
"""

from datetime import datetime
from pathlib import Path


def parse_iso(value: str | None) -> datetime | None:
    """解析 ISO 时间字符串，失败返回 None。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def format_relative(value: str | None) -> str:
    """把 ISO 时间变成“刚刚 / 12 分钟前 / 昨天”这类适合卡片显示的文本。"""
    moment = parse_iso(value)
    if moment is None:
        return "还没玩过"
    now = datetime.now(moment.tzinfo) if moment.tzinfo else datetime.now()
    seconds = max(0, int((now - moment).total_seconds()))
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{seconds // 60} 分钟前"
    if seconds < 86400:
        return f"{seconds // 3600} 小时前"
    if seconds < 86400 * 7:
        return f"{seconds // 86400} 天前"
    return moment.strftime("%Y-%m-%d")


def format_date(value: str | None) -> str:
    """版本列表里的日期只保留 YYYY-MM-DD。"""
    moment = parse_iso(value)
    return moment.strftime("%Y-%m-%d") if moment else "—"


def format_duration(seconds: float) -> str:
    """游戏运行时长，格式 mm:ss 或 h:mm:ss。"""
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_size(size: int | float | None) -> str:
    """文件大小，用于导入预检信息。"""
    value = float(size or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def shorten_path(path: str | Path, limit: int = 46) -> str:
    """中间省略的长路径，避免卡片被撑爆。"""
    text = str(path)
    if len(text) <= limit:
        return text
    head = max(8, (limit - 3) // 2)
    tail = max(8, limit - 3 - head)
    return f"{text[:head]}...{text[-tail:]}"


def initial_of(name: str) -> str:
    """实例封面上的字符：中文取首字，英文取首字母。"""
    text = (name or "?").strip()
    return text[0].upper() if text else "?"


def plural(count: int, unit: str) -> str:
    """中文没有复数变化，这里只是统一文案。"""
    return f"{count} {unit}"


def memory_gb(value: str) -> int:
    """把 ``4G`` / ``4096M`` 转成 GB 整数，给滑块用。"""
    text = str(value or "4G").strip().upper()
    try:
        amount = int(text[:-1])
    except (ValueError, IndexError):
        return 4
    if text.endswith("M"):
        return max(1, round(amount / 1024))
    return max(1, amount)


def loader_display(loader: str, version: str = "") -> str:
    """加载器显示名，带版本号时拼成 ``NeoForge 21.1``。"""
    names = {
        "vanilla": "原版",
        "fabric": "Fabric",
        "quilt": "Quilt",
        "forge": "Forge",
        "neoforge": "NeoForge",
    }
    name = names.get((loader or "vanilla").lower(), loader or "原版")
    return f"{name} {version}".strip() if version else name


def ellipsis(text: str, limit: int) -> str:
    """按字符数截断，超长补省略号。"""
    text = str(text or "")
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"
