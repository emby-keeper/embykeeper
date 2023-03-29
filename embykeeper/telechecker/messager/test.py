from datetime import datetime, timedelta

from .base import Messager
from .common import WATERY

__ignore__ = True


class TestMessager(Messager):
    name = "测试群组"
    chat_name = "api_group"
    messages = WATERY(100, (datetime.now().time(), (datetime.now() + timedelta(minutes=10)).time()))
