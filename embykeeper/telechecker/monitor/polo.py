import asyncio
from pyrogram.types import Message

from .base import Monitor

__ignore__ = True


class PoloMonitor(Monitor):
    name = "Polo"
    chat_name = "poloemby"
    chat_keyword = r"普通可用的注册码:\n([\s\S]*)"
    bot_username = "polo_emby_bot"
    notify_create_name = True
    allow_edit = False

    async def on_trigger(self, message: Message, key, reply):
        for code in key.split("\n"):
            await self.client.send_message(self.bot_username, f"/invite {code}")
            await self.client.send_message(self.bot_username, self.unique_name)
            await asyncio.sleep(0.5)
            self.log.bind(notify=True).info(f'已向Bot发送邀请码: "{code}", 请查看.')
