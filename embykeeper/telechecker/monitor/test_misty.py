from .misty import MistyMonitor


class TestMistyMonitor(MistyMonitor):
    name = "Misty 测试"
    chat_name = "api_group"
    chat_allow_outgoing = True
    chat_user = []
