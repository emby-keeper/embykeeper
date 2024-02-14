from pyrogram.types import Message

from .base import AnswerBotCheckin

__ignore__ = True


class TembyCheckin(AnswerBotCheckin):
    name = "Temby"
    bot_username = "HiEmbyBot"
    bot_checkin_cmd = "/hi"
    bot_success_keywords = ["Checkin successfully"]
    bot_checked_keywords = ["you have checked in already today"]

    async def on_answer(self, message: Message):
        await super().on_answer(message)
        await message.click(0)
