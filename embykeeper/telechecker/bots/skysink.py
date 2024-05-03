from pyrogram.types import Message
from pyrogram.raw.types.messages import BotCallbackAnswer

from .base import BotCheckin


class SkysinkCheckin(BotCheckin):
    name = "尘烬"
    bot_username = "kyououbot"
    bot_checkin_cmd = "/start"

    async def message_handler(self, client, message: Message):
        if message.caption and "请选择功能" in message.caption and message.reply_markup:
            keys = [k.text for r in message.reply_markup.inline_keyboard for k in r]
            for k in keys:
                if "签到" in k:
                    answer: BotCallbackAnswer = await message.click(k)
                    await self.on_text(Message(id=0), answer.message)
                    return
            else:
                self.log.warning(f"签到失败: 账户错误.")
                return await self.fail()
        await super().message_handler(client, message)
