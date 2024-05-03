from .pornemby import PornembyMessager

__ignore__ = True


class TestMessager(PornembyMessager):
    name = "测试群组"
    chat_name = "api_group"
    default_messages = ["pornemby-common-wl@latest.yaml * 1000"]
