from pathlib import Path

from a2cr_launcher.core.download import download_file, download
from a2cr_launcher.core.platform_info import current_platform
from a2cr_launcher.launch.libraries import build_library_downloads
from a2cr_launcher.meta.assets import build_asset_downloads, fetch_asset_index


def download_client(meta, versions_dir):
    # print(f"downloading {meta["downloads"]["client"]["url"]}")
    if download_file(meta["downloads"]["client"]["url"],
                     Path(versions_dir, meta['id'], f"{meta["downloads"]["client"]["url"].split("/")[-1]}"),
                     meta["downloads"]["client"]["sha1"]) != "failed":
        return True
    return False


def download_logging(meta, assets_dir):
    try:
        target_file: dict = meta["logging"]["client"]["file"]
    except KeyError:
        target_file = {}
    if target_file:
        return download_file(target_file["url"], Path(assets_dir, "log_configs", target_file["id"]),
                             target_file["sha1"]) != "failed"
    return True


def download_assets(meta, assets_dir):
    asset_index: tuple = (meta["assetIndex"].get("url", ""),
                          meta['assetIndex'].get('sha1', ""))
    assets = fetch_asset_index(asset_index[0], Path(assets_dir, f'indexes/{asset_index[0].split("/")[-1]}'),
                               asset_index[1])

    if download(build_asset_downloads(assets.get('objects', {}), assets_dir)):
        return True
    return False


def download_libraries(meta, libraries_dir):
    libs = build_library_downloads(meta, libraries_dir, current_platform()[0], current_platform()[1])
    if download(libs):
        return True
    return False
