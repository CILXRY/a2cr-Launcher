from pathlib import Path

from a2cr_launcher.launch.rules import is_allowed

DEFAULT_MAVEN = "https://libraries.minecraft.net/"


def library_path(library: dict) -> str | None:
    """
    返回运行库在 libraries 目录下的相对路径。

    版本 JSON 里有两种写法：
      - 原版：downloads.artifact.path
      - Fabric/Forge 等：只给 maven 坐标 name（group:artifact:version[:classifier]）和 url
    """
    artifact = (library.get("downloads") or {}).get("artifact") or {}
    if artifact.get("path"):
        return artifact["path"]

    name = library.get("name")
    if not name:
        return None

    parts = name.split(":")
    if len(parts) < 3:
        return None

    group, artifact_id, version = parts[0], parts[1], parts[2]
    classifier = parts[3] if len(parts) > 3 else ""
    filename = f"{artifact_id}-{version}" + (f"-{classifier}" if classifier else "") + ".jar"
    return "/".join(group.split(".") + [artifact_id, version, filename])


def allowed_libraries(meta, os_name, os_arch) -> list[dict]:
    return [library for library in meta.get("libraries", [])
            if is_allowed(library.get("rules", []), os_name, os_arch)]


def build_library_downloads(meta, libraries_dir, os_name, os_arch) -> list[tuple[str, Path, str, int]]:
    """
    组织 library 的下载列表
    :param meta: 版本 meta
    :param libraries_dir: 运行库目录
    :param os_name: 系统名称
    :param os_arch: 系统架构
    :return: list[tuple[下载 URL, 下载存放路径, 文件sha1, 文件大小]]
    """
    downloads = []
    for library in allowed_libraries(meta, os_name, os_arch):
        path = library_path(library)
        if path is None:
            continue

        artifact = (library.get("downloads") or {}).get("artifact") or {}
        if artifact.get("url"):
            url = artifact["url"]
            sha1 = artifact.get("sha1", "")
            size = artifact.get("size", 0)
        else:
            url = (library.get("url") or DEFAULT_MAVEN).rstrip("/") + "/" + path
            sha1 = library.get("sha1", "")
            size = library.get("size", 0)

        downloads.append((url, Path(libraries_dir, path), sha1, size))
    return downloads
