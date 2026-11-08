"""给 CLI 和 GUI 共用的高层入口。

界面层只跟这三个函数打交道，不需要知道 meta / paths / arguments 这些细节。
"""

from pathlib import Path

from a2cr_launcher.core.paths import INSTANCES_DIR, VERSIONS_DIR
from a2cr_launcher.launch.arguments import build_arguments
from a2cr_launcher.launch.install import install
from a2cr_launcher.launch.process import launch
from a2cr_launcher.meta.versions import get_version_meta


def list_installed() -> list[str]:
    """已安装的版本号（有 client.jar 就算装了）。"""
    return sorted(path.parent.name for path in Path(VERSIONS_DIR).glob("*/client.jar"))


def install_version(version_id: str, on_progress=None) -> bool:
    """下载并装好一个版本。on_progress 签名见 core.download.download。"""
    meta = get_version_meta(version_id, refresh=True)
    return install(meta, on_progress=on_progress)


def launch_version(version_id: str, max_memory: str = "4G", name: str = "a2Cr", on_log=None) -> int:
    """启动一个版本，返回游戏进程的退出码（会阻塞到游戏退出）。

    on_log(text) 会在每读到一行游戏输出时被调用；不传则打印到控制台。
    """
    meta = get_version_meta(version_id)
    game_dir = Path(INSTANCES_DIR, version_id)
    game_dir.mkdir(parents=True, exist_ok=True)
    return launch(build_arguments(meta, game_dir, name=name, max_memory=max_memory), game_dir,
                  on_log=on_log)
