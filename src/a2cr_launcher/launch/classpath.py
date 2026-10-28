from pathlib import Path

from a2cr_launcher.launch.rules import is_allowed
from a2cr_launcher.meta.versions import get_version_meta


def build_classpath(meta, libraries_dir: Path, os_name: str, os_arch: str) -> list[Path]:
    # allowed 过滤
    allowed = [l for l in meta["libraries"] if is_allowed(l.get("rules", []), os_name, os_arch)]

    # 取 path
    paths = [l['downloads']['artifact']['path'] for l in allowed]
    classpath = [Path(libraries_dir, path) for path in paths]

    return classpath


if __name__ == "__main__":
    meta_26_2 = get_version_meta("26.2")

    print(len(build_classpath(meta_26_2, Path("libraries"), "windows", "x86_64")))
    print(build_classpath(meta_26_2, Path("libraries"), "windows", "x86_64"))
    print(len(build_classpath(meta_26_2, Path("libraries"), "osx", "x86_64")))
