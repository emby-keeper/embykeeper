from pyrogram.types import Message
from pyrogram.raw.types.messages import BotCallbackAnswer

from embykeeper.utils import to_iterable

from ._base import BotCheckin

__ignore__ = True


class TemplateACheckin(BotCheckin):
    bot_checkin_cmd = "/start"
    templ_panel_keywords = ["请选择功能", "用户面板"]

    async def message_handler(self, client, message: Message):
        text = message.caption or message.text
        if (
            text
            and any(keyword in text for keyword in to_iterable(self.templ_panel_keywords))
            and message.reply_markup
        ):
            keys = [k.text for r in message.reply_markup.inline_keyboard for k in r]
            for k in keys:
                if "签到" in k:
                    try:
                        answer: BotCallbackAnswer = await message.click(k)
                    except TimeoutError:
                        self.log.debug(f"点击签到按钮无响应, 可能按钮未正确处理点击回复. 一般来说不影响签到.")
                    else:
                        await self.on_text(Message(id=0), answer.message)
                    return
            else:
                self.log.warning(f"签到失败: 账户错误.")
                return await self.fail()

        if message.text and "请先点击下面加入我们的" in message.text:
            self.log.warning(f"签到失败: 账户错误.")
            return await self.fail()

        await super().message_handler(client, message)


def use(**kw):
    return type("TemplatedClass", (TemplateACheckin,), kw)
