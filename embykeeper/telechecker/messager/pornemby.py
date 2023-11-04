from datetime import datetime
from ..lock import pornemby_nohp
from .base import Messager


class PornembyMessager(Messager):
    name = "Pornemby"
    chat_name = "Pornemby"
    default_messages = ["pornemby-common-wl@latest.yaml * 100"]

    async def prepare_send(self, message):
        nohp_date = pornemby_nohp.get(self.me.id, None)
        if nohp_date and nohp_date >= datetime.today().date():
            self.log.info(f"取消发送: 血量已耗尽.")
        else:
            return message
