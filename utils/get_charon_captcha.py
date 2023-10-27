import asyncio
from pathlib import Path
from tqdm import tqdm, trange
import tomli as tomllib

from embykeeper.telechecker.tele import ClientsSession
from embykeeper.utils import AsyncTyper, async_partial

app = AsyncTyper()

bot = "charontv_bot"
chat = "api_group"


@app.async_command()
async def generate(config: Path, num: int = 200, output: Path = "captchas.txt"):
    with open(config, "rb") as f:
        config = tomllib.load(f)
    proxy = config.get("proxy", None)
    async with ClientsSession(config["telegram"][:1], proxy=proxy) as clients:
        async for tg in clients:
            wr = async_partial(tg.wait_reply, bot, timeout=None)
            photos = []
            try:
                for _ in trange(num, desc="获取验证码"):
                    while True:
                        await asyncio.sleep(1)
                        msg = await wr("/cancel")
                        msg = await wr("/checkin")
                        if msg.caption and "请输入验证码" in msg.caption:
                            photos.append(msg.photo.file_id)
                            break
            finally:
                with open(output, "w+", encoding='utf-8') as f:
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
                async with tg.catch_reply(chat) as f:
                    await tg.send_photo(chat, photo)
                    labelmsg = await asyncio.wait_for(f, None)
                if not len(labelmsg.text) == 6:
                    continue
                else:
                    tasks.append(
                        asyncio.create_task(tg.download_media(photo, f"data/{labelmsg.text.lower()}.png"))
                    )
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    app()
