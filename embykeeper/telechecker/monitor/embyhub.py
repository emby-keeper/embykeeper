import random
import string

from pyrogram.types import Message

from .base import Monitor


class EmbyhubMonitor(Monitor):
    name = "EmbyHub"
    chat_name = "emby_hub"
    chat_user = "ednovas"
    chat_keyword = r"注册已开放"
    bot_username = "EdHubot"
    notify_create_name = True

    async def on_trigger(self, message: Message, keys, reply):
        cmd = f"/create {self.unique_name}"
        await self.client.send_message(self.bot_username)
        self.log.bind(notify=True).info(f'已向Bot发送用户注册申请: "{cmd}", 请检查结果.')
