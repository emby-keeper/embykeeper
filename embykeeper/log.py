from logging import Formatter
from loguru import logger
from rich.logging import Console, RichHandler
import asyncio

from .utils import to_iterable


def formatter(record):
    extra = record["extra"]
    scheme = extra.get("scheme", None)

    def ifextra(keys, pattern="{}"):
        keys = to_iterable(keys)
        if all(k in extra for k in keys):
            return pattern.format(*[f"{{extra[{k}]}}" for k in keys])
        else:
            return ""

    scheme_names = {
        "telegram": "Telegram",
        "telechecker": "每日签到",
        "telemonitor": "消息监控",
        "telemessager": "定时水群",
        "telelink": "账号服务",
        "embywatcher": "Emby 保活",
    }

    if scheme in ("telegram", "telechecker", "telemonitor", "telemessager", "telelink"):
        username = ifextra("username", " ([cyan]{}[/])")
        name = ifextra("name", "([magenta]{}[/]) ")
        return f"[blue]{scheme_names[scheme]}[/]{username}: {name}{{message}}"
    elif scheme == "embywatcher":
        ident = ifextra(["server", "username"], " ([cyan]{}:{}[/])")
        return f"[blue]{scheme_names[scheme]}[/]{ident}: {{message}}"
    else:
        return "{message}"


def initialize(level="INFO"):
    logger.remove()
    handler = RichHandler(
        console=Console(stderr=True), markup=True, rich_tracebacks=True, tracebacks_suppress=[asyncio]
    )
    handler.setFormatter(Formatter(None, "[%m/%d %H:%M]"))
    logger.add(handler, format=formatter, level=level)
