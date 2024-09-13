from ._base import BotCheckin

__ignore__ = True


class QingfengSGKCheckin(BotCheckin):
    name = "清风社工库"
    bot_username = "Weifeng007_bot"
    bot_checkin_cmd = "/qd"
    additional_auth = ["prime"]
    bot_checked_keywords = "您今天已经签到过了"
