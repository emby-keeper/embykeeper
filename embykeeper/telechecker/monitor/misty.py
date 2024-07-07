import asyncio
import random
import string

from pyrogram.types import Message
from PIL import Image
from ddddocr import DdddOcr

from ...utils import async_partial
from ...data import get_datas
from ..lock import misty_locks
from ._base import Monitor

__ignore__ = True

misty_monitor_pool = {}


class MistyMonitor(Monitor):
    ocr = "digit5-large@v1"
    lock = asyncio.Lock()

    name = "Misty"
    chat_name = "FreeEmbyGroup"
    chat_user = "MistyNoiceBot"
    chat_keyword = r"空余名额数: (?!0$)"
    bot_username = "EmbyMistyBot"
    notify_create_name = True

    async def init(self, initial=True):
        async with self.lock:
            if isinstance(self.ocr, str):
                data = []
                files = (f"{self.ocr}.onnx", f"{self.ocr}.json")
                async for p in get_datas(self.basedir, files, proxy=self.proxy, caller=self.name):
                    if p is None:
                        self.log.info(f"初始化错误: 无法下载所需文件.")
                        return False
                    else:
                        data.append(p)
                self.__class__.ocr = DdddOcr(
                    show_ad=False, import_onnx_path=str(data[0]), charsets_path=str(data[1])
                )

        misty_monitor_pool[self.client.me.id] = self
        self.captcha = None
        self.log.info(f"正在初始化机器人状态.")
        wr = async_partial(self.client.wait_reply, self.bot_username)
        misty_locks.setdefault(self.client.me.id, asyncio.Lock())
        lock = misty_locks.get(self.client.me.id, None)
        async with lock:
            for _ in range(20 if initial else 3):
                try:
                    msg: Message = await wr("/cancel")
                    if "选择您要使用的功能" in (msg.caption or msg.text):
                        await asyncio.sleep(random.uniform(2, 4))
                        msg = await wr("⚡️账号功能")
                    if "请选择功能" in (msg.text or msg.caption):
                        await asyncio.sleep(random.uniform(2, 4))
                        msg = await wr("⚡️注册账号")
                        if "请输入验证码" in (msg.caption or msg.text):
                            data = await self.client.download_media(msg, in_memory=True)
                            image = Image.open(data)
                            self.captcha = (
                                self.ocr.classification(image)
                                .translate(str.maketrans("", "", string.punctuation))
                                .replace(" ", "")
                            )
                            self.log.debug(f"接收到验证码: {self.captcha}")
                except (asyncio.TimeoutError, TypeError):
                    continue
                else:
                    if self.captcha and len(self.captcha) == 5:
                        self.log.info(
                            f"机器人状态初始化完成, 当接收到邀请码时将输入验证码 {self.captcha} 以抢注, 请勿操作 @EmbyMistyBot."
                        )
                        return True
                    else:
                        self.log.info(f"机器人状态初始化失败, 正在重试.")
            else:
                self.log.bind(notify=True).warning(f"机器人状态初始化失败, 监控将停止.")
                return False

    async def on_trigger(self, message: Message, key, reply):
        wr = async_partial(self.client.wait_reply, self.bot_username)
        misty_locks.setdefault(self.client.me.id, asyncio.Lock())
        lock = misty_locks.get(self.client.me.id, None)
        async with lock:
            for _ in range(3):
                try:
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
                            self.log.bind(notify=True).info(
                                f'已向 Bot @{self.bot_username} 发送了用户注册申请: "{self.unique_name}", 请检查结果.'
                            )
                except asyncio.TimeoutError:
                    pass
            else:
                self.log.info(f"未成功, 结束注册申请.")
