import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType
from pyrogram.types import Message
from pyrogram.raw.functions.messages import AcceptUrlAuth
from pyrogram.raw.types import UrlAuthResultAccepted
from faker import Faker

from ._base import BotCheckin


class JMSCheckin(BotCheckin):
    name = "卷毛鼠"
    bot_username = "jmsembybot"
    bot_checked_keywords = "请明天再来签到"

    async def message_handler(self, client, message: Message):
        if message.reply_markup:
            keys = [k for r in message.reply_markup.inline_keyboard for k in r]
            for k in keys:
                if "点我签到" in k.text:
                    r: UrlAuthResultAccepted = await self.client.invoke(
                        AcceptUrlAuth(
                            peer=await self.client.resolve_peer(message.chat.id),
                            msg_id=message.id,
                            button_id=k.login_url.button_id,
                            url=k.login_url.url,
                        )
                    )
                    url = r.url
                    if self.proxy:
                        connector = ProxyConnector(
                            proxy_type=ProxyType[self.proxy["scheme"].upper()],
                            host=self.proxy["hostname"],
                            port=self.proxy["port"],
                            username=self.proxy.get("username", None),
                            password=self.proxy.get("password", None),
                        )
                    else:
                        connector = aiohttp.TCPConnector()
                    for _ in range(1, 3):
                        async with aiohttp.ClientSession(connector=connector) as session:
                            async with session.get(url, headers={"User-Agent": Faker().safari()}) as resp:
                                if resp.status == 200:
                                    return
        return await super().message_handler(client, message)
