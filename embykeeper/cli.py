import time
import uuid
from pathlib import Path

import click
import schedule
import toml
from dateutil import parser
from faker import Faker
from faker.providers import internet, profile
from loguru import logger
from rich.logging import Console, RichHandler

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
    multiple=True,
    help="每日指定时间执行Telegram bot签到",
)
@click.option(
    "--telegram-follow", is_flag=True, hidden=True, help="启动Telegram监听模式以确定ChatID"
)
@click.option("--emby", "-e", type=int, flag_value=7, help="每隔N天执行Emby保活")
@click.option("--instant/--no-instant", default=True, help="立刻执行一次计划任务")
def cli(config, telegram, emby, instant, telegram_follow):
    if not config:
        logger.warning("你需要输入一个config文件.")
        default = Path("accounts.toml")
        if not default.exists():
            logger.warning(f'作为范例, 请参考"{default.name}".')
            with open(default, "w+") as f:
                toml.dump(_get_faked_accounts(), f)
    else:
        if telegram_follow:
            telechecker(config, follow=True)
        if not telegram and not emby:
            telegram = ["08:00"]
            emby = 7
        if telegram:
            for t in telegram:
                t = parser.parse(t).time().strftime("%H:%M")
                schedule.every().day.at(t).do(telechecker, config=config)
        if emby:
            pass
        if instant:
            schedule.run_all()
        logger.info(f"下一次签到将在{int(schedule.idle_seconds()/3600)}小时后进行.")
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    cli()
