from ._base import BotCheckin

__ignore__ = True


class MasterSGKCheckin(BotCheckin):
    name = "Master 社工库"
    bot_username = "BaKaMasterBot"
    bot_checkin_cmd = "/sign"
    additional_auth = ["prime"]
    checked_retries = 6
