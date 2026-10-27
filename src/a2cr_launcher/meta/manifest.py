from a2cr_launcher.core.http_util import http_get

# Minecraft 版本列表
MOJANG_VERSION_LIST_URL = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'


def get_version_list(version_type: str, limit=0):
    data = http_get(MOJANG_VERSION_LIST_URL).json().get('versions')
    vlist = []
    for version in data:
        if version_type == "all":
            vlist.append(version)
        else:
            if version.get('type') == version_type:
                vlist.append(version)
    if limit:
        return vlist[:limit]

    return vlist


if __name__ == "__main__":
    version_list = get_version_list()
    print(version_list)
