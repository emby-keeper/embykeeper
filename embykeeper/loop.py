import asyncio

from loguru import logger

from . import __url__, __name__

loop = asyncio.new_event_loop()
stopped = asyncio.Event()


def cancel_all_tasks():
    to_cancel = asyncio.all_tasks(loop)
    if not to_cancel:
        return
    for task in to_cancel:
        task.cancel()
    loop.run_until_complete(asyncio.gather(*to_cancel, loop=loop, return_exceptions=True))
    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "停止时出现错误",
                    "exception": task.exception(),
                    "task": task,
                }
            )


def stop():
    logger.info("所有客户端已停止, 欢迎您再次使用 Embykeeper.")
    try:
        cancel_all_tasks()
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        asyncio.set_event_loop(None)
        loop.close()


def show_error(e):
    logger.opt(exception=e).critical(
        f'发生错误, {__name__.capitalize()} 将退出, 请在 "{__url__}/issues/new" 提供反馈以帮助作者修复该问题:'
    )


def exception_handler(l, context):
    e = context.get("exception", None)
    if not stopped.is_set():
        if isinstance(e, Exception):
            stopped.set()
            show_error(e)
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            asyncio.ensure_future(asyncio.gather(*tasks, return_exceptions=True))
            asyncio.ensure_future(stop())
            return
    loop.default_exception_handler(context)


def run_coros(coros):
    try:
        return loop.run_until_complete(asyncio.gather(*coros))
    except Exception as e:
        loop.call_exception_handler({"exception": e})


loop.set_exception_handler(exception_handler)
asyncio.set_event_loop(loop)
