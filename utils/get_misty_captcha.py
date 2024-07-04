import asyncio
from pathlib import Path
from tqdm import tqdm, trange
import tomli as tomllib

from loguru import logger

from embykeeper.telechecker.monitor.misty import MistyMonitor
from embykeeper.telechecker.tele import ClientsSession
from embykeeper.utils import AsyncTyper, async_partial

app = AsyncTyper()

chat = "api_group"


@app.async_command()
async def generate(config: Path, num: int = 200, output: Path = "captchas.txt"):
    with open(config, "rb") as f:
        config = tomllib.load(f)
    proxy = config.get("proxy", None)
    async with ClientsSession(config["telegram"][:1], proxy=proxy) as clients:
        async for tg in clients:
            m = MistyMonitor(tg)
            wr = async_partial(tg.wait_reply, m.bot_username, timeout=None)
            msg = await wr("/cancel")
            if msg.caption and "选择您要使用的功能" in msg.caption:
                msg = await wr("⚡️账号功能")
                if not "请选择功能" in msg.text:
                    logger.error("账号错误.")
                    return
            photos = []
            try:
                for _ in trange(num, desc="获取验证码"):
                    msg = await wr("⚡️注册账号")
                    if msg.text:
                        continue
                    if msg.caption and "请输入验证码" in msg.caption:
                        photos.append(msg.photo.file_id)
                        msg = await wr("/cancel")
                        if not "请选择功能" in msg.text:
                            logger.error("账号错误.")
                            return
            finally:
                with open(output, "w+", encoding="utf-8") as f:
                    f.writelines(str(photo) + "\n" for photo in photos)


@app.async_command()
async def label(config: Path, inp: Path = "captchas.txt"):
    with open(inp) as f:
        photos = [l.strip() for l in f.readlines()]
    with open(config, "rb") as f:
        config = tomllib.load(f)
    proxy = config.get("proxy", None)
    tasks = []
    async with ClientsSession(config["telegram"][:1], proxy=proxy) as clients:
        async for tg in clients:
            for photo in tqdm(photos, desc="标记验证码"):
                await tg.send_photo(chat, photo)
                labelmsg = await tg.wait_reply(chat, timeout=None, outgoing=True)
                if not len(labelmsg.text) == 5:
                    continue
                else:
                    tasks.append(
                        asyncio.create_task(tg.download_media(photo, f"output/{labelmsg.text.lower()}.png"))
                    )
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    app()
