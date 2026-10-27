from a2cr_launcher.core.http_util import http_get
from a2cr_launcher.meta.manifest import find_version


def get_version_meta(version_id: str) -> dict:
    try:
        version_meta_url = find_version(version_id).get("url")
    except ValueError:
        raise ValueError(f"版本不存在: {version_id}")

    meta = http_get(version_meta_url).json()

    main_class = meta.get('mainClass')
    asset_index_id = meta.get('assetIndex').get('id')
    asset_index_url = meta.get('assetIndex').get('url')
    libraries_len = len(meta.get("libraries"))
    name_of_first_library = meta.get("libraries")[0].get("name")
    downloads_client_url = meta.get('downloads').get('client').get('url')
    downloads_client_sha1 = meta.get('downloads').get('client').get('sha1')
    java_version = meta.get('javaVersion').get("majorVersion")

    return {"main_class": main_class, "asset_index_id": asset_index_id, "asset_index_url": asset_index_url,
            "libraries_len": libraries_len, "name_of_first_library": name_of_first_library,
            "downloads_client_url": downloads_client_url, "downloads_client_sha1": downloads_client_sha1,
            "java_version": java_version}


if '__main__' == __name__:
    print(get_version_meta('26.2'))
