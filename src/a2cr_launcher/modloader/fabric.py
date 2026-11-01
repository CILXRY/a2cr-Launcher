"""Fabric / Quilt 加载器安装。

这两个加载器的元数据接口直接给出「带 inheritsFrom 的版本 JSON」，
里面包含 mainClass、maven 运行库、sha1 和大小，照着下载就行。
"""

import json
from pathlib import Path

from a2cr_launcher.core.download import download
from a2cr_launcher.core.http_util import http_get
from a2cr_launcher.core.paths import LIBRARIES_DIR, VERSIONS_DIR
from a2cr_launcher.core.platform_info import current_platform
from a2cr_launcher.launch.libraries import build_library_downloads

META_URLS = {
    "fabric": "https://meta.fabricmc.net/v2/versions/loader/{mc}/{loader}/profile/json",
    "quilt": "https://meta.quiltmc.org/v3/versions/loader/{mc}/{loader}/profile/json",
}
LIST_URLS = {
    "fabric": "https://meta.fabricmc.net/v2/versions/loader/{mc}",
    "quilt": "https://meta.quiltmc.org/v3/versions/loader/{mc}",
}


def latest_loader(mc_version: str, flavor: str = "fabric") -> str:
    """获取指定 Minecraft 版本最新的加载器版本号。"""
    data = http_get(LIST_URLS[flavor].format(mc=mc_version)).json()
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"{flavor} 没有找到适配 Minecraft {mc_version} 的加载器")
    return data[0]["loader"]["version"]


def install(mc_version: str, loader_version: str | None = None, flavor: str = "fabric") -> str:
    """
    安装 Fabric / Quilt 加载器。

    Args:
        mc_version: Minecraft 版本
        loader_version: 加载器版本，为空时取最新
        flavor: "fabric" 或 "quilt"

    Returns:
        str: 安装后可以传给启动器的版本 id
    """
    if not loader_version:
        loader_version = latest_loader(mc_version, flavor)

    profile = http_get(META_URLS[flavor].format(mc=mc_version, loader=loader_version)).json()
    version_id = profile.get("id") or f"{flavor}-loader-{loader_version}-{mc_version}"

    version_dir = Path(VERSIONS_DIR, version_id)
    version_dir.mkdir(parents=True, exist_ok=True)
    with open(Path(version_dir, f"{version_id}.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    downloads = build_library_downloads(profile, LIBRARIES_DIR, *current_platform())
    if downloads and not download(downloads, description=f"{flavor} 运行库"):
        raise RuntimeError(f"{flavor} 运行库下载失败，请重新运行安装")

    return version_id
