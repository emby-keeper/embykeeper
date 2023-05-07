import asyncio
import string
from pyrogram.types import Message
from PIL import Image
from ddddocr import DdddOcr

from ...utils import async_partial

from .base import Monitor

ocr = DdddOcr(show_ad=False)

__ignore__ = True


class MistyMonitor(Monitor):
    name = "Misty"
    chat_name = "FreeEmbyGroup"
    chat_user = "MistyNoiceBot"
    chat_keyword = r"空余名额数: (?!0$)"
    bot_username = "EmbyMistyBot"
    notify_create_name = True

    async def init(self, initial=True):
        self.log.info(f"正在初始化机器人状态.")
        wr = async_partial(self.client.wait_reply, self.bot_username)
        for _ in range(10 if initial else 3):
            try:
                msg: Message = await wr("/cancel")
                if msg.caption and "选择您要使用的功能" in msg.caption or msg.text:
                    msg = await wr("🌏切换服务器")
                    if "选择您要使用的服务器" in msg.text or msg.caption:
                        msg = await wr("✨Misty")
                        if "选择您要使用的功能" in msg.caption or msg.text:
                            msg = await wr("⚡️账号功能")
                if msg.text and "请选择功能" in msg.text or msg.caption:
                    msg = await wr("⚡️注册账号")
                    if "请输入验证码" in msg.caption or msg.text:
                        data = await self.client.download_media(msg, in_memory=True)
                        image = Image.open(data)
                        self.captcha = (
                            ocr.classification(image)
                            .translate(str.maketrans("", "", string.punctuation))
                            .replace(" ", "")
                        )
                        self.log.debug(f"接收到验证码: {self.captcha}")
            except (asyncio.TimeoutError, TypeError):
                continue
            else:
                if (
                    self.captcha
                    and len(self.captcha) == 5
                    and (all(i not in self.captcha for i in ("1", "7", "0")) or not initial)
                ):
                    self.log.info(f"机器人状态初始化完成, 当接收到验证码时将输入验证码 {self.captcha}, 请勿操作 @EmbyMistyBot.")
                    return True
                else:
                    self.log.info(f"机器人状态初始化失败, 正在重试.")
        else:
            self.log.bind(notify=True).warning(f"机器人状态初始化失败, 监控将停止.")
            return False

    async def start(self):
        self.captcha = None
        if await self.init(initial=True):
            return await super().start()

    async def on_trigger(self, message: Message, keys, reply):
        wr = async_partial(self.client.wait_reply, self.bot_username)
        for _ in range(3):
            msg = await wr(self.captcha)
            if "验证码错误" in msg.text:
                self.log.info(f"验证码错误, 将重新初始化.")
                if not await self.init():
                    return
            elif "暂时停止注册" in msg.text:
                self.log.info(f"注册名额已满, 将进行重试.")
                if not await self.init():
                    return
            elif "用户名" in msg.text:
                msg = await wr(self.unique_name)
                if "密码" in msg.text:
                    await self.client.send_message(self.bot_username, "/cancel")
                    self.log.bind(notify=True).info(f'已向Bot发送用户注册申请: "{self.unique_name}", 请检查结果.')
        else:
            self.log.info(f"未成功, 结束注册申请.")
