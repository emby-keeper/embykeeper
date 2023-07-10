import asyncio
import random
from pyrogram.types import Message
from thefuzz import process, fuzz

from ...data import get_data
from .base import AnswerBotCheckin


class JMSCheckin(AnswerBotCheckin):
    ocr = "idioms@v2"
    idioms = None
    lock = asyncio.Lock()

    name = "卷毛鼠"
    bot_username = "jmsembybot"

    async def start(self):
        self.retries = 2
        async with self.lock:
            if self.idioms is None:
                with open(
                    await get_data(self.basedir, "idioms@v1.txt", proxy=self.proxy, caller=self.name)
                ) as f:
                    self.__class__.idioms = [i for i in f.read().splitlines() if len(i) == 4]
        return await super().start()

    def to_idiom(self, captcha: str):
        phrase, score = process.extractOne(captcha, self.idioms)
        if score > 70 or len(captcha) < 4:
            result = phrase
            self.log.debug(f'[gray50]已匹配识别验证码 "{captcha}" -> 成语 "{result}".[/]')
        else:
            result = captcha
            self.log.debug(f'[gray50]验证码 "{captcha}" 无法矫正, 使用原词.[/]')
        return result

    async def on_captcha(self, message: Message, captcha: str):
        captcha = self.to_idiom(captcha)
        async with self.operable:
            if not self.message:
                await self.operable.wait()
            await asyncio.sleep(random.randint(300, 500) / 100)
            for l in captcha:
                try:
                    await self.message.click(l)
                    await asyncio.sleep(random.randint(50, 300) / 100)
                except ValueError:
                    self.log.info(f'未能找到对应 "{l}" 的按键, 正在重试.')
                    await self.retry()
                    break
