import random
from ...utils import to_iterable
from ._base import BotCheckin


class FeiyueMusicGroupCheckin(BotCheckin):
    name = "飞跃星空群组发言"
    chat_name = -1002197507537
    bot_checkin_cmd = "签到"
    skip = 14

    async def send_checkin(self):
        cmd = random.choice(to_iterable(self.bot_checkin_cmd))
        await self.send(cmd)
        self.finished.set()
