from pathlib import Path
from datetime import datetime, timedelta
import re
import sys

import typer
import asyncio
from appdirs import user_data_dir
from dateutil import parser

from . import __author__, __name__, __url__, __version__
from .utils import Flagged, FlagValueCommand, AsyncTyper, AsyncTaskPool
from .settings import prepare_config

app = AsyncTyper(
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version(version):
    if version:
        print(__version__)
        raise typer.Exit()


@app.async_command(
    cls=FlagValueCommand, help=f"欢迎使用 [orange3]{__name__.capitalize()}[/] {__version__} :cinema: 无参数默认开启全部功能."
)
async def main(
    config: Path = typer.Argument(
        None,
        dir_okay=False,
        allow_dash=True,
        rich_help_panel="参数",
        help="配置文件 (置空以生成)",
    ),
    checkin: str = typer.Option(
        Flagged("", "<10:00AM,9:00PM>"),
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
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        rich_help_panel="调试参数",
        callback=version,
        is_eager=True,
        help=f"打印 {__name__.capitalize()} 版本",
    ),
    instant: bool = typer.Option(
        True, "--instant/--no-instant", "-i/-I", rich_help_panel="调试参数", help="立刻执行一次任务"
    ),
    once: bool = typer.Option(False, "--once/--cron", "-o/-O", rich_help_panel="调试参数", help="仅执行一次任务而不计划执行"),
    debug: bool = typer.Option(
        False, "--debug", "-d", envvar="EK_DEBUG", show_envvar=False, rich_help_panel="调试参数", help="开启调试模式"
    ),
    debug_cron: bool = typer.Option(
        False, hidden=True, envvar="EK_DEBUG_CRON", show_envvar=False, help="开启任务调试模式, 在三秒后立刻开始执行计划任务"
    ),
    simple_log: bool = typer.Option(False, "--simple-log", "-L", help="简化日志输出格式"),
    follow: bool = typer.Option(False, "--follow", "-f", rich_help_panel="调试参数", help="仅启动消息调试"),
    analyze: bool = typer.Option(False, "--analyze", "-a", rich_help_panel="调试参数", help="仅启动历史信息分析"),
    public: bool = typer.Option(False, rich_help_panel="调试参数", help="启用公共仓库部署模式"),
    basedir: Path = typer.Option(None, rich_help_panel="调试参数", help="设定输出文件位置"),
):
    from .log import logger, initialize

    initialize(
        level="DEBUG" if debug else "INFO", show_path=debug and (not simple_log), show_time=not simple_log
    )

    config: dict = prepare_config(config, public=public)

    if debug:
        config["nofail"] = False
        logger.warning("您当前处于调试模式, 错误将会导致程序停止运行.")
    if debug_cron:
        logger.warning("您当前处于计划任务调试模式, 将在 3 秒后运行计划任务.")

    if emby < 0:
        emby = -emby

    if not checkin and not monitor and not emby and not send:
        checkin = "<5:00PM,8:00PM>"
        emby = 7
        monitor = True
        send = True

    msg = " 您可以通过 Ctrl+C 以结束运行." if not public else ""
    logger.info(f"欢迎使用 [orange3]{__name__.capitalize()}[/]! 正在启动, 请稍等.{msg}")
    logger.info(f'当前版本 ({__version__}) 活跃贡献者: {", ".join(__author__)}.')
    logger.debug(f'命令行参数: "{" ".join(sys.argv[1:])}".')

    basedir = Path(basedir or user_data_dir(__name__))
    basedir.mkdir(parents=True, exist_ok=True)
    config["basedir"] = basedir
    try:
        session_dir_spec = Path("~") / basedir.relative_to(Path.home())
    except ValueError:
        session_dir_spec = basedir
    if not basedir == Path("/app"):
        logger.info(f'您的 Telegram 会话将存储至 "{session_dir_spec}", 请注意保管.')

    from .embywatcher.main import watcher, watcher_schedule
    from .telechecker.main import (
        analyzer,
        checkiner,
        checkiner_schedule,
        follower,
        messager,
        monitorer,
        notifier,
    )

    if follow:
        return await follower(config)

    if analyze:
        indent = " " * 23
        chats = typer.prompt(indent + "请输入群组用户名 (以空格分隔)").split()
        keywords = typer.prompt(indent + "请输入关键词 (以空格分隔)", default="", show_default=False)
        keywords = keywords.split() if keywords else []
        timerange = typer.prompt(indent + '请输入时间范围 (以"-"分割)', default="", show_default=False)
        timerange = timerange.split("-") if timerange else []
        limit = typer.prompt(indent + "请输入各群组最大获取数量", default=1000, type=int)
        return await analyzer(config, chats, keywords, timerange, limit)

    if instant and not debug_cron:
        instants = []
        if emby:
            instants.append(watcher(config))
        if checkin:
            instants.append(checkiner(config, instant=True))
        await asyncio.gather(*instants)
        logger.debug("启动时立刻执行签到和保活: 已完成.")

    if not once:
        await notifier(config)
        pool = AsyncTaskPool()
        debug_time = datetime.now() + timedelta(seconds=3) if debug_cron else None
        if emby:
            pool.add(watcher_schedule(config, 1 if debug_cron else emby))
        if checkin:
            if debug_time:
                start_time = end_time = debug_time.time()
            else:
                checkin_range_match = re.match(r"<\s*(.*),\s*(.*)\s*>", checkin)
                if checkin_range_match:
                    start_time, end_time = [parser.parse(checkin_range_match.group(i)).time() for i in (1, 2)]
                else:
                    start_time = end_time = parser.parse(checkin).time()
            pool.add(checkiner_schedule(config, instant=debug_cron, start_time=start_time, end_time=end_time))
        if monitor:
            pool.add(monitorer(config))
        if send:
            pool.add(messager(config))

        async for t in pool.as_completed():
            msg = f"任务 {t.get_name()} "
            try:
                e = t.exception()
                if e:
                    msg += f"发生错误并退出: {e}"
                else:
                    msg += f"成功结束."
            except asyncio.CancelledError:
                msg += f"被取消."
            logger.debug(msg)
            try:
                await t
            except Exception as e:
                if debug:
                    raise
                else:
                    logger.opt(exception=e).error("出现错误, 模块可能停止运行:")


if __name__ == "__main__":
    app()
