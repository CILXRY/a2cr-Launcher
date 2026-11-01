from pathlib import Path

from a2cr_launcher.core.download import download_file, download
from a2cr_launcher.core.paths import VERSIONS_DIR
from a2cr_launcher.core.platform_info import current_platform
from a2cr_launcher.launch.libraries import build_library_downloads
from a2cr_launcher.meta.assets import build_asset_downloads, fetch_asset_index


def ensure_natives_dirs(version: str) -> Path:
    """创建 natives 目录：LWJGL / JNA / Netty 启动时会往这些子目录里解压本地库。"""
    natives = Path(VERSIONS_DIR, version, "natives")
    natives.mkdir(parents=True, exist_ok=True)
    for sub in ("java", "jna", "lwjgl", "netty"):
        (natives / sub).mkdir(parents=True, exist_ok=True)
    return natives


def download_client(meta, dest_dir):
    client = meta["downloads"]["client"]
    return download_file(client["url"],
                         Path(dest_dir, meta['id'], client["url"].split("/")[-1]),
                         client["sha1"], client.get("size", 0)) != "failed"


def download_logging(meta, dest_dir):
    try:
        target_file: dict = meta["logging"]["client"]["file"]
    except KeyError:
        target_file = {}
    if target_file:
        return download_file(target_file["url"], Path(dest_dir, target_file["id"]),
                             target_file["sha1"], target_file.get("size", 0)) != "failed"
    return True


def download_assets(meta, dest_dir):
    asset_index = meta["assetIndex"]
    index_url = asset_index.get("url", "")
    assets = fetch_asset_index(index_url,
                               Path(dest_dir, f'indexes/{index_url.split("/")[-1]}'),
                               asset_index.get("sha1", ""))
    return download(build_asset_downloads(assets.get('objects', {}), dest_dir), description="资源文件")


def download_libraries(meta, dest_dir):
    libs = build_library_downloads(meta, dest_dir, current_platform()[0], current_platform()[1])
    return download(libs, description="运行库")
