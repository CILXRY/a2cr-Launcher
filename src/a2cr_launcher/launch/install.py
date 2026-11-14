import json
from pathlib import Path

from a2cr_launcher.core.download import download_file, download
from a2cr_launcher.core.paths import VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR, LOG_CONFIGS_DIR
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


def install(meta, on_progress=None, cancel=None) -> bool:
    """
    一次性装齐某个版本所需的全部文件（资源索引 / client / logging / libraries / assets）。

    Args:
        meta (dict): 版本 meta
        on_progress (callable | None): on_progress(已完成数, 总数, 文件名, 状态)，给 GUI 用。
            传了这个就不再往控制台打进度条。
        cancel (callable | None): 返回 True 时中止下载，给 GUI 的“取消”按钮用。

    Returns:
        bool: 全部成功返回 True

    Raises:
        RuntimeError: 有文件下载失败
        DownloadCancelled: 用户取消
    """
    version = meta["id"]
    ensure_natives_dirs(version)

    # 资源索引必须先单独拿到，才能知道要下哪些 objects
    index = meta["assetIndex"]
    index_path = Path(ASSETS_DIR, "indexes", index["url"].split("/")[-1])
    if download_file(index["url"], index_path, index.get("sha1", ""),
                     index.get("size", 0), verbose=False, cancel=cancel) == "failed":
        raise RuntimeError(f"资源索引下载失败: {index['url']}")
    with open(index_path, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    targets: list[tuple[str, Path, str, int]] = []

    client = meta["downloads"]["client"]
    targets.append((client["url"],
                    Path(VERSIONS_DIR, version, client["url"].split("/")[-1]),
                    client["sha1"], client.get("size", 0)))

    log_file = ((meta.get("logging") or {}).get("client") or {}).get("file")
    if log_file:
        targets.append((log_file["url"],
                        Path(LOG_CONFIGS_DIR, log_file["id"]),
                        log_file["sha1"], log_file.get("size", 0)))

    targets += build_library_downloads(meta, LIBRARIES_DIR, *current_platform())
    targets += build_asset_downloads(index_data.get("objects", {}), ASSETS_DIR)

    ok = download(targets,
                  show_progress=on_progress is None,
                  description=f"安装 {version}",
                  on_progress=on_progress,
                  cancel=cancel)
    if not ok:
        raise RuntimeError(f"{version} 有文件下载失败，重新运行即可继续补下")
    return True

