from pyrogram.types import Message

from .base import Monitor

__ignore__ = True


class TestMonitor:
    class T1(Monitor):
        name = "测试-1"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"测试\s*([\w]+)$"
        chat_delay = 1

        def chat_reply(self, message: Message, keys):
            return f'接收到: "{keys[0]}"'

    class T2(Monitor):
        name = "测试-2"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"从众"
        chat_follow_user = 3
        chat_delay = 1
        chat_reply = "我来"
