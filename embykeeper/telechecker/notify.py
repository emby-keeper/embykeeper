import logging

from loguru import logger

from ..log import formatter
from .log import TelegramStream

logger = logger.bind(scheme="telegram")


async def start_notifier(config: dict):
    """消息通知初始化函数."""

    def _filter(record):
        notify = record.get("extra", {}).get("notify", None)
        if notify or record["level"].no == logging.ERROR:
            return True
        else:
            return False

    def _formatter(record):
        notify = record.get("extra", {}).get("notify", False)
        format = formatter(record)
        if notify and notify != True:
            format = format.replace("{message}", "{extra[notify]}")
        return "{level}#" + format

    accounts = config.get("telegram", [])
    notifier = config.get("notifier", None)
    if notifier:
        try:
            if notifier == True:
                notifier = accounts[0]
            elif isinstance(notifier, int):
                notifier = accounts[notifier + 1]
            elif isinstance(notifier, str):
                for a in accounts:
                    if a["phone"] == notifier:
                        notifier = a
                        break
            else:
                notifier = None
        except IndexError:
            notifier = None
    if notifier:
        logger.info(f'计划任务的关键消息将通过 Embykeeper Bot 发送至 "{notifier["phone"]}" 账号.')
        logger.add(
            TelegramStream(
                account=notifier, proxy=config.get("proxy", None), basedir=config.get("basedir", None)
            ),
            format=_formatter,
            filter=_filter,
        )
