import asyncio
import time
from pathlib import Path
from typing import Iterable, Union

from loguru import logger
import aiohttp
import aiofiles
from aiohttp_socks import ProxyConnector, ProxyType

from .utils import to_iterable, humanbytes

logger = logger.bind(scheme="datamanager")


async def get_datas(basedir: Path, names: Union[Iterable[str], str], proxy: dict = None, caller: str = None):
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
        logger.info(f"这是您首次使用{caller or '该功能'}, 将下载所需文件: {', '.join(not_existing)}")

    for name in to_iterable(names):
        if name in existing:
            yield existing[name]
        else:
            try:
                url = f"https://raw.githubusercontent.com/embykeeper/embykeeper-data/main/data/{name}"
                for retries in range(3):
                    if proxy:
                        connector = ProxyConnector(
                            proxy_type=ProxyType[proxy["scheme"].upper()],
                            host=proxy["hostname"],
                            port=proxy["port"],
                        )
                    else:
                        connector = aiohttp.TCPConnector()
                    async with aiohttp.ClientSession(connector=connector) as session:
                        try:
                            async with session.get(url) as resp:
                                if resp.status == 200:
                                    file_size = int(resp.headers.get("Content-Length", 0))
                                    logger.info(f"开始下载: {name} ({humanbytes(file_size)})")
                                    async with aiofiles.open(basedir / name, mode="wb+") as f:
                                        timer = time.time()
                                        length = 0
                                        async for chunk in resp.content.iter_chunked(512):
                                            if time.time() - timer > 3:
                                                timer = time.time()
                                                logger.info(
                                                    f"正在下载: {name} ({humanbytes(length)} / {humanbytes(file_size)})"
                                                )
                                            await f.write(chunk)
                                            length += len(chunk)
                                    logger.info(f"下载完成: {name} ({humanbytes(file_size)})")
                                    yield basedir / name
                                    break
                                else:
                                    logger.warning(f"下载失败: {name} ({resp.status})")
                                    yield None
                                    break
                        except aiohttp.ClientConnectorError as e:
                            (basedir / name).unlink(missing_ok=True)
                            logger.warning(f"下载失败: {name}, 将在 3 秒后重试.")
                            await asyncio.sleep(3)
                            continue
                        except Exception as e:
                            (basedir / name).unlink(missing_ok=True)
                            logger.warning(f"下载失败: {name} ({e})")
                            yield None
                            break
                else:
                    logger.warning(f"下载失败: {name}.")
                    yield None
                    continue
            except KeyboardInterrupt:
                (basedir / name).unlink(missing_ok=True)
                raise


async def get_data(basedir: Path, name: str, proxy: dict = None, caller: str = None):
    async for data in get_datas(basedir, name, proxy, caller):
        return data
