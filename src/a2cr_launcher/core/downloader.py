import requests


def http_get(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as err:
        print("HTTP 请求失败", err)
