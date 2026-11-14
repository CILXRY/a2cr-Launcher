"""界面运行状态：日志总线、后台任务、游戏会话。

Flet 的控件只能在事件循环里更新，所以工作线程不直接碰控件：
- 日志写进 ``LogBus`` 的队列；
- 导入/安装进度写进 ``TaskState``；
- 游戏进程句柄放进 ``GameSession``。
界面用定时 pump 把这些状态搬到控件上。
"""

import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


LEVEL_ERROR = "ERROR"
LEVEL_WARN = "WARN"
LEVEL_INFO = "INFO"


@dataclass
class LogEntry:
    """一行日志。source 用来区分启动器、导入器、游戏进程。"""

    time: str
    source: str
    level: str
    text: str


class LogBus:
    """线程安全的日志队列。

    队列只保留很短的时间，界面每 100~200ms 批量取走。这样即使下载器在一秒里
    打出几百行，也不会触发几百次 ``page.update``。
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[LogEntry] = queue.Queue()

    def push(self, text: str, source: str = "启动器", level: str | None = None) -> None:
        if text is None:
            return
        for line in str(text).replace("\r\n", "\n").split("\n"):
            line = line.rstrip()
            if not line.strip():
                continue
            self._queue.put(LogEntry(
                time=datetime.now().strftime("%H:%M:%S"),
                source=source,
                level=(level or _guess_level(line)).upper(),
                text=line,
            ))

    def drain(self, limit: int = 300) -> list[LogEntry]:
        """最多取 limit 行，避免一次更新卡住界面。"""
        entries: list[LogEntry] = []
        while len(entries) < limit:
            try:
                entries.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return entries

    def empty(self) -> bool:
        return self._queue.empty()


_ERROR_RE = re.compile(r"\b(ERROR|FATAL|Exception|Traceback)\b", re.IGNORECASE)
_WARN_RE = re.compile(r"\bWARN(ING)?\b", re.IGNORECASE)


def _guess_level(line: str) -> str:
    """从常见日志格式里粗略判断级别，用于给日志上色。"""
    if _ERROR_RE.search(line):
        return LEVEL_ERROR
    if _WARN_RE.search(line):
        return LEVEL_WARN
    return LEVEL_INFO


@dataclass
class TaskState:
    """一个可取消的后台任务（导入或安装）。字段由工作线程写、UI 线程读。"""

    kind: str
    title: str
    stage: str = "准备中"
    done: int = 0
    total: int = 0
    detail: str = ""
    status: str = "running"  # running / done / error / cancelled
    error: str = ""
    result: object = None
    started_at: float = field(default_factory=time.time)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    logs: deque = field(default_factory=lambda: deque(maxlen=8))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def ratio(self) -> float | None:
        """总数为 0 时返回 None，界面显示不确定进度条。"""
        if not self.total:
            return None
        return min(1.0, max(0.0, self.done / self.total))

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at

    def update(self, *, stage: str | None = None, done: int | None = None,
               total: int | None = None, detail: str | None = None) -> None:
        with self._lock:
            if stage is not None:
                self.stage = stage
            if done is not None:
                self.done = done
            if total is not None:
                self.total = total
            if detail is not None:
                self.detail = detail

    def add_log(self, text: str) -> None:
        with self._lock:
            self.logs.append(str(text).rstrip())

    def finish(self, result: object = None) -> None:
        with self._lock:
            self.status = "done"
            self.result = result
            self.stage = "完成"
            self.done = max(self.done, self.total or 1)
            self.total = max(self.total, 1)

    def fail(self, message: str) -> None:
        with self._lock:
            self.status = "error"
            self.error = message or "未知错误"
            self.stage = "失败"

    def cancel(self) -> None:
        self.cancel_event.set()
        self.update(detail="正在取消…")

    def cancelled(self) -> None:
        with self._lock:
            self.status = "cancelled"
            self.stage = "已取消"

    @property
    def running(self) -> bool:
        return self.status == "running"


@dataclass
class GameSession:
    """当前游戏进程。启动成功后才会有 process。"""

    label: str
    version_id: str
    process: object = None
    started_at: float = field(default_factory=time.time)
    exit_code: int | None = None
    running: bool = True
    stop_requested: bool = False

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at


class StdoutTee:
    """把 stdout 同时写到原来的终端和界面的日志队列。

    打包后的应用里 stdout 是 None，所有 print 都会落到 Flet 的 console.log；
    这里接一份出来显示在界面上，CLI 行为的唯一变化是日志多了一处副本。
    """

    def __init__(self, original, sink):
        self._original = original
        self._sink = sink

    def write(self, text):
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass
        if text and text.strip():
            self._sink(text.rstrip("\n"))
        return len(text)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def isatty(self):
        return False

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8") or "utf-8"

    @property
    def errors(self):
        return getattr(self._original, "errors", "replace") or "replace"
