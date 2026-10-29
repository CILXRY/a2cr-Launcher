import json
from pathlib import Path

from a2cr_launcher.core.download import download_file


def fetch_asset_index(meta, dest, sha1) -> dict:
    if download_file(meta, dest, sha1) != "failed":
        with open(Path(dest), 'r', encoding="utf-8") as f:
            a = json.load(f)
            return a
    else:
        raise RuntimeError(f"asset index 下载失败: {meta}")


def build_asset_downloads(objects_list: dict, assets_dir) -> list[tuple[str, Path, str, int]]:
    downloads = []
    for obj in objects_list:
        target = objects_list[obj]
        file_hash = target.get('hash')
        file_size = target.get('size')
        file_path = f"{file_hash[:2]}/{file_hash}"
        target_download = (f"https://resources.download.minecraft.net/{file_path}",
                           Path(assets_dir, "objects", file_path),
                           file_hash, file_size)
        downloads.append(target_download)

    return downloads


if __name__ == "__main__":
    from a2cr_launcher.meta.versions import get_version_meta
    from a2cr_launcher.core.paths import ASSETS_DIR

    asset_index: tuple = (get_version_meta('26.2').get('asset_index_url', ""),
                          get_version_meta('26.2').get('asset_index_sha1', ""))
    assets = fetch_asset_index(asset_index[0], Path(ASSETS_DIR, f'indexes/{asset_index[0].split("/")[-1]}'),
                               asset_index[1])

    print(len(assets.get('objects', {})))
    print(len(build_asset_downloads(assets.get('objects', {}), ASSETS_DIR)))
