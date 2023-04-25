from pyrogram.types import Message

from ...utils import truncate_str
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
        spec = f"[gray50]({truncate_str(keys[0], 10)})[/]"
        for retries in range(3):
            result = await Link(self.client).answer(keys[0] + "\n" + keys[1])

            if result:
                self.log.info(f"问题回答: {result} {spec}.")
                break
            else:
                self.log.info(f"问题错误或超时, 正在重试 {spec}.")
        else:
            self.log.info(f"错误次数超限, 回答失败 {spec}.")
            return
        try:
            answer = await message.click(self.key_map[result])
            self.log.info(f'回答结果: "{answer.message}" {spec}.')
        except KeyError:
            self.log.info(f"点击失败: {result} 不是可用的答案 {spec}.")
