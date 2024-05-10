from .base import BotCheckin

__ignore__ = True


class Data007Checkin(BotCheckin):
    name = "Data 007 社工库"
    bot_username = "DATA_007bot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
