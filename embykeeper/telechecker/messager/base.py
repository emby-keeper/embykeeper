import asyncio
import random
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable, List, Union

import yaml
from dateutil import parser
from loguru import logger
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import ChatWriteForbidden, RPCError
from schema import Optional, Schema, SchemaError

from ...data import get_data
from ...utils import random_time, show_exception, time_in_range, truncate_str
from ..tele import ClientsSession

__ignore__ = True


@dataclass(eq=False)
class MessageSchedule:
    """定义一个发送规划, 即在特定时间段内某些消息中的一个有一定几率被发送."""

    messages: Iterable[str]
    at: Union[Iterable[Union[str, time]], Union[str, time]] = ("0:00", "23:59")
    days: int = 0
    possibility: float = 1.0
    multiply: int = 1
    only: str = None

    def next_time(self, days=None, trange=None):
        """生成下一个发送时间"""
        days = days if days is not None else self.days
        trange = trange if trange is not None else self.at
        rtime = datetime.combine(datetime.today() + timedelta(days=days), random_time(*trange))
        if rtime < datetime.now():
            rtime += timedelta(days=1)
        return rtime

    def roll(self, days=None, trange=None):
        skip = False
        if random.random() >= self.possibility:
            skip = True
        if self.only:
            today = datetime.today()
            if self.only.startswith("weekday") and today.weekday() > 4:
                skip = True
            if self.only.startswith("weekend") and today.weekday() < 5:
                skip = True
        return MessagePlan(
            message=random.choice(self.messages),
            at=self.next_time(days=days, trange=trange),
            schedule=self,
            skip=skip,
        )


@dataclass(eq=False)
class MessagePlan:
    """定义一个发送计划, 即在某事件发送某个消息."""

    message: str
    at: datetime
    schedule: MessageSchedule
    skip: bool = False


class Messager:
    """自动水群类."""

    name: str = None  # 水群器名称
    chat_name: str = None  # 群聊的名称
    default_messages: List[str] = []  # 默认的话术列表资源名

    site_last_message_time = None
    site_lock = asyncio.Lock()

    def __init__(self, account, username=None, nofail=True, proxy=None, basedir=None, config: dict = None):
        """
        自动水群类.
        参数:
            account: 账号登录信息
            username: 用户名, 仅用于在登录前的日志输出
            nofail: 启用错误处理外壳, 当错误时报错但不退出
            basedir: 文件存储默认位置
            proxy: 代理配置
            config: 当前水群器的特定配置
        """
        self.account = account
        self.nofail = nofail
        self.proxy = proxy
        self.basedir = basedir
        self.config = config

        self.min_interval = timedelta(
            seconds=config.get("min_interval", config.get("interval", 1800))
        )  # 两条消息间的最小间隔时间
        max_interval = config.get("max_interval", None)
        if max_interval:
            self.max_interval = timedelta(seconds=max_interval)  # 两条消息间的最大间隔时间
            if self.min_interval > self.max_interval:
                raise ValueError("最小间隔不应大于最大间隔")
        else:
            self.max_interval = None

        self.log = logger.bind(scheme="telemessager", name=self.name, username=username)
        self.timeline: List[MessagePlan] = []  # 消息计划序列

    def parse_message_yaml(self, file):
        with open(file, "r") as f:
            data = yaml.safe_load(f)
        schema = Schema(
            {
                "messages": [str],
                Optional("at"): [str],
                Optional("days"): int,
                Optional("possibility"): float,
                Optional("only"): str,
            }
        )
        schema.validate(data)
        at = data.get("at", ("10:00", "23:00"))
        assert len(at) == 2
        at = [parser.parse(t).time() for t in at]
        return MessageSchedule(
            messages=data.get("messages"),
            at=at,
            days=data.get("days", 0),
            possibility=data.get("possibility", 1.0),
            only=data.get("only", None),
        )

    def add(self, schedule: MessageSchedule):
        for _ in range(600):
            plan = schedule.roll()
            for p in self.timeline:
                if time_in_range(p.at - self.min_interval, p.at + self.min_interval, plan.at):
                    break
            else:
                if self.max_interval:
                    if self.timeline:
                        for p in self.timeline:
                            if time_in_range(p.at - self.max_interval, p.at + self.max_interval, plan.at):
                                self.timeline.append(plan)
                                return
                    else:
                        now = datetime.now()
                        if time_in_range(now - self.max_interval, now + self.max_interval, plan.at):
                            self.timeline.append(plan)
                            return
                else:
                    self.timeline.append(plan)
                    return
        else:
            plan.skip = True
            self.timeline.append(plan)
            return

    async def get_spec_path(self, spec):
        if not Path(spec).exists():
            return await get_data(self.basedir, spec, proxy=self.proxy, caller=f"{self.name}水群")
        else:
            return spec

    async def get_spec_schedule(self, spec):
        file = await self.get_spec_path(spec)
        if not file:
            self.log.warning(f'话术文件 "{spec}" 无法下载或不存在, 将被跳过.')
            return None
        try:
            return self.parse_message_yaml(file)
        except (OSError, yaml.YAMLError, SchemaError) as e:
            self.log.warning(f'话术文件 "{spec}" 错误, 将被跳过: {e}')
            show_exception(e)
            return None

    async def start(self):
        messages = self.config.get("messages", [])
        if not messages:
            messages = self.default_messages

        schedules = []
        for m in messages:
            match = re.match(r"(.*)\*\s?(\d+)", m)
            if match:
                multiply = int(match.group(2))
                spec = match.group(1).strip()
            else:
                multiply = 1
                spec = m
            schedule = await self.get_spec_schedule(spec)
            if schedule:
                schedule.multiply = multiply
                schedules.append(schedule)

        nmsgs = sum([s.multiply for s in schedules])
        self.log.info(f"共启用 {len(schedules)} 个消息规划, 发送 {nmsgs} 条消息.")
        for s in schedules:
            for _ in range(s.multiply):
                self.add(s)

        if self.timeline:
            last_valid_p = None
            while True:
                valid_p = [p for p in self.timeline if not p.skip]
                self.log.debug(f"时间线上当前有 {len(self.timeline)} 个消息计划, {len(valid_p)} 个有效.")
                self.log.debug(
                    "时间序列: " + " ".join([p.at.strftime("%H%M") for p in sorted(valid_p, key=lambda x: x.at)])
                )
                if valid_p:
                    next_valid_p = min(valid_p, key=lambda x: x.at)
                    if not next_valid_p == last_valid_p:
                        last_valid_p = next_valid_p
                        self.log.info(
                            f"下一次发送将在 [blue]{next_valid_p.at.strftime('%m-%d %H:%M:%S')}[/] 进行: {truncate_str(next_valid_p.message, 20)}."
                        )
                else:
                    self.log.info(f"下一次发送被跳过.")
                next_p = min(self.timeline, key=lambda x: x.at)
                self.log.debug(
                    f"下一次计划任务将在 [blue]{next_p.at.strftime('%m-%d %H:%M:%S')}[/] 进行 ({'跳过' if next_p.skip else '有效'})."
                )
                await asyncio.sleep((next_p.at - datetime.now()).total_seconds())
                if not next_p.skip:
                    await self._send(next_p.message)
                self.timeline.remove(next_p)
                self.add(next_p.schedule)

    async def _send(self, *args, **kw):
        try:
            return await self.send(*args, **kw)
        except OSError as e:
            self.log.info(f'出现错误: "{e}", 忽略.')
            show_exception(e)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self.nofail:
                self.log.warning(f"发生错误, 自动水群将停止.")
                show_exception(e, regular=False)
            else:
                raise

    async def prepare_send(self, message):
        return message

    async def send(self, message):
        message = await self.prepare_send(message)
        if not message:
            return
        if self.site_last_message_time:
            need_sec = random.randint(5, 10)
            while self.site_last_message_time > datetime.now() - timedelta(seconds=need_sec):
                await asyncio.sleep(1)
        async with ClientsSession([self.account], proxy=self.proxy, basedir=self.basedir) as clients:
            async for tg in clients:
                chat = await tg.get_chat(self.chat_name)
                self.log.bind(username=tg.me.name).info(f'向聊天 "{chat.name}" 发送: [gray50]{message}[/]')
                try:
                    await tg.send_message(self.chat_name, message)
                except ChatWriteForbidden as e:
                    try:
                        chat = await tg.get_chat(self.chat_name)
                        member = await chat.get_member(tg.me.id)
                        if member.status == ChatMemberStatus.RESTRICTED:
                            if member.until_date:
                                delta = member.until_date - datetime.now()
                                secs = delta.total_seconds()
                                if secs < 2592000:
                                    self.log.warning(f"发送失败: 您已被禁言 {secs} 秒.")
                                else:
                                    self.log.warning(f"发送失败: 您已被永久禁言.")
                            else:
                                self.log.warning(f"发送失败: 您已被禁言.")
                        else:
                            self.log.warning(f"发送失败: 已全员禁言.")
                    except RPCError:
                        self.log.warning(f"发送失败: {e}.")
                except RPCError as e:
                    self.log.warning(f"发送失败: {e}.")
                except KeyError as e:
                    self.log.warning(f"发送失败, 您可能已被封禁.")
                    show_exception(e)
                else:
                    async with self.site_lock:
                        self.__class__.site_last_message_time = datetime.now()
