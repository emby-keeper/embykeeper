from .base import Messager

__ignore__ = True


class TestMessager(Messager):
    name = "测试群组"
    chat_name = "api_group"
    default_messages = ["watery-wl@v1.yaml * 100"]
