from ._base import BotCheckin

__ignore__ = True


class TestGroupCheckin(BotCheckin):
    name = "群组签到测试"
    chat_name = "api_group"
    bot_checkin_cmd = "签到"

    async def send_checkin(self, retry=False):
        super().send_checkin(retry)
        self.finished.set()
