import time
from functools import partial
from textwrap import indent
from threading import Event

import click
from appdirs import user_cache_dir
from loguru import logger
from teleclient.client import AuthorizationState, Telegram

from . import *

CHECKINERS = (JMSCheckin, TerminusCheckin, JMSIPTVCheckin, LJYYCheckin, PeachCheckin)


def login(config):
    proxy = config.get("proxy", None)
    if proxy:
        proxy_host = proxy.get("host", "127.0.0.1")
        proxy_port = proxy.get("port", "1080")
        proxy_type = proxy.get("type", "socks5")
        if proxy_type.lower() == "socks5":
            proxy_type = {"@type": "proxyTypeSocks5"}
        elif proxy_type.lower() in ("http", "https"):
            proxy_type = {"@type": "proxyTypeHttp"}
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
                logger.error(f'账号 "{a["phone"]}" 需要额外的信息以登录, 但由于quiet模式而跳过.')
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
            logger.error(f'账号 "{tg.phone}" 无法读取用户名而跳过.')
            continue
        else:
            tg.username = f"{me.update['first_name']} {me.update['last_name']}"
            logger.info(f"欢迎你: {tg.username}.")
        chats = tg.get_chats()
        chats.wait()
        if chats.error:
            logger.error(f'账号 "{tg.username}" 无法读取会话而跳过.')
            continue
        yield tg


def dump_update(update, tg, cache={}):
    message = update["message"]
    content = message["content"]
    user_id = message["sender_id"].get("user_id", None)
    if not user_id:
        return
    if "text" in content:
        text = content["text"]["text"].strip()
    elif "photo" in content:
        text = content["caption"]["text"].strip()
    else:
        return
    markups = message.get("reply_markup", {}).get("rows", [])
    markup_lines = []
    for row in markups:
        for btn in row:
            text = btn.get('text', None)
            usage = btn.get('type', {})
            usage = usage.get('url', usage.get('data', None))
            markup_lines.append(f'{text} ({usage})')
    if message["is_outgoing"]:
        sender_name = "Me"
    else:
        sender_name = cache.get(user_id, None)
        if not sender_name:
            sender = tg.get_user(user_id)
            sender.wait()
            if sender.error:
                sender_name = f"<Unknown User {user_id}>"
            else:
                sender_name = (
                    f"{sender.update['first_name']} {sender.update['last_name']}"
                )
            cache[user_id] = sender_name
    text = text.replace("\n", " ")
    msg = "{} > {}: {} (chatid = {}, userid = {}) ".format(
            tg.username,
            sender_name.strip(),
            (text[:50] + "...") if len(text) > 50 else text,
            message["chat_id"],
            user_id,
        )
    if markup_lines:
        markup_lines = indent("\n".join(markup_lines), " " * 4)
        msg += f'\n  Buttons:\n{markup_lines}'
    print(msg)
    
def main(config, follow=False):
    if not follow:
        for tg in login(config):
            checkiners = [cls(tg, config.get("retries", 10)) for cls in CHECKINERS]
            for c in checkiners:
                logger.info(c.msg("开始执行签到."))
                c.checkin()
            endtime = time.time() + config.get("timeout", 240)
            for c in checkiners:
                timeout = endtime - time.time()
                if timeout:
                    if not c.finished.wait(timeout):
                        logger.error(c.msg("无法在时限内完成签到."))
                else:
                    if not c.finished.is_set():
                        logger.error(c.msg("无法在时限内完成签到."))
            logger.info("Telegram签到运行完成.")
    else:
        cache = {}
        for tg in login(config):
            logger.info(f"等待新消息更新以获取 ChatID.")
            tg.add_update_handler("updateNewMessage", partial(dump_update, tg=tg, cache=cache))
        Event().wait()
