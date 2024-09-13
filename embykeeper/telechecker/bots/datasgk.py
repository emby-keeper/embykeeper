from ._base import BotCheckin


class DataSGKCheckin(BotCheckin):
    name = "数据社工库"
    bot_username = "DataSGK_bot"
    bot_checkin_cmd = "/signin"
    additional_auth = ["prime"]
    bot_checked_keywords = "请勿重复签到"
