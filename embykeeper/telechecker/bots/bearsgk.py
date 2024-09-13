from ._base import BotCheckin

__ignore__ = True


class BearSGKCheckin(BotCheckin):
    name = "小熊社工库"
    bot_username = "BearSGK_bot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    bot_checked_keywords = "请勿重复签到"
