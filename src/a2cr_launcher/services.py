from pathlib import Path

from a2cr_launcher.core.paths import INSTANCES_DIR
from a2cr_launcher.launch.arguments import build_arguments
from a2cr_launcher.launch.install import install
from a2cr_launcher.launch.process import launch
from a2cr_launcher.meta.versions import get_version_meta


def list_installed() -> list[str]:
    instances = Path(INSTANCES_DIR).glob("*")

    return list(str(instance) for instance in instances)  # 扫 INSTANCES_DIR


def install_version(version_id, on_progress=None) -> dict:
    meta = get_version_meta(version_id)
    return install(meta, on_progress=on_progress)


def launch_version(version_id) -> int:
    meta = get_version_meta(version_id)
    game_dir = Path(INSTANCES_DIR, version_id)
    return launch(build_arguments(meta, game_dir), game_dir)


if __name__ == "__main__":
    print(list_installed())
