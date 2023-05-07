from pathlib import Path
import csv

import tomli as tomllib
from rich import box
from rich.table import Column, Table
from rich.live import Live

from embykeeper.telechecker.monitor.pornemby import PornembyMonitor
from embykeeper.telechecker.tele import ClientsSession
from embykeeper.utils import AsyncTyper, to_iterable

app = AsyncTyper()

columns = [
    Column("题目", style="bright_blue", no_wrap=True, max_width=40),
    Column("A", style="gray50", no_wrap=True, max_width=10),
    Column("B", style="gray50", no_wrap=True, max_width=10),
    Column("C", style="gray50", no_wrap=True, max_width=10),
    Column("D", style="gray50", no_wrap=True, max_width=10),
    Column("答案", style="green", min_width=5, max_width=10),
]


@app.async_command()
async def main(config: Path, output: Path = "questions.csv"):
    with open(config, "rb") as f:
        config = tomllib.load(f)
    proxy = config.get("proxy", None)
    async with ClientsSession(config["telegram"][:1], proxy=proxy) as clients:
        async for tg in clients:
            monitor = PornembyMonitor.PornembyAnswerMonitor(tg)
            monitor.chat_name = "PornembyFun"
            monitor.chat_keyword = r"问题\d+：(.*?)\n+A:(.*)\n+B:(.*)\n+C:(.*)\n+D:(.*)\n+答案为：([ABCD])"
            table = Table(*columns, header_style="bold magenta", box=box.SIMPLE)
            with Live(table, refresh_per_second=4, vertical_overflow="visible"):
                write_header = not output.exists()
                with open(output, mode="a+", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    if write_header:
                        writer.writerow(["Question", "A", "B", "C", "D", "Answer"])
                    for c in to_iterable(monitor.chat_name):
                        count = 0
                        finished = False
                        while not finished:
                            finished = True
                            async for m in tg.get_chat_history(c, limit=100, offset=count):
                                count += 1
                                finished = False
                                if m.text:
                                    for key in monitor.keys(m):
                                        table.add_row(*key)
                                        writer.writerow(key)


if __name__ == "__main__":
    app()
