import subprocess
from pathlib import Path


def launch(cmd: list[str], game_dir: Path) -> int:
    proc = subprocess.Popen(
        cmd, cwd=game_dir,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    for line in proc.stdout:
        print(line, end="")
    return proc.wait()
