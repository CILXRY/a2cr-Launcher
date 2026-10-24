from a2cr_launcher.core.downloader import http_get

# Minecraft 版本列表
MOJANG_VERSION_LIST_URL = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'


def get_version_list():
    data = http_get(MOJANG_VERSION_LIST_URL).json()

    return data['versions']
