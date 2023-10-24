from datetime import datetime
from ..lock import pornemby_status
from .base import Messager


class PornembyMessager(Messager):
    name = "Pornemby"
    chat_name = "Pornemby"
    default_messages = ["pornemby-common-wl@latest.yaml * 100"]

    async def prepare_send(self, message):
        if pornemby_status.get("nohp", None) and pornemby_status["nohp"] >= datetime.today().date():
            self.log.warning(f"取消发送: 血量已耗尽.")
        else:
            return message
