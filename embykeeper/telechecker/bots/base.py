import asyncio
import re
from contextlib import asynccontextmanager, suppress
from enum import Flag, auto

import ddddocr
from loguru import logger
from PIL import Image
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.handlers import EditedMessageHandler, MessageHandler
from pyrogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup
from thefuzz import fuzz

ocr = ddddocr.DdddOcr(beta=True, show_ad=False)


class MessageType(Flag):
    TEXT = auto()
    CAPTION = auto()
    CAPTCHA = auto()
    ANSWER = auto()


class AsyncPool(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = asyncio.Lock()
        self.next = 1001

    async def append(self, value):
        async with self.lock:
            key = self.next
            self[key] = value
            self.next += 1
            return key


class BotCheckin:
    group_pool = AsyncPool()
    name = "Bot"
    bot_id = None
    bot_username = None
    bot_checkin_cmd = ["/checkin"]
    bot_checkin_caption_pat = None
    bot_text_ignore = []
    bot_captcha_len = range(2, 7)
    bot_use_history = None

    def __init__(self, client: Client, retries=10, timeout=120):
        self.client = client
        self.retries = retries
        self.timeout = timeout
        self.finished = asyncio.Event()
        self.log = logger.bind(scheme="telechecker", name=self.name, username=self.client.me.first_name)
        self._retries = 0

    @asynccontextmanager
    async def listener(self):
        handlers = [MessageHandler(self.message_handler), EditedMessageHandler(self.message_handler)]
        group = await BotCheckin.group_pool.append(handlers)
        for h in handlers:
            self.client.add_handler(h, group=group)
        yield
        for h in handlers:
            self.client.remove_handler(h, group=group)

    async def checkin(self):
        self.log.info("开始执行签到.")
        async with self.listener():
            if self.bot_use_history is None:
                await self.send_checkin()
            elif not await self.walk_history(self.bot_use_history):
                await self.send_checkin()
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self.finished.wait(), self.timeout)
        if not self.finished.is_set():
            self.log.warning("无法在时限内完成签到.")
            return False
        else:
            return self._retries <= self.retries

    async def walk_history(self, limit=0):
        async for m in self.client.get_chat_history(self.bot_id or self.bot_username, limit=limit):
            if MessageType.CAPTCHA in self.message_type(m):
                await self.on_photo(m)
                return True
        return False

    async def send(self, cmd):
        await self.client.send_message(self.bot_id or self.bot_username, cmd)

    async def send_checkin(self):
        for cmd in self.bot_checkin_cmd:
            await self.send(cmd)

    async def message_handler(self, client: Client, message: Message):
        if not message.outgoing:
            if message.chat.type == ChatType.BOT:
                if message.from_user.id == self.bot_id or message.from_user.username == self.bot_username:
                    await self.message_parser(message)

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

    async def message_parser(self, message: Message, type=None):
        type = type or self.message_type(message)
        if MessageType.TEXT in type:
            await self.on_text(message, message.text)
        if MessageType.CAPTION in type:
            await self.on_text(message, message.caption)
        if MessageType.CAPTCHA in type:
            await self.on_photo(message)

    async def on_photo(self, message: Message):
        data = await self.client.download_media(message, in_memory=True)
        image = Image.open(data)
        captcha = ocr.classification(image).replace(" ", "")
        if len(captcha) not in self.bot_captcha_len:
            self.log.info(f'验证码"{captcha}" 低于设定长度, 正在重试.')
            await self.retry()
        else:
            await asyncio.sleep(1)
            await self.on_captcha(message, captcha)

    async def on_captcha(self, message: Message, captcha: str):
        self.log.debug(f"接收到验证码: {captcha}")
        await message.reply(captcha)

    async def on_text(self, message: Message, text: str):
        if any(s in text for s in self.bot_text_ignore):
            pass
        elif any(s in text for s in ("失败", "错误", "超时")):
            await self.retry()
        elif any(s in text for s in ("成功", "通过", "完成")):
            matches = re.search(r"(\d+)[^\d]*(\d+)", text)
            if matches:
                self.log.info(f"[yellow]签到成功[/]: + {matches.group(1)} 分 -> {matches.group(2)} 分.")
            else:
                matches = re.search(r"\d+", text)
                if matches:
                    self.log.info(f"[yellow]签到成功[/]: 当前 {matches.group(0)} 分.")
                else:
                    self.log.info(f"[yellow]签到成功[/].")
            self.finished.set()
        elif any(s in text for s in ("只能", "已经", "下次", "过了")):
            self.log.info(f"今日已经签到过了.")
            self.finished.set()
        else:
            self.log.warning(f"接收到异常返回信息: {text}")

    async def retry(self):
        self._retries += 1
        if self._retries <= self.retries:
            await asyncio.sleep(5)
            await self.send_checkin()
        else:
            self.log.error("超过最大重试次数.")
            self.finished.set()


class AnswerBotCheckin(BotCheckin):
    bot_checkin_button_pat = None

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.mutex = asyncio.Lock()
        self.operable = asyncio.Condition(self.mutex)
        self.message: Message = None

    async def walk_history(self, limit=0):
        answer = None
        captcha = None
        async for m in self.client.get_chat_history(self.bot_id or self.bot_username, limit=limit):
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

    def get_keys(self, message: Message):
        reply_markup = message.reply_markup
        if isinstance(reply_markup, InlineKeyboardMarkup):
            return [k.text for r in reply_markup.inline_keyboard for k in r]
        elif isinstance(reply_markup, ReplyKeyboardMarkup):
            return [k.text for r in reply_markup.keyboard for k in r]

    def is_valid_answer(self, message: Message):
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

    async def message_parser(self, message: Message):
        type = self.message_type(message)
        if MessageType.ANSWER in type:
            await self.on_answer(message)
        await super().message_parser(message, type=type)

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
