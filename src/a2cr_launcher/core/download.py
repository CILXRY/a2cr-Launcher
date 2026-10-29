import hashlib
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from pathlib import Path
from time import sleep

import requests

MAX_RETRY = 3
MAX_WORKERS = 8
# 下载分片大小
CHUNK_SIZE = 1024 * 1024


def _hash_file(file_path):
    with open(file_path, 'rb') as file:
        digest = hashlib.file_digest(file, 'sha1')
        return digest.hexdigest()


def _create_dir(file_path):
    Path(file_path).mkdir(parents=True, exist_ok=True)


def _download_file_to_disk(url, file_path):
    """
    单次请求的文件下载函数
    :param url: 文件地址
    :param file_path: 文件地址
    :return: 没有返回值
    """
    # 建立请求
    req = requests.get(url, stream=True, timeout=10)
    # 进度初始化
    downloaded = 0

    req.raise_for_status()

    # 分片下载文件
    with open(file_path, 'wb') as f:
        # 用 iter_content 来给文件分片, 分到各个 chunk 里
        # 不要把 for 循环和 with 的顺序写反, 否则到最后就只剩最后的那个 chunk的内容了
        for chunk in req.iter_content(CHUNK_SIZE):
            # 写入
            f.write(chunk)
            downloaded += len(chunk)


def download_file(url: str, dest: Path, file_sha1: str = "") -> str:
    """
    对外所用的文件下载, 集成了 文件哈希,错误重试,创建文件 的整体函数
    :param dest: 目标文件夹位置
    :param file_sha1: 文件哈希
    :param url: 文件地址
    :return: 正常下载返回 success, 下载出错(最大尝试之后都出错)返回 failed, 跳过下载(哈希校验)返回 skipped
    """

    # 文件路径和默认哈希
    file_path = Path(dest)
    temp_file_path = file_path.with_suffix(file_path.suffix + ".part")

    # 创建目标文件夹
    _create_dir(dest.parent)

    # 检测有没有原有文件（强制哈希校验）
    if file_path.is_file() and _hash_file(file_path) == file_sha1:
        return "skipped"

    # print(f"准备下载 {file_path}")
    for _ in range(MAX_RETRY):
        try:
            _download_file_to_disk(url, temp_file_path)
        except requests.RequestException as e:
            print(f"下载请求出错，重试。\n错误原因: {e}")
            sleep(1)
            continue
        try:
            sha1 = _hash_file(temp_file_path)
        except FileNotFoundError as e:
            print(f"文件 {file_path} 不存在，重新尝试")
            continue
        if not file_sha1 or sha1 == file_sha1:
            temp_file_path.replace(file_path)
            # print(f"下载 {file_path} 完成")
            return "success"

        else:
            print(f"Hash 校验出错, 重试...")
    return "failed"


def download(targets: list[tuple[str, Path, str, int]]):
    done = success = skipped = failed = 0
    failed_dest = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_file, url, dest, sha1): dest for url, dest, sha1, _ in targets}
        for f in as_completed(futures):
            dest = futures[f]
            done += 1
            try:
                result = f.result()
            except Exception as e:
                failed += 1
                failed_dest[dest] = f"{type(e).__name__}: {e}"
                continue
            if result == "success":
                success += 1
            elif result == "failed":
                failed += 1
                failed_dest[dest] = "download failed"
            elif result == "skipped":
                skipped += 1
            print(f"[{done}/{len(targets)}] {result:7s} {dest.name}")
        print("==" * 20)
        print(f"结束：成功 {success} 个，跳过 {skipped} 个，失败 {failed} 个。\n")
        if success + skipped + failed != len(targets):
            print(f"有任务丢失，请尝试重新下载。")
        if failed_dest:
            print(f"失败列表：\n", "\n".join(map(str, failed_dest.items())))


if __name__ == '__main__':
    from a2cr_launcher.meta.versions import get_version_meta
    from a2cr_launcher.core.paths import ASSETS_DIR
    from a2cr_launcher.meta.assets import build_asset_downloads, fetch_asset_index

    asset_index: tuple = (get_version_meta('26.2').get('asset_index_url', ""),
                          get_version_meta('26.2').get('asset_index_sha1', ""))
    assets = fetch_asset_index(asset_index[0], Path(ASSETS_DIR, f'indexes/{asset_index[0].split("/")[-1]}'),
                               asset_index[1])
    download(build_asset_downloads(assets.get('objects', {}), ASSETS_DIR))
