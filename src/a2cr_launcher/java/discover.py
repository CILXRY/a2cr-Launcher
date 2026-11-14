import os
import re
import shutil
import subprocess
from pathlib import Path


def _iter_subdirs(root: Path) -> list[Path]:
    """列出目录下的子目录，目录不存在或没有权限时返回空列表。"""
    try:
        return [path for path in root.iterdir() if path.is_dir()]
    except OSError:
        return []


def _mojang_runtime_roots() -> list[Path]:
    """官方启动器 / 微软商店版启动器下载 Java 运行时的位置。"""
    roots = []
    appdata = os.getenv("APPDATA")
    if appdata:
        roots.append(Path(appdata, ".minecraft", "runtime"))
    localappdata = os.getenv("LOCALAPPDATA")
    if localappdata:
        roots.append(Path(localappdata, "Packages", "Microsoft.4297127D64EC6_8wekyb3d8bbwe",
                          "LocalCache", "Local", "runtime"))
    return roots


def get_java_version(path) -> tuple[int, str] | None:
    """
    返回给定的 path 里的 Java 版本
    Args:
        path (Path): java 的根目录

    Returns:
        tuple[int, str] | None: 目录里的 Java 版本
    """
    path = Path(path)
    java_path = Path(path, 'bin', "java.exe")
    version = ''

    def __analysis_version_code(version_code):
        """
        为了解析一些 <= Java 9 的版本号，因为这些版本的 Java 版本号会写成 '1.X.X_XXX'
        Args:
            version_code (str): 传入的版本号

        Returns:
            str: 解析到的实际版本号
        """
        if version_code.split('.')[0] == '1':
            version_code = ".".join(version_code.split('.')[1:])
        return version_code

    def __get_version_by_release_file(file):
        try:
            with open(Path(file), 'r', encoding="utf-8", errors="replace") as f:
                f_content = f.readlines()
        except OSError:
            return None

        if f_content:
            for line in f_content:
                if line.startswith('JAVA_VERSION='):
                    return __analysis_version_code(line.split('=', 1)[1].strip().strip('"'))
        return None

    def __get_version_by_executable_file(file):
        try:
            application_return = subprocess.run([str(file), '-version'], capture_output=True, text=True,
                                                timeout=10).stderr
        except (OSError, subprocess.SubprocessError):
            return None
        v = re.search(r'version "([^"]+)"', application_return)
        return __analysis_version_code(v.group(1)) if v else None

    if not path.is_dir():
        return None

    # 根据 path 下的 release 文件判断版本
    if Path(path, 'release').is_file():
        version = __get_version_by_release_file(Path(path, 'release')) or ""

    # 根据可执行文件结果判断版本
    if version == "" and java_path.is_file():
        version = __get_version_by_executable_file(java_path) or ""

    return (int(version.split(".")[0]), version) if version else None


def list_jdks(*custom_paths: Path):
    """返回 ``(Java 目录, 主版本)`` 列表，保持 CLI 原有的返回格式。"""
    return [(path, major) for path, major, _version in _collect_jdks(*custom_paths)]


def _collect_jdks(*custom_paths: Path) -> list[tuple[Path, int, str]]:
    """扫描常见的 Java 安装位置，返回 ``(目录, 主版本, 完整版本)``。

    把“搜索”和“转换格式”拆开，是因为 CLI 只需要主版本，而设置界面想给用户
    显示完整的 Java 版本号（例如 25.0.1）。
    """
    searches: list[Path] = []

    java_home = os.getenv("JAVA_HOME")
    if java_home:
        searches.append(Path(java_home))

    program_files = os.getenv("ProgramFiles")
    if program_files:
        base = Path(program_files)
        for vendor in ("Zulu", "Java", "Eclipse Adoptium", "Microsoft", "BellSoft", "Amazon Corretto", "Semeru"):
            searches.extend(_iter_subdirs(base / vendor))

    # 官方启动器自带的 Java（26.x 需要的 Java 25 通常就在这里）
    for runtime_root in _mojang_runtime_roots():
        searches.extend(_iter_subdirs(runtime_root))

    searches.extend(Path(path) for path in custom_paths)

    which_java = shutil.which("java")
    if which_java:
        root = Path(which_java).resolve().parent.parent
        if root.is_dir():
            searches.append(root)

    found: list[tuple[Path, int, str]] = []
    for search in searches:
        result = get_java_version(search)
        if result is not None:
            found.append((search, result[0], result[1]))

    # 去重，同时保持顺序
    return list(dict.fromkeys(found))


def list_java_runtimes(*custom_paths: Path) -> list[dict]:
    """给 GUI 用的 Java 列表，按主版本从新到旧排列。"""
    runtimes = [
        {"path": str(path), "major": major, "version": version}
        for path, major, version in _collect_jdks(*custom_paths)
    ]
    runtimes.sort(key=lambda item: (-item["major"], item["path"].lower()))
    return runtimes


def java_executable(path) -> str | None:
    """把用户选的 Java 目录/可执行文件解析成真正的 java 路径。

    设置界面允许用户选目录（更直观），也允许直接选 ``java.exe``。传入的路径
    不存在或不像 Java 时返回 ``None``，由调用方决定是回退到自动发现还是报错。
    """
    target = Path(path)
    if target.is_file():
        return str(target)
    name = "java.exe" if os.name == "nt" else "java"
    candidate = Path(target, "bin", name)
    if candidate.is_file():
        return str(candidate)
    return None


def find_java(required, *custom_paths):
    """
    寻找一个等于或高于给定版本的 Java
    Args:
        required (int): 需要的 Java 版本号
        *custom_paths (Path): 自定义 Java 寻找池

    Returns:
        str: Java 路径
    """
    javas = list_jdks(*custom_paths)

    # candidates 是一个包括和目标Java版本差值的列表
    candidates = []

    for java in javas:
        if java[1] >= required:
            candidates.append((java[1] - required, java[0]))

    candidates.sort()

    if not candidates:
        raise RuntimeError(
            f"没有找到 Java {required} 或更高版本。请安装 Java {required}，"
            f"或者把 JAVA_HOME 指向已有的 Java {required} 安装目录。")

    best_match = candidates[0]
    java_name = "java.exe" if os.name == "nt" else "java"
    return str(Path(best_match[1], "bin", java_name))


if __name__ == "__main__":
    print(find_java(8, Path(r"C:\Users\Rxx\Desktop\zulu8.98.0.107-ca-jdk8.0.512-win_i686"),
                    Path(r"C:\Users\Rxx\Downloads\zulu27.30.109-ca-jdk27.0.1.0.3-win_x64")))
