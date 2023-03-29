from pathlib import Path
from datetime import datetime

import tomli as tomllib
import typer
import asyncio
from appdirs import user_data_dir
from rich import traceback
from schedule import Scheduler
from dateutil import parser

traceback.install()

from . import __author__, __name__, __url__, __version__
from .utils import Flagged, FlagValueCommand
from .settings import prepare_config
from .loop import loop, run_coros
from .log import logger

app = typer.Typer(
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def run_pending_async(scheduler: Scheduler):
    async def coro():
        while True:
            scheduler.run_pending()
            await asyncio.sleep(1)

    return coro()


def version(version):
    if version:
        print(__version__)
        raise typer.Exit()


@app.command(
    cls=FlagValueCommand, help=f"欢迎使用 [orange3]{__name__.capitalize()}[/] {__version__} :cinema: 无参数默认开启全部功能."
)
def main(
    config: Path = typer.Argument(
        None,
        envvar=f"{__name__.upper()}_CONFIG",
        dir_okay=False,
        allow_dash=True,
        rich_help_panel="参数",
        help="配置文件 (置空以生成)",
    ),
    checkin: str = typer.Option(
        Flagged("", "6:00PM"),
        "--checkin",
        "-c",
        rich_help_panel="模块开关",
        show_default="不指定值时默认为6:00PM",
        help="启用每日指定时间签到",
    ),
    emby: int = typer.Option(
        Flagged(0, 7),
        "--emby",
        "-e",
        rich_help_panel="模块开关",
        help="启用每隔天数Emby自动保活",
        show_default="不指定值时默认为每7天",
    ),
    monitor: bool = typer.Option(False, "--monitor", "-m", rich_help_panel="模块开关", help="启用群聊监视"),
    send: bool = typer.Option(False, "--send", "-s", rich_help_panel="模块开关", help="启用自动水群"),
    instant: bool = typer.Option(
        True, "--instant/--no-instant", "-i/-I", rich_help_panel="调试参数", help="立刻执行一次计划任务"
    ),
    debug: bool = typer.Option(False, "--debug", "-d", rich_help_panel="调试参数", help="开启调试模式, 错误将会导致程序停止运行"),
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        rich_help_panel="调试参数",
        callback=version,
        is_eager=True,
        help=f"打印 {__name__.capitalize()} 版本",
    ),
    follow: bool = typer.Option(False, "--follow", "-f", rich_help_panel="调试参数", help="仅启动消息调试"),
    analyze: bool = typer.Option(False, "--analyze", "-a", rich_help_panel="调试参数", help="仅启动历史信息分析"),
):
    try:
        config = prepare_config(config)
    except tomllib.TOMLDecodeError as e:
        logger.error(f"TOML 配置文件错误: {e}.")
        raise typer.Exit(1)
    if not config:
        raise typer.Exit(1)
    if debug:
        config.setdefault("nofail", False)
        logger.warning("您当前处于调试模式, 错误将会导致程序停止运行.")
    if emby < 0:
        emby = -emby
    if not checkin and not monitor and not emby and not send:
        checkin = "08:00"
        emby = 7
        monitor = True
        send = True

    logger.info(f"欢迎使用 [orange3]{__name__.capitalize()}[/]! 正在启动, 请稍等. 您可以通过 Ctrl+C 以结束运行.")
    logger.info(f'当前版本 ({__version__}) 活跃贡献者: {", ".join(__author__)}.')
    session_dir = Path(user_data_dir(__name__))
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir_spec = Path("~") / session_dir.relative_to(Path.home())
    logger.info(f'您的 Telegram 会话将存储至 "{session_dir_spec}", 请注意保管.')

    from .embywatcher.main import watcher
    from .telechecker.main import analyzer, checkiner, follower, messager, monitorer, notifier

    if follow:
        return asyncio.run(follower(config))
    if analyze:
        indent = " " * 29
        chats = typer.prompt(indent + "请输入群组用户名 (以空格分隔)").split()
        keywords = typer.prompt(indent + "请输入关键词 (以空格分隔)", default="", show_default=False)
        keywords = keywords.split() if keywords else []
        timerange = typer.prompt(indent + '请输入时间范围 (以"-"分割)', default="", show_default=False)
        timerange = timerange.split("-") if timerange else []
        limit = typer.prompt(indent + "请输入各群组最大获取数量", default=1000, type=int)
        return asyncio.run(analyzer(config, chats, keywords, timerange, limit))

    if instant:
        instants = []
        if emby:
            instants.append(watcher(config))
        if checkin:
            instants.append(checkiner(config, instant=True))
        if not run_coros(instants):
            raise typer.Exit(1)

    loop.create_task(notifier(config))

    if emby:
        schedule_emby = Scheduler()
        loop.create_task(run_pending_async(schedule_emby))
        schedule_emby.every(emby).days.at(datetime.now().strftime("%H:%M:%S")).do(
            lambda: loop.create_task(watcher(config))
        )
        logger.bind(scheme="embywatcher").info(
            f"下一次保活将在 {schedule_emby.next_run.strftime('%m-%d %H:%M %p')} 进行."
        )
    if checkin:
        schedule_checkin = Scheduler()
        loop.create_task(run_pending_async(schedule_checkin))
        checkin = parser.parse(checkin).time().strftime("%H:%M:%S")
        schedule_checkin.every().day.at(checkin).do(lambda: loop.create_task(checkiner(config)))
        logger.bind(scheme="telechecker").info(
            f"下一次签到将在 {schedule_checkin.next_run.strftime('%m-%d %H:%M %p')} 进行."
        )
    if send:
        schedule_send = Scheduler()
        loop.create_task(run_pending_async(schedule_send))
        loop.create_task(messager(config, schedule_send))
    if monitor:
        loop.create_task(monitorer(config))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\r"),
    finally:
        logger.info("所有客户端已停止, 欢迎您再次使用 Embykeeper.")

        async def exit():
            loop.stop()

        asyncio.ensure_future(exit())


if __name__ == "__main__":
    app()
