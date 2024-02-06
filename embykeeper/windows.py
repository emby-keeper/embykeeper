import os
import platform
import sys
import time
from msvcrt import getch
from pathlib import Path
from subprocess import Popen

from appdirs import user_data_dir
from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.table import Table

from . import __name__ as __product__
from . import var
from .cli import app as cli
from .settings import write_faked_config


def generate_config(config: Path):
    if config.exists():
        return False
    write_faked_config(config, quiet=True)
    message = Table.grid(padding=2)
    message.add_column()
    urls = Table.grid(padding=2)
    urls.add_column(style="green", justify="right")
    urls.add_column(no_wrap=True)
    urls.add_row("配置教程", "https://github.com/embykeeper/embykeeper/wiki/配置文件")
    message.add_row("您需要在即将打开的文件中进行账户配置, 您可以根据注释提示进行配置.")
    message.add_row("您也可以参考 Wiki, 链接如下:")
    message.add_row(urls)
    message.add_row(Align("请按任意键以打开模板配置文件", align="center", style="bold blink underline"))
    var.console.print(
        Panel.fit(
            message,
            box=box.ROUNDED,
            padding=(1, 2),
            title="[b red]欢迎您使用 Embykeeper!",
            border_style="bright_blue",
        ),
        justify="center",
    )

    _ = getch()

    p = Popen(["start", config], shell=True)

    if not p:
        var.console.print(f"配置文件打开失败, 请按任意键退出", justify="center")
        _ = getch()
        sys.exit(1)

    var.console.print(f"等待您编辑配置文件, 请保存关闭编辑器窗口以继续 ...", justify="center")
    p.wait()
    var.console.print(
        f"请确认您配置完成, 并按任意键以继续启动 {__product__.capitalize()}...", justify="center"
    )
    var.console.print(f"配置完成, 即将启动 {__product__.capitalize()} ...", justify="center")


def main():
    config = Path(user_data_dir(__product__)) / "config.toml"
    config.parent.mkdir(exist_ok=True, parents=True)
    generate_config(config)
    os.system("cls")
    var.console.rule("Embykeeper")
    cli(["-W"])


if __name__ == "__main__":
    if not platform.system() == "Windows":
        raise RuntimeError("this entrypoint is only for windows")
    main()
