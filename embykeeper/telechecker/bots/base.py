import asyncio
import re
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from enum import Flag, auto
import string
import time
from typing import Iterable, List, Union

from ddddocr import DdddOcr
from appdirs import user_data_dir
from loguru import logger
from PIL import Image
from pyrogram import filters
from pyrogram.errors import UsernameNotOccupied, FloodWait
from pyrogram.handlers import EditedMessageHandler, MessageHandler
from pyrogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup
from thefuzz import fuzz
from aiocache import cached

from ...data import get_datas
from ...utils import to_iterable, AsyncCountPool
from ..tele import Client

__ignore__ = True


class MessageType(Flag):
    TEXT = auto()
    CAPTION = auto()
    CAPTCHA = auto()
    ANSWER = auto()


class BaseBotCheckin(ABC):
    name = None

    def __init__(self, client: Client, retries=4, timeout=120, nofail=True, basedir=None, proxy=None):
        self.client = client
        self.retries = retries
        self.timeout = timeout
        self.nofail = nofail
        self.basedir = basedir or user_data_dir(__name__)
        self.proxy = proxy
        self.finished = asyncio.Event()
        self.log = logger.bind(scheme="telechecker", name=self.name, username=client.me.name)

    async def _start(self):
        try:
            return await self.start()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self.nofail:
                self.log.opt(exception=e).warning(f"初始化错误:")
                return False
            else:
                raise

    @abstractmethod
    async def start(self):
        pass


class BotCheckin(BaseBotCheckin):
    """签到类, 用于回复模式签到."""

    group_pool = AsyncCountPool(base=2000)
    ocr = None

    name: str = None  # 签到器的名称
    bot_id: int = None  # Bot 的 UserID
    bot_username: str = None  # Bot 的 用户名
    bot_checkin_cmd: Union[str, List[str]] = ["/checkin"]  # Bot 依次执行的签到命令
    bot_send_interval: int = 1  # 签到命令间等待的秒数
    bot_checkin_caption_pat: str = None  # 当 Bot 返回图片时, 仅当符合该 regex 才识别为验证码
    bot_text_ignore: Union[str, List[str]] = []  # 当含有列表中的关键词, 即忽略该消息
    bot_captcha_len: Iterable = None  # 验证码的可能范围
    bot_success_pat: str = r"(\d+)[^\d]*(\d+)"  # 当接收到成功消息后, 从消息中提取数字的模式
    bot_retry_wait: int = 2  # 失败时等待的秒数
    bot_use_history: int = None  # 首先尝试识别历史记录中最后一个验证码图片, 最多识别 N 条
    bot_allow_from_scratch: bool = False  # 允许从未聊天情况下启动
    chat_name: str = None  # 在群聊中向机器人签到

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._is_archived = False
        self._retries = 0
        self._waiting = {}

    def get_filter(self):
        filter = filters.user(self.bot_id or self.bot_username)
        if self.chat_name:
            filter = filter & filters.chat(self.chat_name)
        else:
            filter = filter & filters.private
        return filter

    def get_handlers(self):
        return [
            MessageHandler(self._message_handler, self.get_filter()),
            EditedMessageHandler(self._message_handler, self.get_filter()),
        ]

    @asynccontextmanager
    async def listener(self):
        group = await self.group_pool.append(self)
        handlers = self.get_handlers()
        for h in handlers:
            self.client.add_handler(h, group=group)
        yield
        for h in handlers:
            try:
                self.client.remove_handler(h, group=group)
            except ValueError:
                pass

    @cached(ttl=60, noself=True)
    async def get_ocr(self, ocr: str = None):
        if not ocr:
            return DdddOcr(beta=True, show_ad=False)
        else:
            data = []
            files = (f"{ocr}.onnx", f"{ocr}.json")
            async for p in get_datas(self.basedir, files, proxy=self.proxy, caller=self.name):
                if p is None:
                    self.log.warning(f"初始化错误: 无法下载所需文件.")
                    return None
                else:
                    data.append(p)
            return DdddOcr(show_ad=False, import_onnx_path=str(data[0]), charsets_path=str(data[1]))

    async def start(self):
        ident = self.chat_name or self.bot_id or self.bot_username
        while True:
            try:
                chat = await self.client.get_chat(ident)
            except UsernameNotOccupied:
                self.log.warning(f'初始化错误: 会话 "{ident}" 不存在.')
                return False
            except KeyError as e:
                self.log.info(f"初始化错误: 无法访问, 您可能已被封禁: {e}.")
                return False
            except FloodWait as e:
                self.log.info(f"初始化信息: Telegram 要求等待 {e.value} 秒.")
                await asyncio.sleep(e.value)
            else:
                break
        async for d in self.client.get_dialogs(folder_id=1):
            if d.chat.id == chat.id:
                self._is_archived = True
                break
        else:
            async for d in self.client.get_dialogs(folder_id=0):
                if d.chat.id == chat.id:
                    break
            else:
                if not self.bot_allow_from_scratch:
                    self.log.info(f'跳过签到: 从未与 "{ident}" 交流.')
                    return None

        bot = await self.client.get_users(self.bot_id or self.bot_username)
        msg = f"开始执行签到: [green]{bot.name}[/] [gray50](@{bot.username})[/]"
        if chat.title:
            msg += f" @ [green]{chat.title}[/] [gray50](@{chat.username})[/]"
        self.log.info(msg + ".")

        if not self.chat_name:
            self.log.debug(f"[gray50]禁用提醒 {self.timeout} 秒: {bot.username}[/]")
            await self.client.mute_chat(ident, time.time() + self.timeout + 10)

        try:
            async with self.listener():
                cancelled = False
                try:
                    if self.bot_use_history is None:
                        await self.send_checkin()
                    elif not await self.walk_history(self.bot_use_history):
                        await self.send_checkin()
                    await asyncio.wait_for(self.finished.wait(), self.timeout)
                except asyncio.CancelledError:
                    cancelled = True
                    raise
                finally:
                    if not cancelled:
                        if not await self.cleanup():
                            self.log.debug(f"[gray50]执行清理失败: {ident}[/]")
                        if self._is_archived:
                            self.log.debug(f"[gray50]将会话重新归档: {ident}[/]")
                            try:
                                if await chat.archive():
                                    self.log.debug(f"[gray50]重新归档成功: {ident}[/]")
                            except asyncio.TimeoutError:
                                self.log.debug(f"[gray50]归档失败: {ident}[/]")
                        if not self.chat_name:
                            self.log.debug(f"[gray50]将会话设为已读: {ident}[/]")
                            try:
                                if await self.client.read_chat_history(ident):
                                    self.log.debug(f"[gray50]设为已读成功: {ident}[/]")
                            except asyncio.TimeoutError:
                                self.log.debug(f"[gray50]设为已读失败: {ident}[/]")
        except OSError as e:
            self.log.warning(f'初始化错误: "{e}".')
            return False
        except asyncio.TimeoutError:
            pass
        if not self.finished.is_set():
            self.log.warning("无法在时限内完成签到.")
            return False
        else:
            return self._retries <= self.retries

    async def cleanup(self):
        return True

    async def walk_history(self, limit=0):
        async for m in self.client.get_chat_history(
            self.chat_name or self.bot_id or self.bot_username, limit=limit
        ):
            if MessageType.CAPTCHA in self.message_type(m):
                await self.on_photo(m)
                return True
        return False

    async def send(self, cmd):
        if self.chat_name:
            bot = await self.client.get_users(self.bot_id or self.bot_username)
            await self.client.send_message(self.chat_name, f"{cmd}@{bot.username}")
        else:
            await self.client.send_message(self.bot_id or self.bot_username, cmd)

    async def send_checkin(self, retry=False):
        cmds = to_iterable(self.bot_checkin_cmd)
        for i, cmd in enumerate(cmds):
            if retry and not i:
                await asyncio.sleep(self.bot_retry_wait)
            if i < len(cmds):
                await asyncio.sleep(self.bot_send_interval)
            await self.send(cmd)

    async def _message_handler(self, client: Client, message: Message):
        try:
            await self.message_handler(client, message)
        except OSError as e:
            self.log.info(f'发生错误: "{e}", 正在重试.')
            await self.retry()
            message.continue_propagation()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if not self.nofail:
                await self.fail()
                raise
            else:
                self.log.opt(exception=e).warning(f"发生错误:")
                await self.fail()
                message.continue_propagation()
        else:
            message.continue_propagation()

    async def message_handler(self, client: Client, message: Message, type=None):
        text = message.text or message.caption
        if text:
            for p, k in self._waiting.items():
                if re.search(p, text):
                    k.set()
                    self._waiting[p] = message
        type = type or self.message_type(message)
        if MessageType.TEXT in type:
            await self.on_text(message, message.text)
        if MessageType.CAPTION in type:
            await self.on_text(message, message.caption)
        if MessageType.CAPTCHA in type:
            await self.on_photo(message)

    def message_type(self, message: Message):
        if message.photo:
            if message.caption:
                if self.bot_checkin_caption_pat:
                    if re.search(self.bot_checkin_caption_pat, message.caption):
                        return MessageType.CAPTCHA
                    else:
                        return MessageType.CAPTION
                else:
                    return MessageType.CAPTCHA
            else:
                return MessageType.CAPTCHA
        elif message.text:
            return MessageType.TEXT

    async def on_photo(self, message: Message):
        data = await self.client.download_media(message, in_memory=True)
        image = Image.open(data)
        captcha = (
            (await self.get_ocr(self.ocr))
            .classification(image)
            .translate(str.maketrans("", "", string.punctuation))
            .replace(" ", "")
        )
        if captcha:
            self.log.debug(f"[gray50]接收验证码: {captcha}.[/]")
            if self.bot_captcha_len and len(captcha) not in to_iterable(self.bot_captcha_len):
                self.log.info(f"签到失败: 验证码低于设定长度, 正在重试.")
                await self.retry()
            else:
                await asyncio.sleep(1)
                await self.on_captcha(message, captcha)
        else:
            self.log.info(f"签到失败: 接收到空验证码, 正在重试.")
            await self.retry()

    async def on_captcha(self, message: Message, captcha: str):
        await message.reply(captcha)

    async def on_text(self, message: Message, text: str):
        if any(s in text for s in to_iterable(self.bot_text_ignore)):
            pass
        elif any(
            s in text for s in ("拉黑", "黑名单", "冻结", "未找到用户", "无资格", "退出群", "退群", "加群", "加入群聊", "请先关注", "注册")
        ):
            self.log.warning(f"签到失败: 账户错误.")
            await self.fail()
        elif any(s in text for s in ("已尝试", "过多")):
            self.log.warning(f"签到失败: 尝试次数过多.")
            await self.fail()
        elif any(s in text for s in ("失败", "错误", "超时")):
            self.log.info(f"签到失败: 验证码错误, 正在重试.")
            await self.retry()
        elif any(s in text for s in ("成功", "通过", "完成", "获得")):
            matches = re.search(self.bot_success_pat, text)
            if matches:
                try:
                    self.log.info(f"[yellow]签到成功[/]: + {matches.group(1)} 分 -> {matches.group(2)} 分.")
                except IndexError:
                    self.log.info(f"[yellow]签到成功[/]: 当前/增加 {matches.group(1)} 分.")
            else:
                matches = re.search(r"\d+", text)
                if matches:
                    self.log.info(f"[yellow]签到成功[/]: 当前/增加 {matches.group(0)} 分.")
                else:
                    self.log.info(f"[yellow]签到成功[/].")
            self.finished.set()
        elif any(s in text for s in ("只能", "已经", "下次", "过了", "签过", "明日再来", "上次签到")):
            self.log.info(f"今日已经签到过了.")
            self.finished.set()
        else:
            self.log.warning(f"接收到异常返回信息: {text}")

    async def retry(self):
        self._retries += 1
        if self._retries <= self.retries:
            await asyncio.sleep(self.bot_retry_wait)
            await self.send_checkin(retry=True)
        else:
            self.log.warning("超过最大重试次数.")
            self.finished.set()

    async def fail(self):
        self.finished.set()
        self._retries = float("inf")

    async def wait_until(self, pattern: str = ".", timeout: float = None):
        self._waiting[pattern] = e = asyncio.Event()
        try:
            await asyncio.wait_for(e.wait(), timeout)
        except asyncio.TimeoutError:
            return None
        else:
            msg: Message = self._waiting[pattern]
            return msg


class AnswerBotCheckin(BotCheckin):
    """签到类, 用于按钮模式签到."""

    bot_checkin_button_pat: str = None  # 所有按键需要满足的 regex 条件

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.mutex = asyncio.Lock()
        self.operable = asyncio.Condition(self.mutex)
        self.message: Message = None

    async def walk_history(self, limit=0):
        try:
            answer = None
            captcha = None
            async for m in self.client.get_chat_history(
                self.chat_name or self.bot_id or self.bot_username, limit=limit
            ):
                if MessageType.ANSWER in self.message_type(m):
                    answer = answer or m
                if MessageType.CAPTCHA in self.message_type(m):
                    captcha = captcha or m
                if answer and captcha:
                    break
            else:
                return False
            await self.on_answer(answer)
            await self.on_photo(captcha)
            return True
        except Exception as e:
            print(e)

    def get_keys(self, message: Message):
        reply_markup = message.reply_markup
        if isinstance(reply_markup, InlineKeyboardMarkup):
            return [k.text for r in reply_markup.inline_keyboard for k in r]
        elif isinstance(reply_markup, ReplyKeyboardMarkup):
            return [k.text for r in reply_markup.keyboard for k in r]

    def is_valid_answer(self, message: Message):
        if not message.reply_markup:
            return False
        if self.bot_checkin_button_pat:
            for k in self.get_keys(message):
                if not re.search(self.bot_checkin_button_pat, k):
                    return False
        return True

    def message_type(self, message: Message):
        if self.is_valid_answer(message):
            return MessageType.ANSWER | super().message_type(message)
        else:
            return super().message_type(message)

    async def message_handler(self, client: Client, message: Message, type=None):
        type = type or self.message_type(message)
        if MessageType.ANSWER in type:
            await self.on_answer(message)
        await super().message_handler(client, message, type=type)

    async def on_answer(self, message: Message):
        async with self.mutex:
            if self.message:
                if self.message.date > message.date:
                    return
                else:
                    self.message = message
            else:
                self.message = message
                self.operable.notify()

    async def on_captcha(self, message: Message, captcha: str):
        async with self.operable:
            if not self.message:
                await self.operable.wait()
            match = [(k, fuzz.ratio(k, captcha)) for k in self.get_keys(self.message)]
            max_k, max_r = max(match, key=lambda x: x[1])
            if max_r < 75:
                self.log.info(f'未能找到对应 "{captcha}" 的按键, 正在重试.')
                await self.retry()
            else:
                await self.message.click(max_k)
