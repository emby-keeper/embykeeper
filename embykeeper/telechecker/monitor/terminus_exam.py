from pyrogram.types import Message

from embykeeper.var import console

from ..link import Link
from ._base import Monitor

__ignore__ = True


class TerminusExamMonitor(Monitor):
    name = "终点站考试辅助"
    chat_name = "EmbyPublicBot"
    chat_keyword = r"(.*?(?:\n(?!本题贡献者).*?)*)\n\n本题贡献者.*?\n\n进度: \d+/\d+\s+\|\s+当前分数: \d+"
    allow_edit = True
    additional_auth = ["gpt"]
    debug_no_log = True
    trigger_interval = 0

    async def on_trigger(self, message: Message, key, reply):
        self.log.info(f"新题: {key}, 解析中...")
        if message.reply_markup and message.reply_markup.inline_keyboard:
            options = []
            for row in message.reply_markup.inline_keyboard:
                for button in row:
                    options.append(button.text)
        question = f"问题:\n{key}\n选项:\n" + "\n".join(f"- {option}" for option in options)
        result, by = await Link(self.client).terminus_answer(question)
        if result:
            console.rule(title=f"{by} 给出答案")
            console.print(result)
            console.rule()
        else:
            self.log.warning("解析失败! 请自行回答.")
