from pathlib import Path

from a2cr_launcher.launch.rules import is_allowed


def build_library_downloads(meta, libraries_dir, os_name, os_arch) -> list[tuple[str, Path, str, int]]:
    """
    组织 library 的下载列表
    :param meta:
    :param libraries_dir:
    :param os_name:
    :param os_arch:
    :return: list[tuple[下载 URL, 下载存放路径, 文件sha1, 文件大小]]
    """
    # allowed 过滤
    allowed = [l for l in meta["libraries"] if is_allowed(l.get("rules", []), os_name, os_arch)]

    downloads = [(l["downloads"]["artifact"]["url"], Path(libraries_dir, l['downloads']['artifact']['path']),
                  l["downloads"]["artifact"]["sha1"], l["downloads"]["artifact"]["size"])
                 for l in allowed]
    return downloads


if "__main__" == __name__:
    pass
