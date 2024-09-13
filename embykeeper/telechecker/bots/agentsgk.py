from ._base import BotCheckin

__ignore__ = True


class AgentSGKCheckin(BotCheckin):
    name = "007 社工库"
    bot_username = "sgk007_bot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    bot_checked_keywords = ["今日已签到"]
