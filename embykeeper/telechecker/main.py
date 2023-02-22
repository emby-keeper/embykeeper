import time
from threading import Event

import click
import toml
from appdirs import user_cache_dir
from loguru import logger
from telegram.client import AuthorizationState, Telegram

from . import *

CHECKINERS = (JMSCheckin, TerminusCheckin, JMSIPTVCheckin, LJYYCheckin, PeachCheckin)


def main(config, follow=False):
    with open(config) as f:
        config = toml.load(f)
    proxy = config.get("proxy", None)
    if proxy:
        proxy_host = proxy.get("host", "127.0.0.1")
        proxy_port = proxy.get("port", "1080")
        proxy_type = proxy.get("type", "socks5")
        if proxy_type.lower() == "socks5":
            proxy_type = {"@type": "proxyTypeSocks5"}
        elif proxy_type.lower() in ("http", "https"):
            proxy_type = {"@type": "proxyTypeHttp"}
        elif proxy_type.lower() == "mtproto":
            proxy_type = {"@type": "proxyTypeMtproto"}
        else:
            raise ValueError(f'proxy_type "{proxy_type}" is not supported.')
    else:
        proxy_host = proxy_port = proxy_type = None
    for a in config.get("telegram", ()):
        logger.info(f'登录 Telegram: {a["phone"]}.')
        tg = Telegram(
            tdlib_verbosity=1,
            api_id=a["api_id"],
            api_hash=a["api_hash"],
            phone=a["phone"],
            database_encryption_key="passw0rd!",
            files_directory=user_cache_dir("telegram"),
            proxy_server=proxy_host,
            proxy_port=proxy_port,
            proxy_type=proxy_type,
        )
        state = tg.login(blocking=False)
        while not state == AuthorizationState.READY:
            if config.get("quiet", False) == True:
                logger.warning(f'账号 "{a["phone"]}" 需要额外的信息以登录, 但由于quiet模式而跳过.')
                continue
            if state == AuthorizationState.WAIT_CODE:
                tg.send_code(click.prompt(f'请在客户端接收验证码 ({a["phone"]})', type=str))
            if state == AuthorizationState.WAIT_PASSWORD:
                tg.send_password(
                    click.prompt(f'请输入密码 ({a["phone"]})', type=str, hide_input=True)
                )
            state = tg.login(blocking=False)
        me = tg.get_me()
        me.wait()
        if me.error:
            logger.warning(f'账号 "{tg.phone}" 无法读取用户名而跳过.')
            continue
        else:
            tg.username = f"{me.update['first_name']} {me.update['last_name']}"
            logger.info(f"欢迎你: {tg.username}.")
        chats = tg.get_chats()
        chats.wait()
        if chats.error:
            logger.warning(f'账号 "{tg.username}" 无法读取会话而跳过.')
            continue
        if follow:
            logger.info(f"等待新消息更新以获取 ChatID.")

            def message_dumper(update):
                if "text" in update["message"]["content"]:
                    text = update["message"]["content"]["text"]["text"].replace(
                        "\n", " "
                    )
                    print(
                        "{} > {} ({}) ".format(
                            tg.username,
                            (text[:50] + "...") if len(text) > 50 else text,
                            update["message"]["chat_id"],
                        )
                    )

            tg.add_update_handler("updateNewMessage", message_dumper)
        else:
            checkiners = [cls(tg, config.get("retries", 10)) for cls in CHECKINERS]
            for c in checkiners:
                logger.info(c.msg("开始执行签到."))
                c.checkin()
            endtime = time.time() + config.get("timeout", 120)
            for c in checkiners:
                timeout = endtime - time.time()
                if timeout:
                    if not c.ok.wait(timeout):
                        logger.error(c.msg("无法在时限内完成签到."))
                else:
                    if not c.ok.is_set():
                        logger.error(c.msg("无法在时限内完成签到."))
            logger.info("运行完成.")
    if follow:
        Event().wait()
