import asyncio
import time
from pathlib import Path
from typing import Iterable, Union

import aiofiles
import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
from cachetools import TTLCache
from loguru import logger

from .utils import format_byte_human, no_waiting, show_exception, to_iterable

logger = logger.bind(scheme="datamanager")

cdn_urls = [
    "https://raw.githubusercontent.com/embykeeper/embykeeper-data/main",
    "https://raw.gitmirror.com/embykeeper/embykeeper-data/main",
    "https://cdn.jsdelivr.net/gh/embykeeper/embykeeper-data",
]

versions = TTLCache(maxsize=128, ttl=600)
lock = asyncio.Lock()


async def refresh_version(connector):
    async with no_waiting(lock):
        for data_url in cdn_urls:
            url = f"{data_url}/version"
            async with aiohttp.ClientSession(connector=connector) as session:
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            result = await resp.text()
                            for l in result.splitlines():
                                if l:
                                    a, b = l.split("=")
                                    versions[a.strip()] = b.strip()
                            break
                        else:
                            logger.warning(f"资源文件版本信息获取失败 ({resp.status})")
                            return False
                except aiohttp.ClientConnectorError as e:
                    continue
                except Exception as e:
                    logger.warning(f"资源文件版本信息获取失败 ({e})")
                    show_exception(e)
                    return False
        else:
            logger.warning(f"资源文件版本信息获取失败.")
            return False


async def get_datas(basedir: Path, names: Union[Iterable[str], str], proxy: dict = None, caller: str = None):
    """
    获取额外数据.
    参数:
        basedir: 文件存储默认位置
        names: 要下载的路径列表
        proxy: 代理配置
        caller: 请求下载的模块名, 用于消息提示
    """
    basedir.mkdir(parents=True, exist_ok=True)

    existing = {}
    not_existing = []
    for name in to_iterable(names):
        if (basedir / name).is_file():
            logger.debug(f'检测到请求的本地文件: "{name}".')
            existing[name] = basedir / name
        else:
            not_existing.append(name)

    if not_existing:
        logger.info(f"{caller or '该功能'} 正在下载或更新资源文件: {', '.join(not_existing)}")

    for name in to_iterable(names):
        version_matching = False
        while True:
            if (basedir / name).is_file():
                yield basedir / name
            else:
                try:
                    for data_url in cdn_urls:
                        url = f"{data_url}/data/{name}"
                        logger.debug(f"正在尝试 URL: {url}")
                        if proxy:
                            connector = ProxyConnector(
                                proxy_type=ProxyType[proxy["scheme"].upper()],
                                host=proxy["hostname"],
                                port=proxy["port"],
                                username=proxy.get("username", None),
                                password=proxy.get("password", None),
                            )
                        else:
                            connector = aiohttp.TCPConnector()
                        async with aiohttp.ClientSession(connector=connector) as session:
                            try:
                                async with session.get(url) as resp:
                                    if resp.status == 200:
                                        file_size = int(resp.headers.get("Content-Length", 0))
                                        logger.info(f"开始下载: {name} ({format_byte_human(file_size)})")
                                        async with aiofiles.open(basedir / name, mode="wb+") as f:
                                            timer = time.time()
                                            length = 0
                                            async for chunk in resp.content.iter_chunked(512):
                                                if time.time() - timer > 3:
                                                    timer = time.time()
                                                    logger.info(
                                                        f"正在下载: {name} ({format_byte_human(length)} / {format_byte_human(file_size)})"
                                                    )
                                                await f.write(chunk)
                                                length += len(chunk)
                                        logger.info(f"下载完成: {name} ({format_byte_human(file_size)})")
                                        yield basedir / name
                                        break
                                    elif resp.status in (403, 404) and not version_matching:
                                        await refresh_version(connector=connector)
                                        if name in versions:
                                            logger.debug(f'解析版本 "{name}" -> "{versions[name]}"')
                                            name = versions[name]
                                            version_matching = True
                                            break
                                        else:
                                            logger.warning(f"下载失败: {name} ({resp.status})")
                                            yield None
                                            break
                                    else:
                                        logger.warning(f"下载失败: {name} ({resp.status})")
                                        yield None
                                        break
                            except aiohttp.ClientConnectorError as e:
                                (basedir / name).unlink(missing_ok=True)
                                continue
                            except Exception as e:
                                (basedir / name).unlink(missing_ok=True)
                                logger.warning(f"下载失败: {name} ({e})")
                                show_exception(e)
                                yield None
                                break
                    else:
                        logger.warning(f"下载失败: {name}.")
                        yield None
                        continue
                except KeyboardInterrupt:
                    (basedir / name).unlink(missing_ok=True)
                    raise
            if not version_matching:
                break


async def get_data(basedir: Path, name: str, proxy: dict = None, caller: str = None):
    async for data in get_datas(basedir, name, proxy, caller):
        return data
