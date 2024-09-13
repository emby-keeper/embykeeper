from ._base import BotCheckin

__ignore__ = True


class TianmaoSGKCheckin(BotCheckin):
    name = "天猫社工库"
    bot_username = "UISGKbot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    checked_retries = 6
