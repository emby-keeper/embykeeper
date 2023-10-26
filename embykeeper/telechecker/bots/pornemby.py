import asyncio
import random
from .base import AnswerBotCheckin

from pyrogram.types import Message


class PornEmbyCheckin(AnswerBotCheckin):
    name = "Pornemby"
    bot_username = "PronembyTGBot2_bot"
    bot_success_pat = r".*?(\d+)$"

    async def start(self):
        if not self.client.me.username:
            self.log.warning(f"签到失败: 需要设置用户名才可生效.")
            return None
        return await super().start()

    async def on_photo(self, message: Message):
        await asyncio.sleep(random.uniform(2, 4))
        async with self.client.catch_reply(self.bot_username) as f:
            try:
                await message.click(0)
            except TimeoutError:
                pass
            try:
                await asyncio.wait_for(f, 10)
            except asyncio.TimeoutError:
                self.log.warning(f"签到失败: 签到无回应, 您可能还没有注册{self.name}.")
                await self.fail()
