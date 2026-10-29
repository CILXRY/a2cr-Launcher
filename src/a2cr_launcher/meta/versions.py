from a2cr_launcher.core.http_util import http_get
from a2cr_launcher.meta.manifest import find_version

def get_version_meta(version_id: str) -> dict:
    version_meta_url = find_version(version_id).get("url")
    meta = http_get(version_meta_url).json()
    return meta


if '__main__' == __name__:
    print(get_version_meta('26.2'))
