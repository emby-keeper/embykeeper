from ._base import BotCheckin

__ignore__ = True


class DingdangSGKCheckin(BotCheckin):
    name = "叮当猫社工库"
    bot_username = "DingDangCats_Bot"
    bot_checkin_cmd = "/qd"
    additional_auth = ["prime"]
