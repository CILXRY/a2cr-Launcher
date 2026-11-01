import json
from pathlib import Path

import requests

from a2cr_launcher.core.http_util import http_get
from a2cr_launcher.core.paths import VERSIONS_DIR

# Minecraft 版本列表
MOJANG_VERSION_LIST_URL = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'


def get_version_manifest(version_type: str, limit=0):
    # 首先先从本地的文件读取
    local_data_path = Path(VERSIONS_DIR, MOJANG_VERSION_LIST_URL.strip().split("/")[-1])
    local_data, local_latest = None, None
    try:
        with open(local_data_path, 'r+') as f:
            local_data = json.load(f)
            local_latest = local_data.get("latest", "") if isinstance(local_data, dict) else None
    except FileNotFoundError:
        local_data = dict()

    # 这里的意图是在远程不可用的时候使用本地的
    try:
        remote_data = http_get(MOJANG_VERSION_LIST_URL).json()
    except requests.exceptions.RequestException:
        remote_data = None

    if isinstance(remote_data, dict):
        # 如果远程是可用的
        data = remote_data.get("versions")
        if local_latest != remote_data.get("latest"):
            # 根据本地和远程的最新版本来判断文件的时效性
            with open(local_data_path, 'w') as f:
                json.dump(remote_data, f)
    elif remote_data is None and local_data:
        # 如果远程是不可用的
        data = local_data.get("versions")
    else:
        # 远程和本地都不可用的情况
        raise ValueError(f"Version not found")

    # 列版本列表
    versions_list = []
    if isinstance(data, list):
        for version in data:
            if version_type == "all" or version.get('type') == version_type:
                versions_list.append(version)
        if limit:
            return versions_list[:limit]

    return versions_list


def find_version(version_id: str):
    version_list = get_version_manifest("all", 0)
    for version in version_list:
        if version.get('id') == version_id:
            return version
    raise ValueError(f"Version {version_id} not found")
