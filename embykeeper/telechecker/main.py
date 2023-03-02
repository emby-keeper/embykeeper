import asyncio
import re
from contextlib import asynccontextmanager, suppress
from functools import partial
from typing import List

from loguru import logger
from pyrogram.enums import ChatType
from pyrogram.errors import BadRequest
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from rich import box
from rich.live import Live
from rich.table import Column, Table
from rich.text import Text

from .. import __name__, __version__
from . import *
from .tele import Client

logger = logger.bind(scheme="telechecker")

CHECKINERS = (
    JMSCheckin,
    TerminusCheckin,
    JMSIPTVCheckin,
    LJYYCheckin,
    PeachCheckin,
    NebulaCheckin,
)


@asynccontextmanager
async def login(config):
    clients: List[Client] = []
    for account in config.get("telegram", []):
        clients.append(
            Client(
                app_version=f"{__name__.capitalize()} {__version__}",
                name=account["phone"],
                api_id=account["api_id"],
                api_hash=account["api_hash"],
                phone_number=account["phone"],
                proxy=config.get("proxy", None),
                lang_code="zh",
            )
        )
    for client in clients:
        logger.info(f'登录账号 "{client.phone_number}".')
        try:
            await client.start()
        except BadRequest as e:
            logger.error(f'登录账号 "{client.phone_number}" 失败 ({e.MESSAGE}), 将被跳过.')
    yield clients
    for client in clients:
        try:
            await client.stop()
        except ConnectionError:
            pass


async def dump_message(client: Client, message: Message, table: Table):
    text = message.text or message.caption
    if text:
        text = text.replace("\n", " ")
        if not text:
            return
    else:
        return
    if message.from_user:
        user = message.from_user
        sender_id = str(user.id)
        sender_icon = "👤"
        if message.outgoing:
            sender = Text("Me", style="bold red")
            text = Text(text, style="red")
        else:
            sender = user.first_name.strip()
            if user.is_bot:
                sender_icon = "🤖"
                sender = Text(sender, style="bold yellow")
    else:
        sender = sender_id = sender_icon = None

    chat_id = "{: }".format(message.chat.id)
    if message.chat.type == ChatType.GROUP or message.chat.type == ChatType.SUPERGROUP:
        chat = message.chat.title
        chat_icon = "👥"
    elif message.chat.type == ChatType.CHANNEL:
        chat = message.chat.title
        chat_icon = "📢"
    elif message.chat.type == ChatType.BOT:
        chat = None
        chat_icon = "🤖"
    else:
        chat = chat_icon = None
    return table.add_row(
        client.me.first_name,
        "│",
        chat_icon,
        chat,
        chat_id,
        "│",
        sender_icon,
        sender,
        sender_id,
        "│",
        text,
    )


async def main(config, follow=False):
    if not follow:
        async with login(config) as clients:
            for tg in clients:
                checkiners = [
                    cls(
                        tg,
                        retries=config.get("retries", 10),
                        timeout=config.get("timeout", 240),
                    )
                    for cls in CHECKINERS
                ]
                tasks = [asyncio.create_task(c.checkin()) for c in checkiners]
                results = await asyncio.gather(*tasks)
                failed = [c for i, c in enumerate(checkiners) if not results[i]]
                if failed:
                    logger.bind(username=tg.me.first_name).error(
                        f"签到失败 ({len(failed)}/{len(checkiners)}): {','.join([f.name for f in failed])}"
                    )
        logger.info("执行完成.")
    else:
        columns = [
            Column("用户", style="cyan", justify="center"),
            Column("", max_width=1, style="white"),
            Column("", max_width=2, overflow="crop"),
            Column(
                "会话", style="bright_blue", no_wrap=True, justify="right", max_width=15
            ),
            Column("(ChatID)", style="gray50", min_width=14, max_width=20),
            Column("", max_width=1, style="white"),
            Column("", max_width=2, overflow="crop"),
            Column("发信人", style="green", no_wrap=True, max_width=15, justify="right"),
            Column("(UserID)", style="gray50", min_width=10, max_width=15),
            Column("", max_width=1, style="white"),
            Column("信息", no_wrap=True, min_width=40, max_width=60),
        ]
        table = Table(*columns, header_style="bold magenta", box=box.SIMPLE)
        async with login(config) as clients:
            for tg in clients:
                tg.add_handler(MessageHandler(partial(dump_message, table=table)))
            with Live(table, refresh_per_second=4, vertical_overflow="visible"):
                await asyncio.Event().wait()
