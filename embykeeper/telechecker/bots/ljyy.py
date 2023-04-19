from .base import AnswerBotCheckin

from pyrogram.errors import BadRequest

__ignore__ = True


class LJYYCheckin(AnswerBotCheckin):
    name = "垃圾影音"
    bot_username = "zckllflbot"
    bot_captcha_len = 4
    bot_use_history = 20
    bot_text_ignore = "下列选项"

    async def retry(self):
        if self.message:
            try:
                await self.message.click()
            except (BadRequest, TimeoutError):
                pass
        await super().retry()
