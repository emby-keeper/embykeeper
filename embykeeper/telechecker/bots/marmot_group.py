import random
from ...utils import to_iterable
from ._base import BotCheckin


class MarmotGroupCheckin(BotCheckin):
    name = "Marmot 群组发言"
    chat_name = "Marmot_Emby"
    bot_checkin_cmd = ["卡", "打卡", "保号", "冒泡"]
    skip = 14

    async def send_checkin(self):
        cmd = random.choice(to_iterable(self.bot_checkin_cmd))
        await self.send(cmd)
        self.finished.set()
