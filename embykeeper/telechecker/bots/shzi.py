from ._base import BotCheckin

__ignore__ = True


class ShziCheckin(BotCheckin):
    name = "Shzi"
    bot_username = "aishuazibot"
    bot_checkin_cmd = "📅 签到"
    additional_auth = ["prime"]
    max_retries = 6
