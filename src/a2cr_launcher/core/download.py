import hashlib
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from logging import getLogger
from pathlib import Path
from time import sleep

import requests

MAX_RETRY = 3
MAX_WORKERS = 8
# 下载分片大小
CHUNK_SIZE = 1024 * 1024
log = getLogger(__name__)


def _hash_file(file_path):
    """
    对给定 file 进行 sha1 计算
    Args:
        file_path (Path): 目标文件路径

    Returns:
        str: 文件哈希
    """
    with open(file_path, 'rb') as file:
        digest = hashlib.file_digest(file, 'sha1')
        return digest.hexdigest()


def _download_file_to_disk(url, dest):
    """
    单次请求文件，将文件下载到本地函数
    Args:
        url (str): 文件 URL
        dest (Path): 文件路径

    Returns:
        None
    """
    # 建立请求
    req = requests.get(url, stream=True, timeout=10)
    # 进度初始化
    downloaded = 0

    req.raise_for_status()

    # 分片下载文件
    with open(dest, 'wb') as f:
        # 用 iter_content 来给文件分片, 分到各个 chunk 里
        # 不要把 for 循环和 with 的顺序写反, 否则到最后就只剩最后的那个 chunk的内容了
        for chunk in req.iter_content(CHUNK_SIZE):
            # 写入
            f.write(chunk)
            downloaded += len(chunk)


def download_file(url, dest, file_sha1=""):
    """
    对外所用的文件下载, 集成了 文件哈希,错误重试,创建文件 的整体函数
    Args:
        url (str): 文件地址
        dest (Path): 文件保存位置
        file_sha1 (str): 文件哈希

    Returns:
        str: 结果："success", "failed", "skipped" 其中之一

    """

    # 文件路径和默认哈希
    file_path = Path(dest)
    temp_file_path = file_path.with_suffix(file_path.suffix + ".part")

    # 创建目标文件夹
    Path(dest.parent).mkdir(parents=True, exist_ok=True)

    # 检测有没有原有文件（强制哈希校验）
    if file_path.is_file() and _hash_file(file_path) == file_sha1:
        return "skipped"

    for _ in range(MAX_RETRY):
        try:
            _download_file_to_disk(url, temp_file_path)
        except requests.RequestException as e:
            log.warning(f"下载请求出错，重试。\n错误原因: {e}")
            sleep(1)
            continue
        try:
            sha1 = _hash_file(temp_file_path)
        except FileNotFoundError as e:
            log.warning(f"文件 {file_path} 不存在，重新尝试")
            continue
        if not file_sha1 or sha1 == file_sha1:
            temp_file_path.replace(file_path)
            # log.info(f"下载 {file_path} 完成")
            return "success"

        else:
            log.info(f"Hash 校验出错, 重试...")
    return "failed"


def download(targets: list[tuple[str, Path, str, int]]):
    """
    对外提供的多文件下载
    Args:
        targets list[tuple[str, Path, str, int]]: 列表，由任务元组组成的列表，任务元组：(URL, 目标路径, 文件 SHA-1, 文件大小)

    Returns:
        dict[int, int, int, dict[Path, str]]: 结果列表，成功、跳过、失败和 [下载失败的文件路径和原因] 组成的字典
    """
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
        log.info("==" * 20)
        log.info(f"结束：成功 {success} 个，跳过 {skipped} 个，失败 {failed} 个。\n")
        if success + skipped + failed != len(targets):
            log.warning(f"有任务丢失，请尝试重新下载。")
        if failed_dest:
            log.warning(f"失败列表：\n%s", "\n".join(map(str, failed_dest.items())))
    return {"success": success, "skipped": skipped, "failed": failed, "failed_list": failed_dest}


if __name__ == '__main__':
    log.warning(download([("https://github.com/CILXRY/a2cr-Launcher/releases/download/v0.2.0-polish/a2Cr_Launcher.exe",
                           Path(r"C:\Users\Rxx\Desktop\a2Cr_Launcher.exe"), "", 0)]))
