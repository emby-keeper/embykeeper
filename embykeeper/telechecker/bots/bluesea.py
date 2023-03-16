from pyrogram.types import Message

from .base import BotCheckin


class BlueseaCheckin(BotCheckin):
    name = "Bluesea"
    bot_username = "blueseamusic_bot"
    bot_captcha_len = 4
