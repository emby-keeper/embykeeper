import asyncio
import random
from urllib.parse import parse_qs, urlparse

from pyrogram.types import Message
from pyrogram.raw.functions.messages import RequestWebView
from aiohttp import ClientSession, TCPConnector
from aiohttp_socks import ProxyConnector, ProxyTimeoutError, ProxyError, ProxyType
from faker import Faker

from ..link import Link
from ._base import BotCheckin

__ignore__ = True


class FutureCheckin(BotCheckin):
    name = "未响"
    bot_username = "lotayu_bot"
    bot_checkin_cmd = "/start"

    async def message_handler(self, client, message: Message):
        if message.text and "验证您的身份" in message.text and message.reply_markup:
            keys = [b for r in message.reply_markup.inline_keyboard for k in r]
            for b in keys:
                if "Verify" in b.text and b.web_app:
                    url = b.web_app.url
                    bot_peer = await self.client.resolve_peer(self.bot_username)
                    url_auth = (
                        await self.client.invoke(
                            RequestWebView(peer=bot_peer, bot=bot_peer, platform="ios", url=url)
                        )
                    ).url
                    if not await self.solve_captcha(url_auth):
                        self.log.error("签到失败: 验证码解析失败, 正在重试.")

                    else:
                        await asyncio.sleep(random.uniform(3, 5))
                        self.log.info("已成功验证, 即将重新进行签到流程.")
                    await self.retry()
                    return
            else:
                self.log.warning(f"签到失败: 账户错误.")
                return await self.fail()

        if message.caption and "開始回響" in message.caption and message.reply_markup:
            keys = [k.text for r in message.reply_markup.inline_keyboard for k in r]
            for k in keys:
                if ("签到" in k) or ("簽到" in k):
                    try:
                        await message.click(k)
                    except TimeoutError:
                        pass
                    return
            else:
                self.log.warning(f"签到失败: 账户错误.")
                return await self.fail()
        await super().message_handler(client, message)

    async def solve_captcha(self, url: str):
        token = await Link(self.client).captcha("future_echo")
        if not token:
            return False
        else:
            scheme = urlparse(url)
            params = parse_qs(scheme.query)
            url_submit = scheme._replace(path="/x/api/submit", query="", fragment="").geturl()
            uuid = params.get("id", [None])[0]
            if self.proxy:
                connector = ProxyConnector(
                    proxy_type=ProxyType[self.proxy["scheme"].upper()],
                    host=self.proxy["hostname"],
                    port=self.proxy["port"],
                    username=self.proxy.get("username", None),
                    password=self.proxy.get("password", None),
                )
            else:
                connector = TCPConnector()
            origin = scheme._replace(path="/", query="", fragment="").geturl()
            useragent = Faker().safari()
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": url,
                "Origin": origin,
                "User-Agent": useragent,
            }
            data = {
                "uuid": uuid,
                "cf-turnstile-response": token,
            }
            try:
                async with ClientSession(connector=connector) as session:
                    async with session.post(url_submit, headers=headers, data=data) as resp:
                        result = await resp.text()
                        if "完成" in result:
                            return True
            except (ProxyTimeoutError, ProxyError, OSError):
                return False
