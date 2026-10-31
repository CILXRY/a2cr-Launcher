from time import sleep

import requests

from a2cr_launcher.core.download import MAX_RETRY


def http_get(url):
    for _ in range(MAX_RETRY):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            sleep(1)
            continue
        return response
    raise requests.RequestException
