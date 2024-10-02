import random
from ...utils import to_iterable
from ._base import BotCheckin


class MarmotGroupCheckin(BotCheckin):
    name = "Marmot 群组发言"
    chat_name = -1001975531465
    bot_checkin_cmd = ["签到", "打劫", "没币了", "低保", "打卡", "冒泡"]
    skip = 14

    async def send_checkin(self):
        cmd = random.choice(to_iterable(self.bot_checkin_cmd))
        await self.send(cmd)
        self.finished.set()
