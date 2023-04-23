from pyrogram.types import Message

from ..link import Link

from .base import Monitor

__ignore__ = True

class TestMonitor:
    class TestReplyMonitor(Monitor):
        name = "回复测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"测试\s*([\w]+)$"
        chat_delay = 1

        def chat_reply(self, message: Message, keys):
            return f'接收到: "{keys[0]}"'

    class TestFollowMonitor(Monitor):
        name = "从众测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"从众"
        chat_follow_user = 3
        chat_delay = 1
        chat_reply = "我来"