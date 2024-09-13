from ._base import BotCheckin

__ignore__ = True


class KoiSGKCheckin(BotCheckin):
    name = "Koi 社工库"
    bot_username = "KoiSGKbot"
    bot_checkin_cmd = "/qd"
    additional_auth = ["prime"]
    bot_checked_keywords = ["今日已签到"]
