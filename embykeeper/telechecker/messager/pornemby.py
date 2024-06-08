import asyncio
from datetime import datetime

from ..lock import (
    pornemby_nohp,
    pornemby_messager_enabled,
    pornemby_messager_mids,
    pornemby_alert,
)
from ..tele import ClientsSession
from ._base import Messager


class PornembyMessager(Messager):
    name = "Pornemby"
    chat_name = "Pornemby"
    default_messages = ["pornemby-common-wl@latest.yaml * 100"]

    async def init(self):
        self.lock = asyncio.Lock()
        pornemby_messager_enabled[self.me.id] = True
        pornemby_messager_mids[self.me.id] = []
        return True

    async def send(self, message):
        if pornemby_alert.get(self.me.id, False):
            self.log.info(f"由于风险急停取消发送.")
            return
        nohp_date = pornemby_nohp.get(self.me.id, None)
        if nohp_date and nohp_date >= datetime.today().date():
            self.log.info(f"取消发送: 血量已耗尽.")
            return
        msg = await super().send(message)
        if msg:
            pornemby_messager_mids[self.me.id].append(msg.id)
        return msg

    async def checkin(self):
        self.log.info("等待发送: 今日尚未签到, 正在签到.")
        from ..bots.pornemby import PornembyCheckin

        async with ClientsSession([self.account], proxy=self.proxy, basedir=self.basedir) as clients:
            async for tg in clients:
                result = await PornembyCheckin(
                    client=tg,
                    retries=1,
                    nofail=True,
                    basedir=self.basedir,
                    proxy=self.proxy,
                )._start()
                if not result:
                    self.log.info("取消发送: 今日尚未签到, 且签到失败.")
                    return
