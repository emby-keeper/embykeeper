from logging import Formatter
import asyncio

from loguru import logger
from rich.logging import RichHandler

from . import var
from .utils import to_iterable

scheme_names = {
    "telegram": "Telegram",
    "telechecker": "每日签到",
    "telemonitor": "消息监控",
    "telemessager": "定时水群",
    "telelink": "账号服务",
    "telenotifier": "消息推送",
    "embywatcher": "Emby保活",
    "datamanager": "下载器",
    "debugtool": "开发工具",
}


def formatter(record):
    """根据日志器的 scheme 属性配置输出格式."""
    extra = record["extra"]
    scheme = extra.get("scheme", None)

    def ifextra(keys, pattern="{}"):
        keys = to_iterable(keys)
        if all(k in extra for k in keys):
            return pattern.format(*[f"{{extra[{k}]}}" for k in keys])
        else:
            return ""

    if scheme in ("telegram", "telechecker", "telemonitor", "telemessager", "telelink"):
        username = ifextra("username", " ([cyan]{}[/])")
        name = ifextra("name", "([magenta]{}[/]) ")
        return f"[blue]{scheme_names[scheme]}[/]{username}: {name}{{message}}"
    elif scheme == "embywatcher":
        ident = ifextra(["server", "username"], " ([cyan]{}:{}[/])")
        return f"[blue]{scheme_names[scheme]}[/]{ident}: {{message}}"
    elif scheme == "datamanager":
        return f"[blue]{scheme_names[scheme]}[/]: {{message}}"
    else:
        return "{message}"


def initialize(level="INFO", **kw):
    """初始化日志配置."""
    logger.remove()
    handler = RichHandler(
        console=var.console, markup=True, rich_tracebacks=True, tracebacks_suppress=[asyncio], **kw
    )
    handler.setFormatter(Formatter(None, "[%m/%d %H:%M]"))
    logger.add(handler, format=formatter, level=level, colorize=False)
