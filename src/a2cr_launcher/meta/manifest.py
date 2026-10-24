import json

from a2cr_launcher.core.downloader import download_file

# Minecraft 版本列表
MOJANG_VERSION_LIST_URL = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'


def get_version_list():
    data = download_file(MOJANG_VERSION_LIST_URL).json()

    version_count = len(data['versions'])
    return version_count, data['versions']

print(get_version_list())