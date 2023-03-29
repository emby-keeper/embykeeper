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

    async def start(self):
        me = self.client.me
        if not me.username:
            random_digits = "".join(random.choice(string.digits) for _ in range(4))
        self.bot_create_username = me.username or me.first_name.lower() + me.last_name.lower() + random_digits
        self.log.info(f'当监控到开注时, 将以用户名 "{self.bot_create_username}" 注册, 请[yellow]保证[/]具有一定独特性以避免注册失败.')
        await super().start()

    async def on_trigger(self, message: Message, keys, reply):
        cmd = f"/create {self.bot_create_username}"
        await self.client.send_message(self.bot_username)
        self.log.bind(notify=True).info(f'已向Bot发送用户注册申请: "{cmd}", 请检查结果.')
