from pyrogram.types import Message, InlineKeyboardMarkup
from pyrogram.errors import RPCError
from pyrogram.enums import MessageEntityType

from ...utils import flatten

from .base import Monitor


class PornembyDragonRainMonitor:
    class PornembyDragonRainClickMonitor(Monitor):
        name = "Pornemby 红包雨"
        chat_user = ["PronembyTGBot2_bot", "PronembyTGBot3_bot"]
        chat_name = "Pornemby"
        chat_keyword = [None]
        additional_auth = ["pornemby_pack"]

        async def on_trigger(self, message: Message, key, reply):
            if message.reply_markup:
                if isinstance(message.reply_markup, InlineKeyboardMarkup):
                    buttons = flatten(message.reply_markup.inline_keyboard)
                    for b in buttons:
                        if "红包奖励" in b.text:
                            try:
                                await message.click(b.text)
                            except TimeoutError:
                                self.log.info("检测到 Pornemby 抢红包雨, 已点击抢红包, 等待结果.")
                            except RPCError:
                                self.log.info("检测到 Pornemby 抢红包雨, 但没有抢到红包.")
                            else:
                                self.log.info("检测到 Pornemby 抢红包雨, 已点击抢红包, 等待结果.")
                            return

    class PornembyDragonRainStatusMonitor(Monitor):
        name = "Pornemby 红包雨结果"
        chat_user = ["PronembyTGBot2_bot", "PronembyTGBot3_bot"]
        chat_name = "Pornemby"
        chat_keyword = "恭喜\s+(.*):本次获得(\d+)豆"

    async def on_trigger(self, message: Message, key, reply):
        for me in message.entities:
            if me.type == MessageEntityType.TEXT_MENTION:
                if me.user.id == self.client.me.id:
                    self.log.info(f"红包雨结果: 恭喜获得 {key[1]} 豆.")
