import time

from loguru import logger

from .base import AnswerBotCheckin


class LJYYCheckin(AnswerBotCheckin):
    name = "垃圾影音"
    bot_username = "zckllflbot"
    bot_captcha_len = [4]
    bot_use_history = 20
    bot_text_ignore = ["下列选项"]

    async def retry(self):
        if self.message:
            self.message.click()
        await super().retry()
