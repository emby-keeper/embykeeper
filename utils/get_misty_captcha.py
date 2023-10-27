import asyncio
from pathlib import Path
from tqdm import tqdm, trange
import tomli as tomllib

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
            while True:
                if msg.caption and "选择您要使用的功能" in msg.caption:
                    msg = await wr("🌏切换服务器")
                    if "选择您要使用的服务器" in msg.text:
                        msg = await wr("✨Misty")
                        if "选择您要使用的功能" in msg.caption:
                            msg = await wr("⚡️账号功能")
                if msg.text and "请选择功能" in msg.text:
                    break
            photos = []
            try:
                for _ in trange(num, desc="获取验证码"):
                    while True:
                        msg = await wr("⚡️注册账号")
                        if msg.text:
                            continue
                        if msg.caption and "请输入验证码" in msg.caption:
                            photos.append(msg.photo.file_id)
                            break
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
                        asyncio.create_task(tg.download_media(photo, f"data/{labelmsg.text.lower()}.png"))
                    )
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    app()
