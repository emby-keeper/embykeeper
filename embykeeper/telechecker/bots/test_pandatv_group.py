from .pandatv_group import PandaTVGroupCheckin

__ignore__ = True


class TestPandaTVGroupCheckin(PandaTVGroupCheckin):
    name = "PandaTV 群组签到测试"
    chat_name = "api_group"

    async def send_checkin(self, retry=False):
        await super().send_checkin(retry=retry)
        self.finished.set()
