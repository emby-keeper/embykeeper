from pyrogram.types import Message

from ..link import Link
from .base import Monitor


class PornembyExamMonitor(Monitor):
    name = "Pornemby 科举"
    chat_name = "PornembyFun"
    chat_user = "pornemby_question_bot"
    chat_keyword = r"问题\d+：(.*?)\n+(A:.*\n+B:.*\n+C:.*\n+D:.*)\n(?!\n*答案)"

    key_map = {
        "A": "🅰",
        "B": "🅱",
        "C": "🅲",
        "D": "🅳",
    }

    async def on_trigger(self, message: Message, keys, reply):
        result = await Link(self.client).answer(keys[0] + "\n" + keys[1])
        if result:
            self.log.info(f"问题回答: {result}.")
        else:
            self.log.info(f"回答失败.")
            return
        try:
            await message.click(self.key_map[result])
            self.log.info(f"回答结果: {result}.")
        except KeyError:
            self.log.info(f"点击失败: {result} 不是可用的答案.")
