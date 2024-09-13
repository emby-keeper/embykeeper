from ._base import BotCheckin

__ignore__ = True


class BaiduSGKCheckin(BotCheckin):
    name = "度娘社工库"
    bot_username = "baidusell_bot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    bot_checked_keywords = ["今日已签到"]
