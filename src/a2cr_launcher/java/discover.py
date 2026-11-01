import os
import re
import shutil
import subprocess
from pathlib import Path


def get_java_version(path) -> tuple[int, str] | None:
    """
    返回给定的 path 里的 Java 版本
    Args:
        path (Path): java 的根目录

    Returns:
        tuple[int, str] | None: 目录里的 Java 版本
    """
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
        with open(Path(file), 'r') as f:
            f_content = f.readlines()

        if f_content:
            for line in f_content:
                if line.startswith('JAVA_VERSION='):
                    return __analysis_version_code(line.split('=', 1)[1].strip().strip('"'))
        return None

    def __get_version_by_executable_file(file):
        application_return = subprocess.run([file, '-version'], capture_output=True, text=True).stderr
        v = re.search(r'version "([^"]+)"', application_return)
        return __analysis_version_code(v.group(1)) if v else None

    if not path.is_dir():
        return None

    # 根据 path 下的 release 文件判断版本
    if Path(path, 'release').is_file():
        version = __get_version_by_release_file(Path(path, 'release'))

    # 根据可执行文件结果判断版本
    if version == "" and java_path.is_file():
        version = __get_version_by_executable_file(java_path)

    return (int(version.split(".")[0]), version) if version else None


def list_jdks(*custom_paths: Path):
    searched: list[tuple[Path, int]] = []

    searches = [Path(str(os.getenv("JAVA_HOME"))),
                *list(Path(str(os.getenv("ProgramFiles")), "Zulu").glob("*")),
                *list(Path(str(os.getenv("ProgramFiles")), "Java").glob("*")),
                *list(Path(str(os.getenv("ProgramFiles")), "Eclipse Adoptium").glob("*")),
                *custom_paths]

    which_java = shutil.which("java")
    if which_java:
        root = Path(which_java).resolve().parent.parent
        if root.is_dir() and root not in searches:
            searches.append(root)

    for search in searches:
        r = get_java_version(search)
        if r is not None:
            searched.append((search, r[0]))

    # 去重
    jdk = list(set(searched))
    return jdk


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
        if java[1] == required:
            candidates.append((0, java[0]))
        elif java[1] > required:
            candidates.append((java[1] - required, java[0]))

    candidates.sort()

    if candidates:
        best_match = candidates[0]
    else:
        raise RuntimeError("未找到可使用的 Java 实例")

    return str(Path(best_match[1], "bin", "java.exe"))


if __name__ == "__main__":
    print(find_java(8, Path(r"C:\Users\Rxx\Desktop\zulu8.98.0.107-ca-jdk8.0.512-win_i686"),
                    Path(r"C:\Users\Rxx\Downloads\zulu27.30.109-ca-jdk27.0.1.0.3-win_x64")))
