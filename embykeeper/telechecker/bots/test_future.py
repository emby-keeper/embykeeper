import asyncio
import random

from pyrogram.types import Message
from pyrogram.raw.functions.messages import RequestWebView

from .future import FutureCheckin


__ignore__ = True


class TestFutureCheckin(FutureCheckin):
    name = "未响签到测试"

    click_button = ["注册", "註冊"]
