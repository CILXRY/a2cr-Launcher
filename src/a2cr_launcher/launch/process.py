import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import unescape

# Minecraft 26.x 的日志配置把控制台输出改成了 log4j XML（LegacyXMLLayout），
# 直接把 XML 打到终端没法看，这里把它还原成和 logs/latest.log 一样的可读格式。
_EVENT_HEADER = re.compile(r"<log4j:Event\b([^>]*)>")
_ATTRIBUTE = re.compile(r'([\w:-]+)="([^"]*)"')
_MESSAGE = re.compile(r"<log4j:Message><!\[CDATA\[(.*?)\]\]></log4j:Message>", re.S)
_MESSAGE_PLAIN = re.compile(r"<log4j:Message>(.*?)</log4j:Message>", re.S)
_THROWABLE = re.compile(r"<log4j:Throwable><!\[CDATA\[(.*?)\]\]></log4j:Throwable>", re.S)

_MAX_TRACE_LINES = 12


def _format_event(block: str) -> str | None:
    """把一段 <log4j:Event>…</log4j:Event> 还原成一行可读日志，解析失败返回 None。"""
    header = _EVENT_HEADER.search(block)
    if not header:
        return None

    attributes = dict(_ATTRIBUTE.findall(header.group(1)))
    level = attributes.get("level", "INFO")
    thread = attributes.get("thread", "main")

    timestamp = attributes.get("timestamp", "")
    when = ""
    if timestamp.isdigit():
        when = datetime.fromtimestamp(int(timestamp) / 1000).strftime("%H:%M:%S")

    message_match = _MESSAGE.search(block) or _MESSAGE_PLAIN.search(block)
    message = unescape(message_match.group(1)).rstrip("\n") if message_match else ""

    lines = message.splitlines() or [""]
    output = [f"[{when}] [{thread}/{level}]: {lines[0]}"]
    output.extend(f"    {line}" for line in lines[1:])

    throwable = _THROWABLE.search(block)
    if throwable and level in ("ERROR", "FATAL"):
        trace = unescape(throwable.group(1)).rstrip("\n").splitlines()
        output.extend(f"    {line}" for line in trace[:_MAX_TRACE_LINES])
        if len(trace) > _MAX_TRACE_LINES:
            output.append(f"    ... 还有 {len(trace) - _MAX_TRACE_LINES} 行，见日志文件")

    return "\n".join(output)


def _safe_console_text(text: str) -> str:
    """把控制台编码（中文 Windows 是 GBK）表示不了的字符替换掉，避免日志里的 emoji 让启动器崩溃。"""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def launch(cmd: list[str], game_dir: Path) -> int:
    proc = subprocess.Popen(
        cmd, cwd=game_dir,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    if proc.stdout is None:
        return proc.wait()

    buffer: list[str] = []
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\r\n")
        if not buffer and not line.lstrip().startswith("<log4j:Event"):
            print(_safe_console_text(line), flush=True)
            continue

        buffer.append(line)
        if "</log4j:Event>" not in line:
            continue

        block = "\n".join(buffer)
        buffer.clear()
        formatted = _format_event(block)
        print(_safe_console_text(formatted if formatted is not None else block), flush=True)

    if buffer:
        print(_safe_console_text("\n".join(buffer)), flush=True)
    return proc.wait()
