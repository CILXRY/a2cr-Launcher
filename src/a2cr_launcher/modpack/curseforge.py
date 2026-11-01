"""CurseForge 整合包（manifest.json + overrides）解析。

CurseForge 清单里只有 projectID / fileID，需要额外解析出文件名和下载地址。
优先用 MCIM 的 CurseForge 镜像接口（带 downloadUrl 和 sha1），失败再退回官网接口 + CDN 拼接。
"""

import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import requests

from a2cr_launcher.core.http_util import http_get

FILE_API = "https://mod.mcimirror.top/curseforge/v1/mods/{project}/files/{file_id}"
FILE_API_FALLBACK = "https://www.curseforge.com/api/v1/mods/{project}/files/{file_id}"
CDN_URL = "https://mediafilez.forgecdn.net/files/{major}/{minor}/{name}"

LOADER_PREFIXES = {"forge": "forge", "neoforge": "neoforge", "fabric": "fabric", "quilt": "quilt"}


def is_curseforge(archive: Path) -> bool:
    try:
        with zipfile.ZipFile(archive) as z:
            if "manifest.json" not in z.namelist():
                return False
            data = json.loads(z.read("manifest.json"))
    except (zipfile.BadZipFile, json.JSONDecodeError, OSError):
        return False
    return isinstance(data, dict) and "minecraft" in data and "files" in data


def _cdn_url(file_id: int, filename: str) -> str:
    return CDN_URL.format(major=file_id // 1000, minor=file_id % 1000, name=quote(filename))


def resolve_file(project_id: int, file_id: int) -> dict:
    """解析一个 CurseForge 文件的文件名 / 下载地址 / sha1 / 大小。"""
    data = None
    try:
        data = http_get(FILE_API.format(project=project_id, file_id=file_id)).json().get("data")
    except (requests.RequestException, ValueError, AttributeError):
        data = None

    if not data:
        data = http_get(FILE_API_FALLBACK.format(project=project_id, file_id=file_id)).json()["data"]

    filename = data.get("fileName") or ""
    url = data.get("downloadUrl") or _cdn_url(file_id, filename)
    sha1 = ""
    for digest in data.get("hashes") or []:
        if digest.get("algo") == 1:
            sha1 = digest.get("value", "")
            break

    return {
        "path": f"mods/{filename}",
        "url": url,
        "sha1": sha1,
        "size": data.get("fileLength") or 0,
    }


def resolve_files(files: list[dict], on_progress=None) -> list[dict]:
    """并行解析清单里的所有文件，保持顺序。"""
    resolved: list[dict] = []
    total = len(files)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(resolve_file, item["project"], item["file_id"]) for item in files]
        for index, future in enumerate(futures, start=1):
            resolved.append(future.result())
            if on_progress:
                on_progress(index, total)
    return resolved


def read(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read("manifest.json"))
        names = z.namelist()

    minecraft = manifest.get("minecraft") or {}
    mc_version = minecraft.get("version")
    if not mc_version:
        raise ValueError("不是有效的 CurseForge 整合包：manifest.minecraft 里没有 version")

    loader_type, loader_version = "vanilla", ""
    loaders = minecraft.get("modLoaders") or []
    if loaders:
        raw = str(loaders[0].get("id", ""))
        for prefix, kind in LOADER_PREFIXES.items():
            if raw.startswith(prefix + "-"):
                loader_type, loader_version = kind, raw[len(prefix) + 1:]
                break

    info = manifest.get("manifest") or {}
    overrides = str(manifest.get("overrides") or "overrides").strip("/")
    overrides = [overrides] if any(entry.startswith(overrides + "/") for entry in names) else []

    files = [{"project": item["projectID"], "file_id": item["fileID"]}
             for item in manifest.get("files") or [] if item.get("required", True)]

    return {
        "format": "curseforge",
        "name": info.get("name") or Path(archive).stem,
        "pack_version": str(info.get("version") or ""),
        "mc_version": mc_version,
        "loader": loader_type,
        "loader_version": loader_version,
        "files": files,
        "overrides": overrides,
        "archive": Path(archive),
    }
