import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, Iterable, List, Union

from loguru import logger
from pyrogram.errors import BadRequest

from ...utils import random_time
from ..tele import ClientsSession

__ignore__ = True


@dataclass(frozen=True)
class MessageSchedule:
    message: str
    at: Union[Iterable[Union[str, time]], Union[str, time]] = ("0:00", "23:59")
    days: int = 1
    possibility: float = 1.0
    only: str = None

    def next_time(self, days=None):
        days = days if days is not None else self.days
        if days:
            rtime = random_time(*self.at)
        else:
            start, end = self.at
            rtime = random_time(max(start, datetime.now().time()), end)
        return datetime.combine(datetime.today() + timedelta(days=days), rtime)


class Messager:
    name: str = None  # 水群器名称
    chat_name: str = None  # 群聊的名称
    messages: List[MessageSchedule] = []  # 可用的话术列表

    def __init__(self, account, username=None, nofail=True, proxy=None, basedir=None):
        self.account = account
        self.nofail = nofail
        self.proxy = proxy
        self.basedir = basedir

        self.log = logger.bind(scheme="telemessager", name=self.name, username=username)
        self.timeline: Dict[Messager, datetime] = {}

    async def start(self):
        for i, m in enumerate(self.messages):
            if isinstance(m, MessageSchedule):
                self.timeline[i] = m.next_time(days=0)
        while True:
            next_i = min(self.timeline, key=self.timeline.get)
            next_m = self.messages[next_i]
            self.log.info(f"下一次发送将在 [blue]{self.timeline[next_i].strftime('%m-%d %H:%M:%S %p')}[/] 进行.")
            await asyncio.sleep((self.timeline[next_i] - datetime.now()).seconds)
            await self._send(next_m.message, next_m.possibility, next_m.only)
            self.timeline[next_i] = next_m.next_time()

    async def _send(self, *args, **kw):
        try:
            return await self.send(*args, **kw)
        except OSError as e:
            self.log.info(f'出现错误: "{e}", 忽略.')
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self.nofail:
                self.log.opt(exception=e).warning(f"发生错误:")
            else:
                raise

    async def send(self, messages, possibility=1.0, only=None):
        if random.random() >= possibility:
            return self.log.info(f"由于概率设置, 本次发送被跳过.")
        if only:
            today = datetime.today()
            if only.startswith("weekday") and today.weekday() > 4:
                return self.log.info(f"由于非周末, 本次发送被跳过.")
            if only.startswith("weekend") and today.weekday() < 5:
                return self.log.info(f"由于非工作日, 本次发送被跳过.")
        async with ClientsSession([self.account], proxy=self.proxy, basedir=self.basedir) as clients:
            async for tg in clients:
                chat = await tg.get_chat(self.chat_name)
                message = random.choice(messages)
                self.log.bind(username=tg.me.name).info(f'向聊天 "{chat.name}" 发送: [gray50]{message}[/]')
                try:
                    await tg.send_message(self.chat_name, message)
                except BadRequest as e:
                    self.log.warning(f"发送失败: {e}.")
                except KeyError as e:
                    self.log.warning(f"发送失败, 您可能已被封禁: {e}.")
