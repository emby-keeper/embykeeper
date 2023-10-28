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
        name = "回复 测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"回复\s*(\w+)"
        chat_delay = 1

        def chat_reply(self, message: Message, keys):
            return f'接收到: "{keys[0]}"'

    class TestGroupMonitor(Monitor):
        name = "多组 测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"多组\s*(\w+)\s+(\w+)"
        chat_delay = 1

        def chat_reply(self, message: Message, keys):
            return f'接收到: "{keys[0]}" => "{keys[1]}"'

    class TestFollowMonitor(Monitor):
        name = "从众 测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_keyword = r"从众"
        chat_follow_user = 3
        chat_delay = 1
        chat_reply = "我来"

    class TestPornembyExamMonitor(PornembyMonitor.PornembyAnswerMonitor):
        name = "Pornemby 科举 测试"
        chat_name = "api_group"
        chat_user = "embykeeper_test_bot"
        chat_allow_outgoing = True

    class TestPornembyDragonRainMonitor(PornembyMonitor.PornembyDragonRainMonitor):
        name = "Pornemby 红包雨 测试"
        chat_name = "api_group"
        chat_user = "embykeeper_test_bot"
        chat_allow_outgoing = True

    class TestPornembyDoubleMonitor(PornembyMonitor.PornembyDoubleMonitor):
        name = "Pornemby 怪兽自动翻倍 测试"
        chat_name = "api_group"
        chat_user = "embykeeper_test_bot"
        chat_allow_outgoing = True

    class TestMistyMonitor(MistyMonitor):
        name = "Misty 测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []

    class TestBGKMonitor(BGKMonitor):
        name = "不给看 测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []

    class TestViperMonitor(ViperMonitor):
        name = "Viper 测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []

    class TestPoloMonitor(PoloMonitor):
        name = "Polo 测试"
        chat_name = "api_group"
        chat_allow_outgoing = True
        chat_user = []
