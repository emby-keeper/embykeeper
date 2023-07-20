import asyncio
from urllib.parse import parse_qs, urlencode, urlparse

from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector
from pyrogram.raw.functions.messages import RequestWebView
from pyrogram.raw.functions.users import GetFullUser
from fake_useragent import UserAgent

from ...utils import remove_prefix
from ..link import Link
from .base import BaseBotCheckin

__ignore__ = True


class NebulaCheckin(BaseBotCheckin):
    name = "Nebula"
    bot_username = "Nebula_Account_bot"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.failed = False
        self.timeout *= 3

    async def fail(self):
        self.failed = True
        self.finished.set()

    async def start(self):
        try:
            try:
                await asyncio.wait_for(self._checkin(), self.timeout)
            except asyncio.TimeoutError:
                pass
        except OSError as e:
            self.log.info(f'发生错误: "{e}".')
            return False
        if not self.finished.is_set():
            self.log.warning("无法在时限内完成签到.")
            return False
        else:
            return not self.failed

    async def _checkin(self):
        bot = await self.client.get_users(self.bot_username)
        self.log.info(f"开始执行签到: [green]{bot.name}[/] [gray50](@{bot.username})[/].")
        bot_peer = await self.client.resolve_peer(self.bot_username)
        user_full = await self.client.invoke(GetFullUser(id=bot_peer))
        url = user_full.full_user.bot_info.menu_button.url
        url_auth = (
            await self.client.invoke(RequestWebView(peer=bot_peer, bot=bot_peer, platform="ios", url=url))
        ).url
        scheme = urlparse(url_auth)
        data = remove_prefix(scheme.fragment, "tgWebAppData=")
        url_base = scheme._replace(path="/api/proxy/userCheckIn", query=f"data={data}", fragment="").geturl()
        scheme = urlparse(url_base)
        query = parse_qs(scheme.query, keep_blank_values=True)
        query = {k: v for k, v in query.items() if not k.startswith("tgWebApp")}
        token, proxy, useragent = await Link(self.client).captcha()
        if (not token) or (not proxy):
            self.log.warning("签到失败: 无法获得验证码.")
            return await self.fail()
        if not useragent:
            useragent = UserAgent(browsers=["edge"]).random
        query["token"] = token
        url_checkin = scheme._replace(query=urlencode(query, True)).geturl()
        connector = ProxyConnector.from_url(proxy)
        async with ClientSession(connector=connector) as session:
            async with session.get(url_checkin, headers={"User-Agent": useragent}) as resp:
                results = await resp.json()
            message = results["message"]
            if any(s in message for s in ("未找到用户", "权限错误")):
                self.log.info("签到失败: 账户错误.")
                await self.fail()
            if "失败" in message:
                self.log.info("签到失败.")
                await self.fail()
            if "重复" in message:
                self.log.info("今日已经签到过了.")
                self.finished.set()
            elif "成功" in message:
                self.log.info(f"[yellow]签到成功[/]: + {results['get_credit']} 分 -> {results['credit']} 分.")
                self.finished.set()
            else:
                self.log.warning(f"接收到异常返回信息: {message}")
