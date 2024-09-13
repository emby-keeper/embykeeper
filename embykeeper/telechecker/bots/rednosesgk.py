from ._base import BotCheckin

__ignore__ = True


class RednoseSGKCheckin(BotCheckin):
    name = "红鼻子社工库"
    bot_username = "freesgk123_bot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    bot_checked_keywords = "请勿重复签到"
