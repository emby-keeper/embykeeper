from pyrogram.types import Message

from .base import Monitor


class ViperMonitor(Monitor):
    name = "Viper"
    chat_keyword = r"register-[-\w]{36}"
    bot_username = "viper_emby_bot"
    notify_create_name = True

    async def on_trigger(self, message: Message, keys, reply):
        await self.client.send_message(self.bot_username, f"/invite {keys[0]}")
        await self.client.send_message(self.bot_username, self.unique_name)
        self.log.bind(notify=True).info(f'已向Bot发送邀请码: "{keys[0]}", 请查看.')
