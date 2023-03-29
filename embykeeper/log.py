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

    if scheme in ("telegram", "telechecker", "telemonitor", "telemessager", "telelink"):
        username = ifextra("username", " ([cyan]{}[/])")
        name = ifextra("name", "([magenta]{}[/]) ")
        return f"[blue]{scheme.capitalize()}[/]{username}: {name}{{message}}"
    elif scheme == "embywatcher":
        ident = ifextra(["server", "username"], " ([cyan]{}:{}[/])")
        return f"[blue]Embywatcher[/]{ident}: {{message}}"
    else:
        return "{message}"


def initialize(level="INFO"):
    logger.remove()
    logger.add(
        RichHandler(
            console=Console(stderr=True), markup=True, rich_tracebacks=True, tracebacks_suppress=[asyncio]
        ),
        format=formatter,
        level=level,
    )
