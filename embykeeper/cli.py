from pathlib import Path
from datetime import datetime, timedelta
import re
import sys
from typing import List

import typer
import asyncio
from dateutil import parser

from . import var, __author__, __name__, __url__, __version__
from .utils import Flagged, FlagValueCommand, AsyncTyper, AsyncTaskPool, show_exception
from .settings import prepare_config

app = AsyncTyper(
    pretty_exceptions_enable=False,
    rich_markup_mode="rich",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version(flag):
    if flag:
        print(__version__)
        raise typer.Exit()


def print_example_config(flag):
    if flag:
        import io

        from .settings import write_faked_config

        file = io.StringIO()
        write_faked_config(file, quiet=True)
        file.seek(0)
        print(file.read())
        raise typer.Exit()


@app.async_command(
    cls=FlagValueCommand,
    help=f"欢迎使用 [orange3]{__name__.capitalize()}[/] {__version__} :cinema: 无参数默认开启全部功能.",
)
async def main(
    config: Path = typer.Argument(
        None,
        dir_okay=False,
        allow_dash=True,
        envvar=f"EK_CONFIG_FILE",
        rich_help_panel="参数",
        help="配置文件 (置空以生成)",
    ),
    checkin: str = typer.Option(
        Flagged("", "-"),
        "--checkin",
        "-c",
        rich_help_panel="模块开关",
        show_default="不指定值时默认为8:00AM-10:00AM之间随机时间",
        help="启用每日指定时间签到",
    ),
    emby: int = typer.Option(
        Flagged(0, 10000),
        "--emby",
        "-e",
        rich_help_panel="模块开关",
        help="启用每隔天数Emby自动保活",
        show_default="不指定值时默认为每3天",
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
    example_config: bool = typer.Option(
        None,
        "--example-config",
        "-E",
        hidden=True,
        callback=print_example_config,
        is_eager=True,
        help=f"输出范例配置文件",
    ),
    instant: bool = typer.Option(
        True,
        "--instant/--no-instant",
        "-i/-I",
        envvar="EK_INSTANT",
        show_envvar=False,
        rich_help_panel="调试参数",
        help="立刻执行一次任务",
    ),
    once: bool = typer.Option(
        False, "--once/--cron", "-o/-O", rich_help_panel="调试参数", help="仅执行一次任务而不计划执行"
    ),
    verbosity: int = typer.Option(
        False,
        "--debug",
        "-d",
        count=True,
        envvar="EK_DEBUG",
        show_envvar=False,
        rich_help_panel="调试参数",
        help="开启调试模式",
    ),
    debug_cron: bool = typer.Option(
        False,
        hidden=True,
        envvar="EK_DEBUG_CRON",
        show_envvar=False,
        help="开启任务调试模式, 在三秒后立刻开始执行计划任务",
    ),
    simple_log: bool = typer.Option(
        False, "--simple-log", "-L", rich_help_panel="调试参数", help="简化日志输出格式"
    ),
    disable_color: bool = typer.Option(
        False, "--disable-color", "-C", rich_help_panel="调试参数", help="禁用日志颜色"
    ),
    follow: bool = typer.Option(False, "--follow", "-F", rich_help_panel="调试工具", help="仅启动消息调试"),
    analyze: bool = typer.Option(
        False, "--analyze", "-A", rich_help_panel="调试工具", help="仅启动历史信息分析"
    ),
    dump: List[str] = typer.Option([], "--dump", "-D", rich_help_panel="调试工具", help="仅启动更新日志"),
    save: bool = typer.Option(
        False, "--save", "-S", rich_help_panel="调试参数", help="记录执行过程中的原始更新日志"
    ),
    public: bool = typer.Option(
        False, "--public", "-P", hidden=True, rich_help_panel="调试参数", help="启用公共仓库部署模式"
    ),
    windows: bool = typer.Option(
        False, "--windows", "-W", hidden=True, rich_help_panel="调试参数", help="启用 Windows 安装部署模式"
    ),
    basedir: Path = typer.Option(
        None, "--basedir", "-B", rich_help_panel="调试参数", help="设定账号文件和模型文件的位置"
    ),
):
    from .log import logger, initialize

    var.debug = verbosity
    if verbosity >= 1:
        level = "DEBUG"
    else:
        level = "INFO"

    initialize(level=level, show_path=verbosity and (not simple_log), show_time=not simple_log)
    if disable_color:
        var.console.no_color = True

    msg = " 您可以通过 Ctrl+C 以结束运行." if not public else ""
    logger.info(f"欢迎使用 [orange3]{__name__.capitalize()}[/]! 正在启动, 请稍等.{msg}")
    logger.info(f'当前版本 ({__version__}) 活跃贡献者: {", ".join(__author__)}.')
    logger.debug(f'命令行参数: "{" ".join(sys.argv[1:])}".')

    if verbosity:
        logger.warning(f"您当前处于调试模式: 日志等级 {verbosity}.")
        app.pretty_exceptions_enable = True

    config: dict = await prepare_config(config, basedir=basedir, public=public, windows=windows)

    if verbosity >= 2:
        config["nofail"] = False
    if not config.get("nofail", True):
        logger.warning(f"您当前处于调试模式: 错误将会导致程序停止运行.")
    if debug_cron:
        logger.warning("您当前处于计划任务调试模式, 将在 10 秒后运行计划任务.")

    default_time = config.get("time", "<8:00AM,10:00AM>")
    default_interval = config.get("interval", 3)
    logger.debug(f"采用默认签到时间范围 {default_time}, 默认保活间隔天数 {default_interval}.")

    if checkin == "-":
        checkin = default_time

    if emby == 10000:
        emby = default_interval

    if not checkin and not monitor and not emby and not send:
        checkin = default_time
        emby = default_interval
        monitor = True
        send = True

    if emby < 0:
        emby = -emby

    if follow:
        from .telechecker.debug import follower

        return await follower(config)

    if analyze:
        from .telechecker.debug import analyzer

        indent = " " * 23
        chats = typer.prompt(indent + "请输入群组用户名 (以空格分隔)").split()
        keywords = typer.prompt(indent + "请输入关键词 (以空格分隔)", default="", show_default=False)
        keywords = keywords.split() if keywords else []
        timerange = typer.prompt(indent + '请输入时间范围 (以"-"分割)', default="", show_default=False)
        timerange = timerange.split("-") if timerange else []
        limit = typer.prompt(indent + "请输入各群组最大获取数量", default=10000, type=int)
        outputs = typer.prompt(indent + "请输入最大输出数量", default=1000, type=int)
        return await analyzer(config, chats, keywords, timerange, limit, outputs)

    if dump:
        from .telechecker.debug import dumper

        return await dumper(config, dump)

    from .embywatcher.main import (
        watcher,
        watcher_schedule,
        watcher_continuous_schedule,
    )
    from .telechecker.main import (
        checkiner,
        checkiner_schedule,
        messager,
        monitorer,
        start_notifier,
    )

    pool = AsyncTaskPool()

    if save:
        from .telechecker.debug import saver

        asyncio.create_task(saver(config))

    if instant and not debug_cron:
        if emby:
            pool.add(watcher(config))
        if checkin:
            pool.add(checkiner(config, instant=True))
        await pool.wait()
        logger.debug("启动时立刻执行签到和保活: 已完成.")

    if not once:
        await start_notifier(config)
        if emby:
            if debug_cron:
                start_time = end_time = (datetime.now() + timedelta(seconds=10)).time()
                pool.add(
                    watcher_schedule(config, start_time=start_time, end_time=end_time, days=0, debug=True)
                )
            else:
                pool.add(watcher_schedule(config, days=emby))
            for a in config.get("emby", ()):
                if a.get("continuous", False):
                    pool.add(watcher_continuous_schedule(config))
                    break
        if checkin:
            if debug_cron:
                start_time = end_time = (datetime.now() + timedelta(seconds=10)).time()
            else:
                checkin_range_match = re.match(r"<\s*(.*),\s*(.*)\s*>", checkin)
                if checkin_range_match:
                    start_time, end_time = [parser.parse(checkin_range_match.group(i)).time() for i in (1, 2)]
                else:
                    start_time = end_time = parser.parse(checkin).time()
            pool.add(
                checkiner_schedule(
                    config,
                    instant=debug_cron,
                    start_time=start_time,
                    end_time=end_time,
                    days=1,
                )
            )
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
                logger.error("出现错误, 模块可能停止运行.")
                show_exception(e, regular=False)
                if not config.get("nofail", True):
                    raise


if __name__ == "__main__":
    app()
