import asyncio
from pathlib import Path
from textwrap import dedent

from loguru import logger
import tomli as tomllib
from pyrogram import filters
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from embykeeper.utils import AsyncTyper
from embykeeper.telechecker.tele import Client, API_KEY

app = AsyncTyper()
app_config = {}

async def dump(client: Client, message: Message):
    if message.text:
        logger.debug(f"<- {message.text}")


async def checkin(client: Client, message: Message):
    url = app_config['url']
    await client.send_message(
        message.chat.id,
        f"请打开并复制网页的内容, 粘贴回复: [{url}]({url})",
        parse_mode=ParseMode.MARKDOWN,
    )

@app.async_command()
async def main(config: Path, url: str):
    with open(config, "rb") as f:
        app_config.update(tomllib.load(f))
    app_config["url"] = url
    for k in API_KEY.values():
        api_id = k["api_id"]
        api_hash = k["api_hash"]
    bot = Client(
        name="test_bot",
        bot_token=app_config["bot"]["token"],
        proxy=app_config.get("proxy", None),
        workdir=Path(__file__).parent,
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    )
    async with bot:
        await bot.add_handler(MessageHandler(dump), group=1)
        await bot.add_handler(MessageHandler(checkin, filters.command("checkin")))
        logger.info(f"Started listening for commands: @{bot.me.username}.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    app()
