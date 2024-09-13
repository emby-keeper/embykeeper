from ._base import BotCheckin

__ignore__ = True


class MoshenSGKCheckin(BotCheckin):
    name = "魔神社工库"
    bot_username = "moshensgk_bot"
    bot_checkin_cmd = "/qd"
    additional_auth = ["prime"]
    max_retries = 6
