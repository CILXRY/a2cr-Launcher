import hashlib
from pathlib import Path
from time import sleep

import requests

max_tries = 3
target_dir = r"./aL"
# 下载分片大小
chunk_size = 1024 * 1024


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
    req = requests.get(url, stream=True)
    # 进度初始化
    downloaded = 0
    total_size = int(req.headers.get('content-length', 0))

    req.raise_for_status()

    # 分片下载文件
    with open(file_path, 'wb') as f:
        # 用 iter_content 来给文件分片, 分到各个 chunk 里
        # 不要把 for 循环和 with 的顺序写反, 否则到最后就只剩最后的那个 chunk的内容了
        for chunk in req.iter_content(chunk_size):
            # 写入
            f.write(chunk)
            downloaded += len(chunk)
            print(f"当前下载进度: {downloaded / 1048576:.2f}/{total_size / 1048576:.2f} MB", flush=True)


def download_file(url, file_hash=""):
    """
    对外所用的文件下载, 集成了 文件哈希,错误重试,创建文件 的整体函数
    :param file_hash: 文件哈希
    :param url: 文件地址
    :return: 正常下载返回 0, 下载出错(最大尝试之后都出错)返回 1
    """

    # 文件路径和默认哈希
    file_path = Path(target_dir, url.split('/')[-1])
    temp_file_path = file_path.with_suffix(file_path.suffix + ".part")
    if not file_hash:
        file_hash = url.split('/')[-2]

    # 检查目标文件夹在不在
    is_target_dir_exist = Path.exists(target_dir)
    if not is_target_dir_exist:
        _create_dir(target_dir)

    print(f"准备下载 {file_path}")
    for i in range(max_tries):
        try:
            _download_file_to_disk(url, temp_file_path)
        except requests.RequestException as e:
            sleep(1)
        sha1 = _hash_file(temp_file_path)
        if sha1 == file_hash:
            Path.replace(temp_file_path, file_path)
            print(f"下载 {file_path} 完成")
            return 0
        else:
            print(f"Hash 校验出错, 重试...")
    return 1


if __name__ == '__main__':
    _create_dir(target_dir)
    download_file(
        "https://piston-data.mojang.com/v1/objects/0c3ec587af28e5a785c0b4a7b8a30f9a8f78f838/client.jar"
    )
