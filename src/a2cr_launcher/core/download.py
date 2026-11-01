"""文件下载：断点续传、失败重试、哈希校验与并发下载。"""

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from random import uniform
from time import sleep

import requests
from requests.adapters import HTTPAdapter
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

# 单个文件最多尝试次数
MAX_RETRY = 4
# 同时下载的文件数
MAX_WORKERS = 8
# 下载分片大小
CHUNK_SIZE = 1024 * 1024
# (连接超时, 读取超时)：读取超时不能太短，否则大文件在慢速网络下会被误判为失败
TIMEOUT = (10, 60)
# 第一轮结束后，对失败的文件再补下的轮数
FAILED_RETRY_PASSES = 2
# 一个都没下载成功时，连续失败多少个就提前中止（多半是断网/代理挂了）
ABORT_AFTER_FAILURES = 12

USER_AGENT = "a2cr-launcher/0.2 (+https://github.com/CILXRY/a2cr-Launcher)"

_thread_local = threading.local()
_error_lock = threading.Lock()
_last_errors: dict[str, str] = {}


def get_session() -> requests.Session:
    """每个线程复用一个 Session，复用连接，避免为每个文件重新做 TLS 握手。"""
    session: requests.Session | None = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        # 禁止压缩，保证本地分片的大小和服务器上的字节偏移一致，断点续传才不会错位
        session.headers["Accept-Encoding"] = "identity"
        adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS, max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _thread_local.session = session
    return session


def _record_error(dest: Path, reason: str) -> None:
    with _error_lock:
        _last_errors[str(dest)] = reason


def _take_error(dest: Path) -> str:
    with _error_lock:
        return _last_errors.pop(str(dest), "未知错误")


def _hash_file(file_path) -> str:
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


def _download_file_to_disk(url, part_path, expected_size=0):
    """
    把 url 下载到 part_path。如果 part_path 已有内容，会尝试用 Range 续传。

    Args:
        url (str): 文件 URL
        part_path (Path): 分片文件路径
        expected_size (int): 期望的文件大小，大于 0 时用来丢弃异常的旧分片

    Returns:
        None
    """
    part_path = Path(part_path)
    part_path.parent.mkdir(parents=True, exist_ok=True)

    downloaded = part_path.stat().st_size if part_path.is_file() else 0
    if expected_size and downloaded > expected_size:
        # 旧分片比目标文件还大，一定是错的，删掉重新下
        part_path.unlink()
        downloaded = 0

    headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}

    response = get_session().get(url, stream=True, timeout=TIMEOUT, headers=headers)
    try:
        if downloaded and response.status_code == 416:
            # 服务器认为已经下完了，交给哈希校验判断
            return
        response.raise_for_status()
        # 只有服务器真的返回 206 时才续写，否则会把整个文件重新写一遍
        mode = "ab" if downloaded and response.status_code == 206 else "wb"
        with open(part_path, mode) as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
    finally:
        response.close()


def download_file(url, dest, file_sha1="", file_size=0, *, verbose=True):
    """
    对外所用的文件下载, 集成了 文件哈希,错误重试,创建文件 的整体函数
    Args:
        url (str): 文件地址
        dest (Path): 文件保存位置
        file_sha1 (str): 文件哈希，为空表示不校验
        file_size (int): 文件大小，大于 0 时用于续传校验
        verbose (bool): 是否打印每次重试的原因

    Returns:
        str: 结果："success", "failed", "skipped" 其中之一

    """
    file_path = Path(dest)
    part_path = file_path.with_name(file_path.name + ".part")

    # 创建目标文件夹
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 检测有没有原有文件（强制哈希校验）
    if file_path.is_file():
        if not file_sha1 or _hash_file(file_path) == file_sha1:
            return "skipped"
        # 文件损坏，删掉重下，避免一直拿坏文件当缓存
        file_path.unlink()

    error = "未知错误"
    for attempt in range(MAX_RETRY):
        try:
            _download_file_to_disk(url, part_path, file_size)
            sha1 = _hash_file(part_path)
            if not file_sha1 or sha1 == file_sha1:
                part_path.replace(file_path)
                with _error_lock:
                    _last_errors.pop(str(file_path), None)
                return "success"
            part_path.unlink(missing_ok=True)
            error = f"SHA-1 校验失败（得到 {sha1}，期望 {file_sha1}）"
        except requests.RequestException as exc:
            error = f"{type(exc).__name__}: {exc}"
        except FileNotFoundError:
            error = "下载过程中分片文件消失"

        if verbose:
            print(f"[重试 {attempt + 1}/{MAX_RETRY}] {file_path.name} 失败：{error}")
        if attempt + 1 < MAX_RETRY:
            # 退避 + 抖动，避免整批请求同时重试把服务器/代理打垮
            sleep(min(0.5 * 2 ** attempt, 4.0) + uniform(0, 0.3))

    _record_error(file_path, error)
    return "failed"


def _unique_targets(targets):
    """同一个目标文件可能出现在多个列表里，去重，避免多线程同时写同一个 .part"""
    seen, unique = set(), []
    for target in targets:
        dest = Path(target[1])
        if dest in seen:
            continue
        seen.add(dest)
        unique.append((target[0], dest, target[2], target[3] or 0))
    return unique


def _build_progress(total_bytes, total_files, show_progress):
    if total_bytes:
        columns = (
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        )
        return Progress(*columns, disable=not show_progress), total_bytes
    columns = (
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
    )
    return Progress(*columns, disable=not show_progress), total_files


def download(targets, *, show_progress=True, description="下载文件"):
    """
    批量下载。

    Args:
        targets (list[tuple[str, Path, str, int]]): (下载 URL, 保存路径, sha1, 大小)
        show_progress (bool): 是否显示进度条
        description (str): 进度条标题

    Returns:
        bool: 是否全部成功
    """
    targets = _unique_targets(targets)
    if not targets:
        return True

    total_bytes = sum(target[3] for target in targets)
    progress, total = _build_progress(total_bytes, len(targets), show_progress)

    success = skipped = 0
    pass_failures: dict[Path, str] = {}
    pending = list(targets)
    aborted = False

    with progress:
        task = progress.add_task(description, total=total, visible=show_progress)
        for pass_index in range(FAILED_RETRY_PASSES + 1):
            if not pending:
                break
            pass_failures = {}
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(download_file, url, dest, sha1, size, verbose=False): dest
                    for url, dest, sha1, size in pending
                }
                for future in as_completed(futures):
                    dest = futures[future]
                    try:
                        result = future.result()
                        reason = ""
                    except Exception as exc:  # 线程里未预料的异常也不能让整个安装崩掉
                        result, reason = "failed", f"{type(exc).__name__}: {exc}"

                    if result == "success":
                        success += 1
                        progress.advance(task, dest.stat().st_size if total_bytes else 1)
                    elif result == "skipped":
                        skipped += 1
                        progress.advance(task, dest.stat().st_size if total_bytes else 1)
                    else:
                        pass_failures[dest] = reason or _take_error(dest)

                    # 一个都没成功的时候不硬撑：否则断网时会把几千个文件挨个重试一遍
                    if success + skipped == 0 and len(pass_failures) >= ABORT_AFTER_FAILURES:
                        aborted = True
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                if aborted:
                    break

            pending = [(url, dest, sha1, size) for url, dest, sha1, size in targets if dest in pass_failures]
            if not pending:
                break
            if pass_index < FAILED_RETRY_PASSES:
                sleep(1.5 * (pass_index + 1))

        progress.update(task, description=f"{description}（结束）")

    failed = pass_failures if (pending or aborted) else {}
    print("==" * 20)
    if aborted:
        print("连续多个文件都下载失败，已提前中止。请检查网络或者代理设置后重新运行。")
    print(f"结束：成功 {success} 个，跳过 {skipped} 个，失败 {len(failed)} 个。\n")
    if failed:
        print("失败列表：")
        for dest, reason in list(failed.items())[:10]:
            print(f"  {dest}\n    {reason}")
        if len(failed) > 10:
            print(f"  ... 还有 {len(failed) - 10} 个")
        print("已下载的文件会被跳过，重新运行本命令即可继续补下。")
        return False
    return True


if __name__ == '__main__':
    from a2cr_launcher.meta.versions import get_version_meta
    from a2cr_launcher.core.paths import ASSETS_DIR
    from a2cr_launcher.meta.assets import build_asset_downloads, fetch_asset_index

    meta = get_version_meta('26.2')
    asset_index: tuple = (meta["assetIndex"].get("url", ""),
                          meta["assetIndex"].get("sha1", ""))
    assets = fetch_asset_index(asset_index[0], Path(ASSETS_DIR, f'indexes/{asset_index[0].split("/")[-1]}'),
                               asset_index[1])
    download(build_asset_downloads(assets.get('objects', {}), ASSETS_DIR))
