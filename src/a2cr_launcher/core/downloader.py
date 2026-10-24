import requests

def download_file(url):
    f = requests.get(url, timeout=10)
    return f


