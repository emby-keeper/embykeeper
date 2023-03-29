import asyncio

from loguru import logger

from . import __url__, __name__

loop = asyncio.new_event_loop()
stopped = asyncio.Event()


def show_error(e):
    logger.opt(exception=e).critical(
        f'发生错误, {__name__.capitalize()} 将退出, 请在 "{__url__}/issues/new" 提供反馈以帮助作者修复该问题:'
    )


def exception_handler(l, context):
    async def exit():
        loop.stop()

    e = context.get("exception", None)
    if not stopped.is_set():
        if isinstance(e, Exception):
            stopped.set()
            show_error(e)
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                task.cancel()
            asyncio.ensure_future(asyncio.gather(*tasks, return_exceptions=True))
            asyncio.ensure_future(exit())
        elif isinstance(e, asyncio.CancelledError):
            logger.debug(f"异步循环警告: {context.get('message', '')}")


def run_coros(coros):
    try:
        loop.run_until_complete(asyncio.gather(*coros))
        return True
    except Exception as e:
        show_error(e)
        return False


loop.set_exception_handler(exception_handler)
asyncio.set_event_loop(loop)
