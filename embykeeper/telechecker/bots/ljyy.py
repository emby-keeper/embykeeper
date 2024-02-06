from .base import AnswerBotCheckin

from pyrogram.types import Message
from pyrogram.errors import RPCError
from thefuzz import fuzz


class LJYYCheckin(AnswerBotCheckin):
    ocr = "uchars4@v1"

    name = "垃圾影音"
    bot_username = "zckllflbot"
    bot_checkin_cmd = ["/cz"]
    bot_use_history = 20
    bot_text_ignore = "下列选项"
    bot_checkin_button_pat = r"\w\s\w\s\w\s\w"

    async def message_handler(self, client, message: Message):
        if message.text and "请选择操作项" in message.text and message.reply_markup:
            keys = [k.text for r in message.reply_markup.inline_keyboard for k in r]
            for k in keys:
                if "签到" in k:
                    await message.click(k)
                    return
            else:
                self.log.warning(f"签到失败: 账户错误.")
                return await self.fail()
        await super().message_handler(client, message)

    async def on_captcha(self, message: Message, captcha: str):
        async with self.operable:
            if not self.message:
                await self.operable.wait()
            match = [(k, fuzz.ratio(k, captcha)) for k in self.get_keys(self.message)]
            max_k, max_r = max(match, key=lambda x: x[1])
            self.log.info(f"识别字符: {captcha}, 选择字符: {max_k}")
            await self.message.click(max_k)
