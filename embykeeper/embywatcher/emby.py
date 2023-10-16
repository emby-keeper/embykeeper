import asyncio
import random

import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
from embypy.emby import Emby as _Emby
from embypy.objects import EmbyObject
from embypy.utils.asyncio import async_func
from embypy.utils.connector import Connector as _Connector
from fake_useragent import UserAgent
from loguru import logger

from .. import __version__

logger = logger.bind(scheme="embywatcher")


class Connector(_Connector):
    """重写的 Emby 连接器, 以支持代理."""

    def __init__(self, url, proxy=None, **kargs):
        super().__init__(url, **kargs)
        self.proxy = proxy

    async def _get_session(self):
        loop = asyncio.get_running_loop()
        loop_id = hash(loop)
        auth_header = (
            f'MediaBrowser Client="Emby",Device="Emby",DeviceId="{self.device_id}",Version="{__version__}"'
        )
        if self.token:
            auth_header += f',Token="{self.token}"'
        headers = {
            "User-Agent": UserAgent().random,
            "Authorization": auth_header,
            "X-Emby-Authorization": auth_header,
        }
        if self.token:
            headers.update({"X-MediaBrowser-Token": self.token})

        async with await self._get_session_lock():
            session = self._sessions.get(loop_id)
            if not session:
                if self.proxy:
                    connector = ProxyConnector(
                        proxy_type=ProxyType[self.proxy["scheme"].upper()],
                        host=self.proxy["hostname"],
                        port=self.proxy["port"],
                        ssl_context=self.ssl,
                    )
                else:
                    connector = aiohttp.TCPConnector(ssl_context=self.ssl)
                session = aiohttp.ClientSession(headers=headers, connector=connector)
                self._sessions[loop_id] = session
                self._session_uses[loop_id] = 1
            else:
                self._session_uses[loop_id] += 1
            return session

    @async_func
    async def _req(self, method, path, params={}, **query):
        await self.login_if_needed()
        for i in range(self.tries):
            url = self.get_url(path, **query)
            try:
                resp = await method(url, timeout=self.timeout, **params)
            except (aiohttp.ClientConnectionError, OSError, asyncio.TimeoutError) as e:
                logger.debug(f'连接 "{url}" 失败: {e.__class__.__name__}: {e}')
            else:
                if self.attempt_login and resp.status == 401:
                    raise aiohttp.ClientConnectionError("用户名密码错误")
                if await self._process_resp(resp):
                    return resp
            await asyncio.sleep(random.random() * i + 0.2)
        raise aiohttp.ClientConnectionError("无法连接到服务器.")

    @async_func
    async def get_stream_noreturn(self, path, **query):
        try:
            session = await self._get_session()
            async with await self._req(session.get, path, **query) as resp:
                async for _ in resp.content.iter_any():
                    await asyncio.sleep(5)
        finally:
            await self._end_session()


class Emby(_Emby):
    def __init__(self, url, **kargs):
        """重写的 Emby 类, 以支持代理."""
        connector = Connector(url, **kargs)
        EmbyObject.__init__(self, {"ItemId": "", "Name": ""}, connector)
        self._partial_cache = {}
        self._cache_lock = asyncio.Condition()

    @async_func
    async def get_items(
        self,
        types,
        path="/Users/{UserId}/Items",
        fields=None,
        limit=10,
        sort="SortName",
        ascending=True,
        **kw,
    ):
        if not fields:
            fields = ["Path", "ParentId", "Overview", "PremiereDate", "DateCreated"]
        resp = await self.connector.getJson(
            path,
            remote=False,
            format="json",
            recursive="true",
            includeItemTypes=",".join(types),
            fields=fields,
            sortBy=sort,
            sortOrder="Ascending" if ascending else "Descending",
            limit=limit,
            **kw,
        )
        return await self.process(resp)
