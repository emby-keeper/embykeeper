from pyrogram.types import Message

from ._base import Monitor


class ViperMonitor(Monitor):
    name = "Viper"
    chat_keyword = r"register-[-\w]{36}"
    bot_username = "viper_emby_bot"
    chat_name = "Viper_Emby_Chat"
    notify_create_name = True
    allow_edit = False

    async def on_trigger(self, message: Message, key, reply):
        await self.client.send_message(self.bot_username, f"/invite {key}")
        await self.client.send_message(self.bot_username, self.unique_name)
        self.log.bind(notify=True).info(f'已向Bot发送邀请码: "{key}", 请查看.')
