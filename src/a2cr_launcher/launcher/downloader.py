import json

import aiohttp
import asyncio

# Minecraft 版本列表
MOJANG_VERSION_LIST_URL = 'https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'
semaphore = asyncio.Semaphore(8)


async def download_file(session, url):
    async with session.get(url) as resp:
        return await resp


async def download_multiple_files(session, urls: list):
    """
    下载多个文件的时候调用
    """
    tasks = [download_file(session, url) for url in urls]
    results = await asyncio.gather(*tasks)


async def get_version_list():
    async with aiohttp.ClientSession() as session:
        data = await download_file(session, MOJANG_VERSION_LIST_URL)
        print(data)


asyncio.run(get_version_list())
