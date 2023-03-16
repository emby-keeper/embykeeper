from pyrogram.types import Message

from .base import AnswerBotCheckin


class JMSCheckin(AnswerBotCheckin):
    name = "卷毛鼠"
    bot_username = "jmsembybot"
    bot_captcha_len = 4

    async def on_captcha(self, message: Message, captcha: str):
        async with self.operable:
            if not self.message:
                await self.operable.wait()
            for l in captcha:
                try:
                    await self.message.click(l)
                except ValueError:
                    self.log.info(f'未能找到对应 "{l}" 的按键, 正在重试.')
                    await self.retry()
                    break
