from pyrogram.types import Message

from .base import Monitor
from .pornemby import PornembyMonitor
from .misty import MistyMonitor
from .bgk import BGKMonitor
from .polo import PoloMonitor
from .viper import ViperMonitor

__ignore__ = True


class TestMonitor:
    class TestReplyMonitor(Monitor):
        name = "回复测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"回复\s*(\w+)"
        chat_delay = 1

        def chat_reply(self, message: Message, keys):
            return f'接收到: "{keys[0]}"'

    class TestGroupMonitor(Monitor):
        name = "多组测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"多组\s*(\w+)\s+(\w+)"
        chat_delay = 1

        def chat_reply(self, message: Message, keys):
            return f'接收到: "{keys[0]}" => "{keys[1]}"'

    class TestFollowMonitor(Monitor):
        name = "从众测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"从众"
        chat_follow_user = 3
        chat_delay = 1
        chat_reply = "我来"

    class TestPornembyExamMonitor(PornembyMonitor.PornembyAnswerMonitor):
        name = "Pornemby科举测试"
        chat_name = "api_group"
        chat_user = "embykeeper_test_bot"

    class TestMistyMonitor(MistyMonitor):
        name = "Misty测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []

    class TestBGKMonitor(BGKMonitor):
        name = "不给看测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []

    class TestViperMonitor(ViperMonitor):
        name = "Viper测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []

    class TestPoloMonitor(PoloMonitor):
        name = "Polo测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []
