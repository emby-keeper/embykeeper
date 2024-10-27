import random
from ...utils import to_iterable
from ._base import BotCheckin

__ignore__ = True


class AkileGroupCheckin(BotCheckin):
    name = "Akile 群组发言"
    chat_name = -1001796203774
    bot_checkin_cmd = ["/checkin@akilecloud_bot"]

    async def send_checkin(self):
        cmd = random.choice(to_iterable(self.bot_checkin_cmd))
        await self.send(cmd)
        self.finished.set()
