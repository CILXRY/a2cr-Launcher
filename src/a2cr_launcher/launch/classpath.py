from os import pathsep
from pathlib import Path

from a2cr_launcher.launch.rules import is_allowed


def build_classpath(meta, libraries_dir, os_name, os_arch):
    """
    直接返回传入参数所使用的 classpath
    Args:
        meta (dict): 版本 meta 文件
        libraries_dir (Path):  运行库文件夹
        os_name (str): 系统名称
        os_arch (str): 系统架构

    Returns:
        str: 可直接使用的 classpath
    """
    # allowed 过滤
    allowed = [l for l in meta["libraries"] if is_allowed(l.get("rules", []), os_name, os_arch)]

    # 取 path
    paths = [l['downloads']['artifact']['path'] for l in allowed]
    classpath = f"{pathsep}".join(str(Path(libraries_dir, path)) for path in paths)

    return classpath
