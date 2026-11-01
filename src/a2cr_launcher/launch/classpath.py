from os import pathsep
from pathlib import Path

from a2cr_launcher.launch.libraries import allowed_libraries, library_path


def build_classpath(meta, libraries_dir, os_name, os_arch, client_jar, include_client=True):
    """
    直接返回传入参数所使用的 classpath
    Args:
        client_jar (str): 版本 jar 的位置
        meta (dict): 版本 meta 文件
        libraries_dir (Path):  运行库文件夹
        os_name (str): 系统名称
        os_arch (str): 系统架构
        include_client (bool): 是否把原版 client.jar 放进 classpath

    Returns:
        str: 可直接使用的 classpath
    """
    paths = []
    for library in allowed_libraries(meta, os_name, os_arch):
        path = library_path(library)
        if path is not None:
            paths.append(path)

    entries = [str(Path(libraries_dir, path)) for path in paths]
    if include_client:
        entries.append(str(client_jar))

    return pathsep.join(entries)
