from pyrogram.types import Message

from .base import Monitor


class EmbyhubMonitor(Monitor):
    name = "EmbyHub"
    chat_name = "emby_hub"
    chat_user = "ednovas"
    chat_keyword = r"注册已开放"
    bot_username = "EdHubot"
    notify_create_name = True

    async def on_trigger(self, message: Message, key, reply):
        await self.client.send_message(self.bot_username, f"/create {self.unique_name}")
        self.log.bind(notify=True).info(f'已向Bot发送用户注册申请: "{self.unique_name}", 请检查结果.')
