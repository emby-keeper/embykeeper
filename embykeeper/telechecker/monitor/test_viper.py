from .viper import ViperMonitor

class TestViperMonitor(ViperMonitor):
    name = "Viper 测试"
    chat_name = "api_group"
    chat_allow_outgoing = True
    chat_user = []
