from .base import BotCheckin

__ignore__ = True


class DogSGKCheckin(BotCheckin):
    name = "狗狗社工库"
    bot_username = "DogeSGK_bot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
