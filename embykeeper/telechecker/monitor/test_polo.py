from .polo import PoloMonitor

class TestPoloMonitor(PoloMonitor):
    name = "Polo 测试"
    chat_name = "api_group"
    chat_allow_outgoing = True
    chat_user = []
