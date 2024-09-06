from ._base import BotCheckin


class PandaTVGroupCheckin(BotCheckin):
    name = "PandaTV 群组发言"
    chat_name = "PandaTV_Emby_Bot"
    bot_checkin_cmd = "签到"
    skip = 14

    async def send_checkin(self, retry=False):
        await super().send_checkin(retry=retry)
        self.finished.set()
