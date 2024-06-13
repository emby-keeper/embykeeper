from ._base import BotCheckin

__ignore__ = True


class AISGKCheckin(BotCheckin):
    name = "AI 社工库"
    bot_username = "aishegongkubot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    bot_checked_keywords = "请勿重复签到"
    checked_retries = 6
