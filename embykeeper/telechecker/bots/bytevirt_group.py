import random
from ...utils import to_iterable
from ._base import BotCheckin

__ignore__ = True

class ByteVirtGroupCheckin(BotCheckin):
    name = "ByteVirt 群组发言"
    chat_name = -1001606760737
    bot_checkin_cmd = ["/showmethemoney"]

    async def send_checkin(self):
        cmd = random.choice(to_iterable(self.bot_checkin_cmd))
        await self.send(cmd)
        self.finished.set()
