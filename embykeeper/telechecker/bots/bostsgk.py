from ._base import BotCheckin

__ignore__ = True


class BostCheckin(BotCheckin):
    name = "Bost 社工库"
    bot_username = "BOST_SGK_BOT"
    bot_checkin_cmd = "/qd"
    additional_auth = ["prime"]
    bot_use_captcha = False
