"""给 CLI 和 GUI 共用的高层入口。

界面层只跟这里的函数打交道，不需要知道 meta / paths / arguments 这些细节。
这里的函数都尽量做成“可被后台线程调用”的纯阻塞函数；UI 负责把它们放进
``asyncio.to_thread``。
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from a2cr_launcher import instance, settings
from a2cr_launcher.core.download import DownloadCancelled
from a2cr_launcher.core.paths import (
    ASSETS_DIR,
    INSTANCES_DIR,
    LIBRARIES_DIR,
    LOG_CONFIGS_DIR,
    ROOT_DIR,
    SETTINGS_FILE,
    TRASH_DIR,
    VERSIONS_DIR,
    create_launcher_dirs,
)
from a2cr_launcher.java.discover import java_executable
from a2cr_launcher.java.discover import list_java_runtimes as _list_java_runtimes
from a2cr_launcher.launch.arguments import build_arguments
from a2cr_launcher.launch.install import ensure_natives_dirs, install
from a2cr_launcher.launch.process import launch
from a2cr_launcher.meta.manifest import get_version_manifest
from a2cr_launcher.meta.merge import resolve_meta
from a2cr_launcher.meta.versions import get_version_meta
from a2cr_launcher.modpack import detect as detect_modpack
from a2cr_launcher.modpack import import_pack


class LaunchError(RuntimeError):
    """启动前的可预期错误（Java 缺失、版本格式太旧等）。"""


class MissingFilesError(LaunchError):
    """启动前检查发现 classpath 里的文件不齐。"""

    def __init__(self, version_id: str, missing: list[str]):
        self.version_id = version_id
        self.missing = missing
        super().__init__(f"缺少 {len(missing)} 个运行库或客户端文件，请先安装 {version_id}")


def ensure_data_dirs() -> None:
    """创建启动器目录。issue #4：首次启动没有目录时不应该直接崩。"""
    create_launcher_dirs()


def data_dirs() -> dict:
    """给设置页展示所有目录，避免 UI 自己拼路径。"""
    return {
        "root": str(ROOT_DIR),
        "instances": str(INSTANCES_DIR),
        "versions": str(VERSIONS_DIR),
        "assets": str(ASSETS_DIR),
        "libraries": str(LIBRARIES_DIR),
        "logs": str(LOG_CONFIGS_DIR),
        "trash": str(TRASH_DIR),
        "settings": str(SETTINGS_FILE),
    }


def load_settings() -> dict:
    """读取设置（文件损坏时返回默认值）。"""
    return settings.load_settings()


def save_settings(changes: dict | None = None, **kwargs) -> dict:
    """保存设置，支持传整个 dict 或零散关键字参数。"""
    merged = dict(changes or {})
    merged.update(kwargs)
    current = settings.load_settings()
    current.update(merged)
    return settings.save_settings(current)


def list_installed() -> list[str]:
    """已安装的版本号（有 client.jar 就算装了）。保留给旧调用方。"""
    return sorted(path.parent.name for path in Path(VERSIONS_DIR).glob("*/client.jar"))


def list_installed_versions() -> list[dict]:
    """列出所有带版本 JSON 的版本，包括 Fabric/Forge 这类加载器版本。

    旧版 ``list_installed`` 只看 client.jar，会漏掉加载器版本；界面需要区分
    “原版”和“加载器”，所以这里直接读本地 JSON，不触发网络请求。
    """
    result: list[dict] = []
    try:
        folders = sorted(Path(VERSIONS_DIR).iterdir(), key=lambda path: path.name.lower(), reverse=True)
    except OSError:
        return result

    for folder in folders:
        if not folder.is_dir():
            continue
        meta_path = Path(folder, f"{folder.name}.json")
        try:
            with open(meta_path, "r", encoding="utf-8") as file:
                meta = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(meta, dict):
            continue
        result.append({
            "id": folder.name,
            "type": meta.get("type", "release"),
            "base_version": meta.get("inheritsFrom") or meta.get("_baseVersion") or folder.name,
            "loader": "vanilla" if not meta.get("inheritsFrom") else "modded",
            "has_client": Path(folder, "client.jar").is_file(),
            "path": str(folder),
        })
    return result


def list_instances() -> list[dict]:
    """列出整合包实例，并补上界面卡片需要的展示字段。"""
    result = []
    for meta in instance.list_all():
        directory = instance.instance_dir(meta.get("folder", ""))
        loader = meta.get("loader") or {}
        mods_count = 0
        try:
            mods_count = sum(1 for item in Path(directory, "mods").iterdir() if item.is_file())
        except OSError:
            pass
        item = dict(meta)
        item.update({
            "path": str(directory),
            "loader_type": loader.get("type", "vanilla"),
            "loader_version": loader.get("version", ""),
            "source_format": (meta.get("source") or {}).get("format", ""),
            "mods_count": mods_count,
        })
        result.append(item)
    return result


def inspect_modpack(path: str | Path) -> dict:
    """只解析整合包，不安装；给导入向导做预检。"""
    plan = detect_modpack(Path(path))
    # Path 对象不能直接塞进 Flet 的数据结构，这里统一转成字符串
    plan = dict(plan)
    if "archive" in plan:
        plan["archive"] = str(plan["archive"])
    plan["file_count"] = len(plan.get("files") or [])
    return plan


def import_modpack(path: str | Path, name: str | None = None, *, on_log=None,
                   on_progress=None, cancel=None, update_folder: str | None = None) -> dict:
    """导入/更新整合包；所有回调都原样传给底层。"""
    ensure_data_dirs()
    return import_pack(
        Path(path),
        name=name,
        log=on_log or print,
        on_progress=on_progress,
        cancel=cancel,
        update_folder=update_folder,
    )


def list_versions(version_type: str = "release", limit: int = 0, prefer_cache: bool = False) -> list[dict]:
    """获取可安装的 Minecraft 版本列表。

    网络失败时底层会自动回退本地缓存；``prefer_cache=True`` 时直接读缓存，
    用于界面首次打开版本页，避免网络慢时长时间白屏。
    """
    versions = get_version_manifest(version_type, limit, prefer_cache=prefer_cache)
    return [
        {
            "id": str(item.get("id", "")),
            "type": item.get("type", "release"),
            "release_time": item.get("releaseTime") or item.get("time") or "",
        }
        for item in versions
        if item.get("id")
    ]


def list_java_runtimes() -> list[dict]:
    """列出 Java，包含设置里手动指定的那一个（即使它不在常见安装位置）。"""
    current = settings.load_settings()
    custom = current.get("java_path")
    return _list_java_runtimes(Path(custom)) if custom else _list_java_runtimes()


def is_valid_java_path(path: str) -> bool:
    """给设置页校验用户选的 Java 目录/可执行文件。"""
    return java_executable(path) is not None


def install_version(version_id: str, on_progress=None, cancel=None) -> bool:
    """下载并装好一个版本。on_progress 签名见 core.download.download。"""
    ensure_data_dirs()
    meta = get_version_meta(version_id, refresh=True)
    return install(meta, on_progress=on_progress, cancel=cancel)


def _launch(version_id: str, game_dir: Path, max_memory: str = "4G", name: str = "a2Cr",
            on_log=None, on_process=None, java_path: str | None = None) -> int:
    """命令行和界面共用的启动流程：解析 inheritsFrom、检查文件、启动进程。"""
    ensure_data_dirs()
    meta = resolve_meta(version_id)

    game_dir = Path(game_dir)
    game_dir.mkdir(parents=True, exist_ok=True)
    try:
        ensure_natives_dirs(version_id)
    except OSError as err:
        raise LaunchError(f"无法创建 natives 目录：{err}") from err

    if not isinstance(meta.get("arguments"), dict):
        raise LaunchError("这个版本用的是旧的启动参数格式（1.13 以前），当前启动器还不支持。")

    try:
        arguments = build_arguments(meta, game_dir, name=name, max_memory=max_memory, java_path=java_path)
    except RuntimeError as err:
        raise LaunchError(str(err)) from err
    except (KeyError, TypeError, ValueError) as err:
        raise LaunchError(f"版本信息不完整或已损坏：{err}") from err

    # 开游戏之前先确认文件齐不齐，否则 Java 只会抛一堆看不懂的 ClassNotFound
    if "-cp" in arguments:
        classpath = arguments[arguments.index("-cp") + 1]
        missing = [item for item in classpath.split(os.pathsep) if item and not Path(item).is_file()]
        if missing:
            raise MissingFilesError(meta.get("_baseVersion", version_id), missing)

    try:
        return launch(arguments, game_dir, on_log=on_log, on_process=on_process)
    except FileNotFoundError as err:
        raise LaunchError(f"启动 Java 失败，找不到可执行文件：{err}") from err
    except OSError as err:
        raise LaunchError(f"启动游戏失败：{err}") from err


def launch_version(version_id: str, max_memory: str = "4G", name: str = "a2Cr",
                   on_log=None, on_process=None, java_path: str | None = None) -> int:
    """启动一个原版/已安装版本，返回游戏进程退出码（会阻塞到游戏退出）。"""
    return _launch(version_id, Path(INSTANCES_DIR, version_id), max_memory=max_memory, name=name,
                   on_log=on_log, on_process=on_process, java_path=java_path)


def launch_instance(folder: str, max_memory: str = "4G", name: str = "a2Cr",
                    on_log=None, on_process=None, java_path: str | None = None) -> int:
    """启动一个整合包实例，游戏目录就是实例目录。"""
    meta = instance.load(folder)
    if meta is None:
        raise LaunchError(f"找不到实例：{folder}")

    def _started(proc):
        # 进程真正创建后再记录最近游玩时间，启动失败（比如 Java 缺失）不会污染排序
        meta["last_played"] = datetime.now().isoformat(timespec="seconds")
        try:
            instance.save(meta)
        except Exception:
            pass
        if on_process is not None:
            on_process(proc)

    return _launch(meta["version_id"], instance.instance_dir(meta["folder"]),
                   max_memory=max_memory, name=name, on_log=on_log,
                   on_process=_started, java_path=java_path)


def trash_instance(folder: str) -> Path:
    """把实例移入启动器回收站，返回移动后的路径。"""
    return instance.trash(folder)


def open_path(path: str | Path) -> None:
    """用系统文件管理器打开目录/文件。"""
    target = str(path)
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def instance_directory(folder: str) -> Path:
    """实例目录；UI 不直接 import instance 模块。"""
    return instance.instance_dir(folder)


def open_instance_folder(folder: str) -> None:
    """打开实例目录，不存在时先创建。"""
    directory = instance.instance_dir(folder)
    directory.mkdir(parents=True, exist_ok=True)
    open_path(directory)


def open_instance_log(folder: str) -> None:
    """打开实例的 latest.log；没有日志时退回到实例目录。"""
    directory = instance.instance_dir(folder)
    log_file = Path(directory, "logs", "latest.log")
    open_path(log_file if log_file.is_file() else directory)
