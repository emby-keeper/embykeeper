from ._base import BotCheckin

__ignore__ = True


class FanhuaSGKCheckin(BotCheckin):
    name = "繁花社工库"
    bot_username = "FanHuaSGK_bot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    bot_checked_keywords = ["今日已签到"]
