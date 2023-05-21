from pathlib import Path
import random
from tqdm import tqdm
import tomli as tomllib

from ddddocr import DdddOcr
from PIL import Image
from pyrogram.enums import ParseMode

from embykeeper.telechecker.tele import ClientsSession
from embykeeper.utils import AsyncTyper

app = AsyncTyper()

bot = "jmsembybot"
chat = "api_group"


@app.async_command()
async def generate(config: Path, output: Path = "captchas.txt"):
    with open(config, "rb") as f:
        config = tomllib.load(f)
    proxy = config.get("proxy", None)
    async with ClientsSession(config["telegram"][:1], proxy=proxy) as clients:
        async for tg in clients:
            photos = []
            try:
                async for msg in tg.get_chat_history(bot):
                    if msg.photo:
                        photos.append(msg.photo.file_id)
            finally:
                with open(output, "a+") as f:
                    f.writelines(str(photo) + "\n" for photo in photos)


@app.async_command()
async def label(config: Path, inp: Path = "captchas.txt", onnx: Path = None, charsets: Path = None):
    ocr = DdddOcr(beta=True, show_ad=False, import_onnx_path=str(onnx), charsets_path=str(charsets))
    output = Path(__file__).parent / "data"
    output.mkdir(exist_ok=True, parents=True)
    with open(inp) as f:
        photos = [l.strip() for l in f.readlines()]
        random.shuffle(photos)
    with open(config, "rb") as f:
        config = tomllib.load(f)
    proxy = config.get("proxy", None)
    async with ClientsSession(config["telegram"][:1], proxy=proxy) as clients:
        async for tg in clients:
            for photo in tqdm(photos, desc="标记验证码"):
                data = await tg.download_media(photo, in_memory=True)
                image = Image.open(data)
                await tg.send_photo(
                    chat, photo, caption=f"`{ocr.classification(image)}`", parse_mode=ParseMode.MARKDOWN
                )
                labelmsg = await tg.wait_reply(chat, timeout=None, outgoing=True)
                if not len(labelmsg.text) == 4:
                    continue
                else:
                    image.save(output / f"{labelmsg.text}.png")


if __name__ == "__main__":
    app()
