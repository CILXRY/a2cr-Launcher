from pathlib import Path

from a2cr_launcher.core.download import download
from a2cr_launcher.core.paths import VERSIONS_DIR, ASSETS_DIR, LOG_CONFIGS_DIR, LIBRARIES_DIR
from a2cr_launcher.core.platform_info import current_platform
from a2cr_launcher.launch.libraries import build_library_downloads
from a2cr_launcher.meta.assets import build_asset_downloads, fetch_asset_index


def install(meta,
            on_progress=None,
            versions_dir=VERSIONS_DIR,
            libraries_dir=LIBRARIES_DIR,
            assets_dir=ASSETS_DIR,
            log_configs_dir=LOG_CONFIGS_DIR):
    """

    Args:
        on_progress:
        meta: 版本元文件
        versions_dir (Path): 版本文件夹
        libraries_dir (Path): 库文件夹
        assets_dir (Path): 资源文件夹
        log_configs_dir (Path): Logging 配置文件夹

    Returns:

    """
    dl = []

    # client
    client_file = meta["downloads"]["client"]
    client = (client_file["url"], Path(versions_dir, meta['id'], f"{client_file["url"].split("/")[-1]}"),
              client_file["sha1"], client_file["size"])
    dl.append(client)

    # logging
    logging_file = meta["logging"]["client"]["file"]
    logging = (logging_file["url"], Path(log_configs_dir, logging_file["id"]),
               logging_file["sha1"], logging_file["size"])

    dl.append(logging)

    # assets
    assets_files = fetch_asset_index(meta["assetIndex"].get("url", ""),
                                     Path(assets_dir, f'indexes/{meta["assetIndex"].get("url", "").split("/")[-1]}'),
                                     meta['assetIndex'].get('sha1', ""))
    assets = build_asset_downloads(assets_files.get('objects', {}), assets_dir)
    dl.extend(assets)

    # libraries
    libs = build_library_downloads(meta, libraries_dir, current_platform()[0], current_platform()[1])
    dl.extend(libs)

    result = download(dl, on_progress)
    if result.get("failed"):
        raise RuntimeError("有文件下载失败")
    return result


if __name__ == "__main__":
    # print(build_downloads(get_version_meta("26.2")))
    pass
