from a2cr_launcher.core.http_util import http_get

# Minecraft 版本列表
MOJANG_VERSION_LIST_URL = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'


def get_version_list(version_type: str, limit=0):
    data = http_get(MOJANG_VERSION_LIST_URL).json().get('versions')
    versions_list = []
    for version in data:
        if version_type == "all":
            versions_list.append(version)
        else:
            if version.get('type') == version_type:
                versions_list.append(version)
    if limit:
        return versions_list[:limit]

    return versions_list


def find_version(version_id: str):
    version_list = get_version_list("all", 0)
    for version in version_list:
        if version.get('id') == version_id:
            return version
    raise ValueError(f"Version {version_id} not found")


if __name__ == "__main__":
    pass
