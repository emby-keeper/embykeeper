import asyncio
import contextlib
from urllib.parse import urlparse

from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector, ProxyType
from pyrogram.raw.functions.messages import RequestWebView
from pyrogram.raw.functions.users import GetFullUser

from ...utils import remove_prefix
from .base import BaseBotCheckin


class NebulaCheckin(BaseBotCheckin):
    name = "Nebula"
    bot_username = "Nebula_Account_bot"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._retries = 0
        proxy = self.client.proxy
        self.connector = (
            ProxyConnector(
                proxy_type=ProxyType[proxy["scheme"].upper()],
                host=proxy["hostname"],
                port=proxy["port"],
            )
            if proxy
            else None
        )

    async def retry(self):
        self._retries += 1
        if self._retries <= self.retries:
            await asyncio.sleep(5)
            await self.checkin()
        else:
            self.log.error("超过最大重试次数.")
            self.finished.set()

    async def checkin(self):
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._checkin(), self.timeout)
        if not self.finished.is_set():
            self.log.warning("无法在时限内完成签到.")
            return False
        else:
            return self._retries <= self.retries

    async def _checkin(self):
        bot = await self.client.resolve_peer(self.bot_username)
        user_full = await self.client.invoke(GetFullUser(id=bot))
        url = user_full.full_user.bot_info.menu_button.url
        url_auth = (
            await self.client.invoke(
                RequestWebView(peer=bot, bot=bot, platform="ios", url=url)
            )
        ).url
        scheme = urlparse(url_auth)
        data = remove_prefix(scheme.fragment, "tgWebAppData=")
        user_checkin_url = scheme._replace(
            path="/api/userCheckIn", query=f"data={data}"
        ).geturl()
        async with ClientSession(connector=self.connector) as session:
            async with session.get(user_checkin_url) as resp:
                check_results = await resp.json()
            message = check_results["message"]
            if "失败" in message:
                self.log.info("签到失败, 正在重试.")
                await self.retry()
            if "重复" in message:
                self.log.info("今日已经签到过了.")
                self.finished.set()
            elif "成功" in message:
                self.log.info(
                    f"[yellow]签到成功[/]: + {check_results['get_credit']} 分 -> {check_results['credit']} 分."
                )
                self.finished.set()
            else:
                self.log.warning(f"接收到异常返回信息: {message}")
