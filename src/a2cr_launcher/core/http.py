import requests


def http_get(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response
