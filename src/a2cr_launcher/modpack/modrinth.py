"""Modrinth ``.mrpack`` 整合包解析。"""

import json
import zipfile
from pathlib import Path

# modrinth.index.json 里 dependencies 的键 -> 加载器类型
DEPENDENCY_LOADERS = {
    "fabric-loader": "fabric",
    "quilt-loader": "quilt",
    "forge": "forge",
    "neoforge": "neoforge",
}


def is_modrinth(archive: Path) -> bool:
    try:
        with zipfile.ZipFile(archive) as z:
            return "modrinth.index.json" in z.namelist()
    except zipfile.BadZipFile:
        return False


def read(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        index = json.loads(z.read("modrinth.index.json"))

    dependencies = index.get("dependencies") or {}
    mc_version = dependencies.get("minecraft")
    if not mc_version:
        raise ValueError("不是有效的 Modrinth 整合包：dependencies 里没有 minecraft 版本")

    loader_type, loader_version = "vanilla", ""
    for key, kind in DEPENDENCY_LOADERS.items():
        if dependencies.get(key):
            loader_type, loader_version = kind, str(dependencies[key])
            break

    files = []
    for item in index.get("files") or []:
        env = item.get("env") or {}
        if env.get("client") == "unsupported":
            continue
        downloads = item.get("downloads") or []
        if not downloads:
            continue
        files.append({
            "path": item["path"],
            "url": downloads[0],
            "sha1": (item.get("hashes") or {}).get("sha1", ""),
            "size": item.get("fileSize", 0),
        })

    overrides = [name.strip("/") for name in ("overrides", "client-overrides")
                 if any(entry.startswith(name + "/") for entry in names)]

    return {
        "format": "modrinth",
        "name": index.get("name") or Path(archive).stem,
        "pack_version": str(index.get("versionId") or ""),
        "mc_version": mc_version,
        "loader": loader_type,
        "loader_version": loader_version,
        "files": files,
        "overrides": overrides,
        "archive": Path(archive),
    }
