from pathlib import Path
from ddddocr import DdddOcr

from embykeeper.utils import AsyncTyper

app = AsyncTyper()


@app.async_command()
async def main(image: Path, beta: bool = False):
    ocr = DdddOcr(beta=beta, show_ad=False)
    with open(image, "rb") as f:
        image = f.read()

    print(ocr.classification(image))


if __name__ == "__main__":
    app()
