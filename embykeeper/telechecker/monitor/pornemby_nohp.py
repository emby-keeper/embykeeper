from datetime import datetime

from pyrogram.types import Message
from pyrogram.enums import MessageEntityType

from ..lock import pornemby_nohp

from .base import Monitor

class PornembyNoHPMonitor(Monitor):
    name = "Pornemby 血量耗尽停止发言"
    chat_user = "PronembyTGBot2_bot"
    chat_name = "Pornemby"
    chat_keyword = "(.*)血量已耗尽。"

    async def on_trigger(self, message: Message, key, reply):
        for me in message.entities:
            if me.type == MessageEntityType.TEXT_MENTION:
                if me.user.id == self.client.me.id:
                    pornemby_nohp[self.client.me.id] = datetime.today().date()
