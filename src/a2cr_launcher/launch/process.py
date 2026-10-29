import subprocess
from pathlib import Path

from a2cr_launcher.core.paths import VERSIONS_DIR
from a2cr_launcher.launch.arguments import build_arguments
from a2cr_launcher.meta.versions import get_version_meta


def launch(cmd: list[str], game_dir: Path) -> int:
    proc = subprocess.Popen(
        cmd, cwd=game_dir,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    for line in proc.stdout:
        print(line, end="")
    return proc.wait()


if __name__ == "__main__":
    version = "26.2"
    launch(build_arguments(get_version_meta(version)), Path(VERSIONS_DIR, version))
