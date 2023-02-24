import time
import uuid
from datetime import datetime
from pathlib import Path

import click
import schedule
import toml
from dateutil import parser
from faker import Faker
from faker.providers import internet, profile
from loguru import logger
from rich.logging import Console, RichHandler

from .embywatcher import main as embywatcher
from .telechecker import main as telechecker
from .utils import CommandWithOptionalFlagValues

logger.remove()
logger.add(RichHandler(console=Console(stderr=True)), format="{message}")


def _get_faked_accounts():
    fake = Faker()
    fake.add_provider(internet)
    fake.add_provider(profile)
    account = {}
    account["timeout"] = 120
    account["retries"] = 10
    account["proxy"] = {
        "host": "127.0.0.1",
        "port": "1080",
        "type": "socks5",
    }
    account["telegram"] = []
    for _ in range(2):
        account["telegram"].append(
            {
                "api_id": fake.numerify(text="########"),
                "api_hash": uuid.uuid4().hex,
                "phone": f'+861{fake.numerify(text="##########")}',
            }
        )
    account["emby"] = []
    for _ in range(2):
        account["emby"].append(
            {
                "url": fake.url(["https"]),
                "username": fake.profile()["username"],
                "password": fake.password(),
            }
        )
    return account


@click.command(cls=CommandWithOptionalFlagValues)
@click.argument("config", required=False, type=click.Path(dir_okay=False, exists=True))
@click.option(
    "--telegram",
    "-t",
    type=str,
    flag_value="08:00",
    help="每日指定时间执行Telegram bot签到",
)
@click.option(
    "--telegram-follow", is_flag=True, hidden=True, help="启动Telegram监听模式以确定ChatID"
)
@click.option("--emby", "-e", type=int, flag_value=7, help="每隔指定天数执行Emby保活")
@click.option("--instant/--no-instant", default=True, help="立刻执行一次计划任务")
@click.option("--quiet/--no-quiet", default=False, help="启用批处理模式并禁用输入, 可能导致无法输入验证码")
def cli(config, telegram, telegram_follow, emby, instant, quiet):
        with open(config) as f:
            config = toml.load(f)
        if quiet == True:
            config['quiet'] = True
        if telegram_follow:
            telechecker(config, follow=True)
        if not telegram and not emby:
            telegram = "08:00"
            emby = 7
        schedule_telegram = schedule.Scheduler()
        if telegram:
            telegram = parser.parse(telegram).time().strftime("%H:%M")
            schedule_telegram.every().day.at(telegram).do(telechecker, config=config)
        schedule_emby = schedule.Scheduler()
        if emby:
            schedule_emby.every(emby).days.at(datetime.now().strftime("%H:%M")).do(
                embywatcher, config=config
            )
        if instant:
            schedule_telegram.run_all()
            schedule_emby.run_all()
        if telegram:
            logger.info(f"下一次签到将在{int(schedule_telegram.idle_seconds/3600)}小时后进行.")
        if emby:
            logger.info(f"下一次保活将在{int(schedule_emby.idle_seconds/3600/24)}天后进行.")
        while True:
            schedule_telegram.run_pending()
            schedule_emby.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    cli()
