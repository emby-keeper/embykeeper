import asyncio
from collections import namedtuple
from datetime import date, datetime, time, timedelta
from functools import wraps
import random
import sys
from typing import Any, Coroutine, Iterable, Union

from loguru import logger
import click
from typer import Typer
from typer.core import TyperCommand

from . import __url__, __name__

Flagged = namedtuple("Flagged", ("noflag", "flag"))


def fail_message(e):
    logger.opt(exception=e).critical(
        f"发生关键错误, {__name__.capitalize()} 将退出, 请在 '{__url__}/issues/new' 提供反馈以帮助作者修复该问题:"
    )


class AsyncTyper(Typer):
    def async_command(self, *args, **kwargs):
        def decorator(async_func):
            @wraps(async_func)
            def sync_func(*_args, **_kwargs):
                try:
                    asyncio.run(async_func(*_args, **_kwargs))
                except KeyboardInterrupt:
                    print("\r", end="", flush=True)
                    logger.info(f"所有客户端已停止, 欢迎您再次使用 {__name__.capitalize()}.")
                except Exception as e:
                    print("\r", end="", flush=True)
                    fail_message(e)
                    sys.exit(1)
                else:
                    logger.info(f"所有任务已完成, 欢迎您再次使用 {__name__.capitalize()}.")

            self.command(*args, **kwargs)(sync_func)
            return async_func

        return decorator


class FlagValueCommand(TyperCommand):
    def parse_args(self, ctx, args):
        long = {}
        short = {}
        defined = set()
        for o in self.params:
            if isinstance(o, click.Option):
                if isinstance(o.default, Flagged):
                    for pre in o.opts:
                        if pre.startswith("--"):
                            long[pre] = o
                        elif pre.startswith("-"):
                            short[pre] = o

        for i, a in enumerate(args):
            a = a.split("=")
            if a[0] in long:
                defined.add(long[a[0]])
                if len(a) == 1:
                    args[i] = f"{a[0]}={long[a[0]].default.flag}"
            elif a[0] in short:
                defined.add(short[a[0]])
                if len(args) == i + 1 or args[i + 1].startswith("-"):
                    args.insert(i + 1, str(short[a[0]].default.flag))

        for u in set(long.values()) - defined:
            for p, o in long.items():
                if o == u:
                    break
            args.append(f"{p}={u.default.noflag}")

        return super().parse_args(ctx, args)


class AsyncTaskPool:
    def __init__(self):
        self.waiter = asyncio.Condition()
        self.tasks = []

    def add(self, coro: Coroutine):
        async def wrapper():
            task = asyncio.ensure_future(coro)
            await asyncio.wait([task])
            async with self.waiter:
                self.waiter.notify()
                return await task

        t = asyncio.create_task(wrapper())
        t.set_name(coro.__name__)
        self.tasks.append(t)

    async def as_completed(self):
        while self.tasks:
            async with self.waiter:
                await self.waiter.wait()
                for t in self.tasks:
                    if t.done():
                        yield t
                        self.tasks.remove(t)


class AsyncCountPool(dict):
    def __init__(self, *args, base=1000, **kw):
        super().__init__(*args, **kw)
        self.lock = asyncio.Lock()
        self.next = base + 1

    async def append(self, value):
        async with self.lock:
            key = self.next
            self[key] = value
            self.next += 1
            return key


def to_iterable(var: Union[Iterable, Any]):
    if var is None:
        return ()
    if isinstance(var, str) or not isinstance(var, Iterable):
        return (var,)
    else:
        return var


def remove_prefix(text: str, prefix: str):
    return text[text.startswith(prefix) and len(prefix) :]


def truncate_str(text: str, length: int):
    return f"{text[:length + 3]}..." if len(text) > length else text


def time_in_range(start, end, x):
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx : min(ndx + n, l)]


def flatten(l):
    return [item for sublist in l for item in sublist]


def async_partial(f, *args1, **kw1):
    async def func(*args2, **kw2):
        return await f(*args1, *args2, **kw1, **kw2)

    return func


async def idle():
    await asyncio.Event().wait()


def random_time(start_time: time = None, end_time: time = None):
    start_datetime = datetime.combine(date.today(), start_time or time(0, 0))
    end_datetime = datetime.combine(date.today(), end_time or time(23, 59, 59))
    if end_datetime < start_datetime:
        end_datetime += timedelta(days=1)
    time_diff_seconds = (end_datetime - start_datetime).seconds
    random_seconds = random.randint(0, time_diff_seconds)
    random_time = (start_datetime + timedelta(seconds=random_seconds)).time()
    return random_time


def next_random_datetime(start_time: time = None, end_time: time = None, interval_days=1):
    min_datetime = datetime.now() + timedelta(days=interval_days)
    target_time = random_time(start_time, end_time)
    offset_date = 0
    while True:
        offset_date += 1
        t = datetime.combine(datetime.now() + timedelta(days=offset_date), target_time)
        if t >= min_datetime:
            break
    return t


def humanbytes(B: float):
    """Return the given bytes as a human friendly KB, MB, GB, or TB string."""
    B = float(B)
    KB = float(1024)
    MB = float(KB**2)  # 1,048,576
    GB = float(KB**3)  # 1,073,741,824
    TB = float(KB**4)  # 1,099,511,627,776

    if B < KB:
        return "{0} {1}".format(B, "Bytes" if 0 == B > 1 else "Byte")
    elif KB <= B < MB:
        return "{0:.2f} KB".format(B / KB)
    elif MB <= B < GB:
        return "{0:.2f} MB".format(B / MB)
    elif GB <= B < TB:
        return "{0:.2f} GB".format(B / GB)
    elif TB <= B:
        return "{0:.2f} TB".format(B / TB)
