from __future__ import annotations

import binascii
from collections import OrderedDict
from contextlib import asynccontextmanager
import uuid
from datetime import datetime
import asyncio
import inspect
from pathlib import Path
import pickle
import random
import sys
from typing import AsyncGenerator, Optional, Union
from sqlite3 import OperationalError
import logging

from rich.prompt import Prompt
from appdirs import user_data_dir
from loguru import logger
import pyrogram
from pyrogram import raw, types, utils, filters, dispatcher
from pyrogram.enums import SentCodeType
from pyrogram.errors import (
    ChannelPrivate,
    BadRequest,
    RPCError,
    ApiIdPublishedFlood,
    Unauthorized,
    SessionPasswordNeeded,
    CodeInvalid,
    PhoneCodeInvalid,
    BadMsgNotification,
)
from pyrogram.handlers import MessageHandler, RawUpdateHandler, DisconnectHandler, EditedMessageHandler
from pyrogram.handlers.handler import Handler
from aiocache import Cache
import aiohttp
from aiohttp_socks import ProxyConnector, ProxyType, ProxyConnectionError, ProxyTimeoutError

from embykeeper import var, __name__ as __product__, __version__
from embykeeper.utils import async_partial, show_exception, to_iterable

logger = logger.bind(scheme="telegram")

_id = b"\x80\x04\x95\x15\x00\x00\x00\x00\x00\x00\x00]\x94(K2K2K9K7K9K6K4K8e."
_hash = b"\x80\x04\x95E\x00\x00\x00\x00\x00\x00\x00]\x94(K7K8KeKeKfKcKfKbK9K8K9KeK1K1K0KcK0KdK3K0K7K8K3K8K5KfK9K9K7KaKeKee."
_decode = lambda x: "".join(map(chr, to_iterable(pickle.loads(x))))

API_KEY = {
    "_": {"api_id": _decode(_id), "api_hash": _decode(_hash)}
    # "nicegram": {"api_id": "94575", "api_hash": "a3406de8d171bb422bb6ddf3bbd800e2"},
    # "tgx-android": {"api_id": "21724", "api_hash": "3e0cb5efcd52300aec5994fdfc5bdc16"},
    # "tg-react": {"api_id": "414121", "api_hash": "db09ccfc2a65e1b14a937be15bdb5d4b"},
}


def _name(self: Union[types.User, types.Chat]):
    return " ".join([n for n in (self.first_name, self.last_name) if n])


def _chat_name(self: types.Chat):
    if self.title:
        return self.title
    else:
        return _name(self)


setattr(types.User, "name", property(_name))
setattr(types.Chat, "name", property(_chat_name))


class LogRedirector(logging.StreamHandler):
    def emit(self, record):
        try:
            if record.levelno >= logging.WARNING:
                logger.debug(f"Pyrogram log: {record.getMessage()}")
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


pyrogram_session_logger = logging.getLogger("pyrogram")
for h in pyrogram_session_logger.handlers[:]:
    pyrogram_session_logger.removeHandler(h)
pyrogram_session_logger.addHandler(LogRedirector())


class Dispatcher(dispatcher.Dispatcher):
    def __init__(self, client: Client):
        super().__init__(client)
        self.mutex = asyncio.Lock()

    async def start(self):
        logger.debug("Telegram 更新分配器启动.")
        if not self.client.no_updates:
            self.handler_worker_tasks = [
                self.loop.create_task(self.handler_worker()) for _ in range(self.client.workers)
            ]

    def add_handler(self, handler, group: int):
        async def fn():
            async with self.mutex:
                if group not in self.groups:
                    self.groups[group] = []
                    self.groups = OrderedDict(sorted(self.groups.items()))
                self.groups[group].append(handler)
                # logger.debug(f"增加了 Telegram 更新处理器: {handler.__class__.__name__}.")

        return self.loop.create_task(fn())

    def remove_handler(self, handler, group: int):
        async def fn():
            async with self.mutex:
                if group not in self.groups:
                    raise ValueError(f"Group {group} does not exist. Handler was not removed.")
                self.groups[group].remove(handler)
                # logger.debug(f"移除了 Telegram 更新处理器: {handler.__class__.__name__}.")

        return self.loop.create_task(fn())

    async def handler_worker(self):
        while True:
            packet = await self.updates_queue.get()

            if packet is None:
                break

            try:
                update, users, chats = packet
                parser = self.update_parsers.get(type(update), None)

                parsed_update, handler_type = (
                    await parser(update, users, chats) if parser is not None else (None, type(None))
                )

                async with self.mutex:
                    groups = {i: g[:] for i, g in self.groups.items()}

                for group in groups.values():
                    for handler in group:
                        args = None

                        if isinstance(handler, handler_type):
                            try:
                                if await handler.check(self.client, parsed_update):
                                    args = (parsed_update,)
                            except Exception as e:
                                logger.warning(f"Telegram 错误: {e}")
                                continue

                        elif isinstance(handler, RawUpdateHandler):
                            args = (update, users, chats)

                        if args is None:
                            continue

                        try:
                            if inspect.iscoroutinefunction(handler.callback):
                                await handler.callback(self.client, *args)
                            else:
                                await self.loop.run_in_executor(
                                    self.client.executor, handler.callback, self.client, *args
                                )
                        except pyrogram.StopPropagation:
                            raise
                        except pyrogram.ContinuePropagation:
                            continue
                        except Exception as e:
                            logger.error(f"更新回调函数内发生错误.")
                            show_exception(e, regular=False)
                        break
                    else:
                        continue
                    break
            except pyrogram.StopPropagation:
                pass
            except TimeoutError:
                logger.info("网络不稳定, 可能遗漏消息.")
            except Exception as e:
                logger.error("更新控制器错误.")
                show_exception(e, regular=False)


class Client(pyrogram.Client):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cache = Cache()
        self.lock = asyncio.Lock()
        self.dispatcher = Dispatcher(self)

    async def authorize(self):
        if self.bot_token:
            return await self.sign_in_bot(self.bot_token)
        retry = False
        while True:
            try:
                sent_code = await self.send_code(self.phone_number)
                code_target = {
                    SentCodeType.APP: " Telegram 客户端",
                    SentCodeType.SMS: "短信",
                    SentCodeType.CALL: "来电",
                    SentCodeType.FLASH_CALL: "闪存呼叫",
                    SentCodeType.FRAGMENT_SMS: " Fragment 短信",
                    SentCodeType.EMAIL_CODE: "邮件",
                }
                if not self.phone_code:
                    if retry:
                        msg = f'验证码错误, 请重新输入 "{self.phone_number}" 的登录验证码 (按回车确认)'
                    else:
                        msg = f'请从{code_target[sent_code.type]}接收 "{self.phone_number}" 的登录验证码 (按回车确认)'
                    self.phone_code = Prompt.ask(" " * 23 + msg, console=var.console)
                signed_in = await self.sign_in(self.phone_number, sent_code.phone_code_hash, self.phone_code)
            except (CodeInvalid, PhoneCodeInvalid):
                self.phone_code = None
                retry = True
            except SessionPasswordNeeded:
                retry = False
                while True:
                    if not self.password:
                        if retry:
                            msg = f'密码错误, 请重新输入 "{self.phone_number}" 的两步验证密码 (不显示, 按回车确认)'
                        else:
                            msg = f'需要输入 "{self.phone_number}" 的两步验证密码 (不显示, 按回车确认)'
                        self.password = Prompt.ask(" " * 23 + msg, password=True, console=var.console)
                    try:
                        return await self.check_password(self.password)
                    except BadRequest:
                        self.password = None
                        retry = True
            except Exception as e:
                logger.error(f"登录时出现异常错误!")
                show_exception(e, regular=False)
                retry = True
            else:
                break
        if isinstance(signed_in, types.User):
            return signed_in
        else:
            raise BadRequest("该账户尚未注册")

    def add_handler(self, handler: Handler, group: int = 0):
        if isinstance(handler, DisconnectHandler):
            self.disconnect_handler = handler.callback

            async def dummy():
                pass

            return asyncio.ensure_future(dummy())
        else:
            return self.dispatcher.add_handler(handler, group)

    def remove_handler(self, handler: Handler, group: int = 0):
        if isinstance(handler, DisconnectHandler):
            self.disconnect_handler = None

            async def dummy():
                pass

            return asyncio.ensure_future(dummy())
        else:
            return self.dispatcher.remove_handler(handler, group)

    async def get_dialogs(
        self, limit: int = 0, exclude_pinned=None, folder_id=None
    ) -> Optional[AsyncGenerator["types.Dialog", None]]:
        async with self.lock:
            cache_id = f"dialogs_{self.phone_number}_{folder_id}_{1 if exclude_pinned else 0}"
            (offset_id, offset_date, offset_peer), cache = await self.cache.get(
                cache_id, ((0, 0, raw.types.InputPeerEmpty()), [])
            )

            current = 0
            total = limit or (1 << 31) - 1
            limit = min(100, total)

            for c in cache:
                yield c
                current += 1
                if current >= total:
                    return

            while True:
                r = await self.invoke(
                    raw.functions.messages.GetDialogs(
                        offset_date=offset_date,
                        offset_id=offset_id,
                        offset_peer=offset_peer,
                        limit=limit,
                        hash=0,
                        exclude_pinned=exclude_pinned,
                        folder_id=folder_id,
                    ),
                    sleep_threshold=60,
                )

                users = {i.id: i for i in r.users}
                chats = {i.id: i for i in r.chats}

                messages = {}

                for message in r.messages:
                    if isinstance(message, raw.types.MessageEmpty):
                        continue

                    chat_id = utils.get_peer_id(message.peer_id)
                    messages[chat_id] = await types.Message._parse(self, message, users, chats)

                dialogs = []

                for dialog in r.dialogs:
                    if not isinstance(dialog, raw.types.Dialog):
                        continue

                    dialogs.append(types.Dialog._parse(self, dialog, messages, users, chats))

                if not dialogs:
                    return

                last = dialogs[-1]

                offset_id = last.top_message.id
                offset_date = utils.datetime_to_timestamp(last.top_message.date)
                offset_peer = await self.resolve_peer(last.chat.id)

                _, cache = await self.cache.get(cache_id, ((0, 0, raw.types.InputPeerEmpty()), []))
                await self.cache.set(
                    cache_id, ((offset_id, offset_date, offset_peer), cache + dialogs), ttl=120
                )
                for dialog in dialogs:
                    yield dialog

                    current += 1

                    if current >= total:
                        return

    @asynccontextmanager
    async def catch_reply(self, chat_id: Union[int, str], outgoing=False, filter=None):
        async def handler_func(client, message, future: asyncio.Future):
            try:
                future.set_result(message)
            except asyncio.InvalidStateError:
                pass

        future = asyncio.Future()
        f = filters.chat(chat_id)
        if not outgoing:
            f = f & (~filters.outgoing)
        if filter:
            f = f & filter
        handler = MessageHandler(async_partial(handler_func, future=future), f)
        await self.add_handler(handler, group=0)
        try:
            yield future
        finally:
            await self.remove_handler(handler, group=0)

    @asynccontextmanager
    async def catch_edit(self, message: types.Message, filter=None):
        def filter_message(id: int):
            async def func(flt, _, message: types.Message):
                return message.id == id

            return filters.create(func, "MessageFilter")

        async def handler_func(client, message, future: asyncio.Future):
            try:
                future.set_result(message)
            except asyncio.InvalidStateError:
                pass

        future = asyncio.Future()
        f = filter_message(message.id)
        if filter:
            f = f & filter
        handler = EditedMessageHandler(async_partial(handler_func, future=future), f)
        await self.add_handler(handler, group=0)
        try:
            yield future
        finally:
            await self.remove_handler(handler, group=0)

    async def wait_reply(
        self, chat_id: Union[int, str], send: str = None, timeout: float = 10, outgoing=False, filter=None
    ):
        async with self.catch_reply(chat_id=chat_id, filter=filter) as f:
            if send:
                await self.send_message(chat_id, send)
            msg: types.Message = await asyncio.wait_for(f, timeout)
            return msg

    async def wait_edit(
        self,
        message: types.Message,
        click: Union[str, int] = None,
        timeout: float = 10,
        noanswer=True,
        filter=None,
    ):
        async with self.catch_edit(message, filter=filter) as f:
            if click:
                try:
                    await message.click(click)
                except TimeoutError:
                    if noanswer:
                        pass
                    else:
                        raise
            msg: types.Message = await asyncio.wait_for(f, timeout)
            return msg

    async def mute_chat(self, chat_id: Union[int, str], until: Union[int, datetime]):
        if isinstance(until, datetime):
            until = until.timestamp()

        return await self.invoke(
            raw.functions.account.UpdateNotifySettings(
                peer=raw.types.InputNotifyPeer(peer=await self.resolve_peer(chat_id)),
                settings=raw.types.InputPeerNotifySettings(
                    show_previews=False,
                    mute_until=int(until),
                ),
            )
        )

    async def handle_updates(self, updates):
        self.last_update_time = datetime.now()

        if isinstance(updates, (raw.types.Updates, raw.types.UpdatesCombined)):
            is_min = any(
                (
                    await self.fetch_peers(updates.users),
                    await self.fetch_peers(updates.chats),
                )
            )

            users = {u.id: u for u in updates.users}
            chats = {c.id: c for c in updates.chats}

            for update in updates.updates:
                channel_id = getattr(
                    getattr(getattr(update, "message", None), "peer_id", None), "channel_id", None
                ) or getattr(update, "channel_id", None)

                pts = getattr(update, "pts", None)
                pts_count = getattr(update, "pts_count", None)

                if isinstance(update, raw.types.UpdateNewChannelMessage) and is_min:
                    message = update.message

                    if not isinstance(message, raw.types.MessageEmpty):
                        try:
                            diff = await self.invoke(
                                raw.functions.updates.GetChannelDifference(
                                    channel=await self.resolve_peer(utils.get_channel_id(channel_id)),
                                    filter=raw.types.ChannelMessagesFilter(
                                        ranges=[
                                            raw.types.MessageRange(
                                                min_id=update.message.id, max_id=update.message.id
                                            )
                                        ]
                                    ),
                                    pts=pts - pts_count,
                                    limit=pts,
                                )
                            )
                        except ChannelPrivate:
                            pass
                        except ValueError:
                            pass
                        except OSError:
                            logger.info("网络不稳定, 可能遗漏消息.")
                        else:
                            if not isinstance(diff, raw.types.updates.ChannelDifferenceEmpty):
                                users.update({u.id: u for u in diff.users})
                                chats.update({c.id: c for c in diff.chats})

                self.dispatcher.updates_queue.put_nowait((update, users, chats))
        elif isinstance(updates, (raw.types.UpdateShortMessage, raw.types.UpdateShortChatMessage)):
            diff = await self.invoke(
                raw.functions.updates.GetDifference(
                    pts=updates.pts - updates.pts_count, date=updates.date, qts=-1
                )
            )

            if diff.new_messages:
                self.dispatcher.updates_queue.put_nowait(
                    (
                        raw.types.UpdateNewMessage(
                            message=diff.new_messages[0], pts=updates.pts, pts_count=updates.pts_count
                        ),
                        {u.id: u for u in diff.users},
                        {c.id: c for c in diff.chats},
                    )
                )
            else:
                if diff.other_updates:  # The other_updates list can be empty
                    self.dispatcher.updates_queue.put_nowait((diff.other_updates[0], {}, {}))
        elif isinstance(updates, raw.types.UpdateShort):
            self.dispatcher.updates_queue.put_nowait((updates.update, {}, {}))
        elif isinstance(updates, raw.types.UpdatesTooLong):
            logger.info(updates)


class ClientsSession:
    pool = {}
    lock = asyncio.Lock()
    watch = None

    @classmethod
    def from_config(cls, config, in_memory=True, quiet=False, **kw):
        accounts = config.get("telegram", [])
        for k, v in kw.items():
            accounts = [a for a in accounts if a.get(k, None) in to_iterable(v)]
        return cls(
            accounts=accounts,
            proxy=config.get("proxy", None),
            basedir=config.get("basedir", None),
            in_memory=in_memory,
            quiet=quiet,
        )

    @classmethod
    async def watchdog(cls, timeout=120):
        logger.debug("Telegram 账号池看门狗启动.")
        try:
            counter = {}
            while True:
                await asyncio.sleep(10)
                for p in list(cls.pool):
                    try:
                        if cls.pool[p][1] <= 0:
                            if p in counter:
                                counter[p] += 1
                                if counter[p] >= timeout / 10:
                                    counter[p] = 0
                                    await cls.clean(p)
                            else:
                                counter[p] = 1
                        else:
                            counter.pop(p, None)
                    except (TypeError, KeyError):
                        pass
        except asyncio.CancelledError:
            await cls.shutdown()

    @classmethod
    async def clean(cls, phone):
        async with cls.lock:
            entry = cls.pool.get(phone, None)
            if not entry:
                return
            try:
                client, ref = entry
            except TypeError:
                return
            if not ref:
                logger.debug(f'登出账号 "{client.phone_number}".')
                await client.stop()
                cls.pool.pop(phone, None)

    @classmethod
    async def clean_all(cls):
        for phone in list(cls.pool):
            await cls.clean(phone)

    @classmethod
    async def shutdown(cls):
        print("\r正在停止...\r", end="", flush=True, file=sys.stderr)
        for v in cls.pool.values():
            if isinstance(v, asyncio.Task):
                v.cancel()
            else:
                client, ref = v
                client.dispatcher.updates_queue.put_nowait(None)
                for t in client.dispatcher.handler_worker_tasks:
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass
        while len(asyncio.all_tasks()) > 1:
            await asyncio.sleep(0.1)
        print(f"Telegram 账号池停止.\r", end="", file=sys.stderr)
        for v in cls.pool.values():
            if isinstance(v, tuple):
                client: Client = v[0]
                await client.storage.save()
                await client.storage.close()
                logger.debug(f'登出账号 "{client.phone_number}".')

    def __init__(self, accounts, proxy=None, basedir=None, in_memory=True, quiet=False):
        self.accounts = accounts
        self.proxy = proxy
        self.basedir = basedir or user_data_dir(__product__)
        self.phones = []
        self.done = asyncio.Queue()
        self.in_memory = in_memory
        self.quiet = quiet
        if not self.watch:
            self.__class__.watch = asyncio.create_task(self.watchdog())

    def get_connector(self, proxy=None):
        if proxy:
            connector = ProxyConnector(
                proxy_type=ProxyType[proxy["scheme"].upper()],
                host=proxy["hostname"],
                port=proxy["port"],
                username=proxy.get("username", None),
                password=proxy.get("password", None),
            )
        else:
            connector = aiohttp.TCPConnector()
        return connector

    async def test_network(self, proxy=None):
        url = "https://www.gstatic.com/generate_204"
        connector = self.get_connector(proxy=proxy)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 204:
                        return True
                    else:
                        logger.warning(f"检测网络状态时发生错误, 网络检测将被跳过.")
                        return False
            except (ProxyConnectionError, ProxyTimeoutError) as e:
                un = connector._proxy_username
                pw = connector._proxy_password
                auth = f"{un}:{pw}@" if un or pw else ""
                proxy_url = f"{connector._proxy_type.name.lower()}://{auth}{connector._proxy_host}:{connector._proxy_port}"
                logger.warning(
                    f"无法连接到您的代理 ({proxy_url}), 您的网络状态可能不好, 敬请注意. 程序将继续运行."
                )
            except OSError as e:
                logger.warning(f"无法连接到网络 (Google), 您的网络状态可能不好, 敬请注意. 程序将继续运行.")
                return False
            except Exception as e:
                logger.warning(f"检测网络状态时发生错误, 网络检测将被跳过.")
                show_exception(e)
                return False

    async def test_time(self, proxy=None):
        url = "http://worldtimeapi.org/api/timezone/Etc/UTC"
        connector = self.get_connector(proxy=proxy)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        resp_dict: dict = await resp.json()
                    else:
                        raise RuntimeError()
                unixtime = int(resp_dict.get("unixtime", None))
                nowtime = datetime.now().timestamp()
                if abs(nowtime - unixtime) > 30:
                    logger.warning(
                        f"您的系统时间设置不正确, 与世界时间差距过大, 可能会导致连接失败失败, 敬请注意. 程序将继续运行."
                    )
            except Exception:
                logger.warning(f"检测世界时间发生错误, 时间检测将被跳过.")
                return False

    async def login(self, account, proxy):
        try:
            account["phone"] = "".join(account["phone"].split())
            Path(self.basedir).mkdir(parents=True, exist_ok=True)
            session_file = Path(self.basedir) / f'{account["phone"]}.session'
            session_string_file = Path(self.basedir) / f'{account["phone"]}.login'
            if not self.quiet:
                logger.info(f'登录至账号 "{account["phone"]}".')
            for _ in range(3):
                if account.get("api_id", None) is None or account.get("api_hash", None) is None:
                    account.update(random.choice(list(API_KEY.values())))
                config_session_string = session_string = account.get("session", None)
                file_session_string = None
                if not session_string:
                    if session_string_file.is_file():
                        with open(session_string_file, encoding="utf-8") as f:
                            file_session_string = session_string = f.read().strip()
                if self.in_memory is None:
                    in_memory = True
                    if not session_string:
                        if session_file.is_file():
                            in_memory = False
                elif session_string:
                    in_memory = True
                else:
                    in_memory = self.in_memory
                if session_string or session_file.is_file():
                    logger.debug(
                        f'账号 "{account["phone"]}" 登录凭据存在, 仅内存模式{"启用" if in_memory else "禁用"}.'
                    )
                else:
                    logger.debug(
                        f'账号 "{account["phone"]}" 登录凭据不存在, 即将进入登录流程, 仅内存模式{"启用" if in_memory else "禁用"}.'
                    )
                try:
                    client = Client(
                        app_version=__version__,
                        device_model="Server " + uuid.uuid1().hex[16:20].upper(),
                        name=account["phone"],
                        api_id=account["api_id"],
                        api_hash=account["api_hash"],
                        phone_number=account["phone"],
                        session_string=session_string,
                        in_memory=in_memory,
                        proxy=proxy,
                        workdir=self.basedir,
                        sleep_threshold=30,
                    )
                    try:
                        await asyncio.wait_for(client.start(), 120)
                    except asyncio.TimeoutError:
                        if proxy:
                            logger.error(f"无法连接到 Telegram 服务器, 请检查您代理的可用性.")
                            continue
                        else:
                            logger.error(f"无法连接到 Telegram 服务器, 请检查您的网络.")
                            continue
                except OperationalError as e:
                    logger.warning(f"内部数据库错误, 正在重置, 您可能需要重新登录.")
                    show_exception(e)
                    session_file.unlink(missing_ok=True)
                except ApiIdPublishedFlood:
                    logger.warning(f'登录账号 "{account["phone"]}" 时发生 API key 限制, 将被跳过.')
                    break
                except Unauthorized as e:
                    if config_session_string:
                        logger.error(
                            f'账号 "{account["phone"]}" 由于配置中提供的 session 已被注销, 将被跳过.'
                        )
                        show_exception(e)
                        break
                    elif file_session_string:
                        logger.error(f'账号 "{account["phone"]}" 已被注销, 将在 3 秒后重新登录.')
                        show_exception(e)
                        session_string_file.unlink(missing_ok=True)
                        continue
                    elif client.in_memory:
                        logger.error(f'账号 "{account["phone"]}" 已被注销, 将在 3 秒后重新登录.')
                        show_exception(e)
                        continue
                    else:
                        logger.error(f'账号 "{account["phone"]}" 已被注销, 将在 3 秒后重新登录.')
                        show_exception(e)
                        await client.storage.delete()
                except KeyError as e:
                    logger.warning(
                        f'登录账号 "{account["phone"]}" 时发生异常, 可能是由于网络错误, 将在 3 秒后重试.'
                    )
                    show_exception(e)
                    await asyncio.sleep(3)
                else:
                    break
            else:
                logger.error(f'登录账号 "{account["phone"]}" 失败次数超限, 将被跳过.')
                return None
        except asyncio.CancelledError:
            raise
        except binascii.Error:
            logger.error(
                f'登录账号 "{account["phone"]}" 失败, 由于您在配置文件中提供的 session 无效, 将被跳过.'
            )
        except RPCError as e:
            logger.error(f'登录账号 "{account["phone"]}" 失败 ({e.MESSAGE.format(value=e.value)}), 将被跳过.')
            return None
        except BadMsgNotification as e:
            if "synchronized" in str(e):
                logger.error(
                    f'登录账号 "{account["phone"]}" 时发生异常, 可能是因为您的系统时间与世界时间差距过大, 将被跳过.'
                )
                return None
            else:
                logger.error(f'登录账号 "{account["phone"]}" 时发生异常, 将被跳过.')
                show_exception(e, regular=False)
                return None
        except Exception as e:
            logger.error(f'登录账号 "{account["phone"]}" 时发生异常, 将被跳过.')
            show_exception(e, regular=False)
            return None
        else:
            if not session_string_file.exists():
                with open(session_string_file, "w+", encoding="utf-8") as f:
                    f.write(await client.export_session_string())
            logger.debug(f'登录账号 "{client.phone_number}" 成功.')
            return client

    async def loginer(self, account):
        client = await self.login(account, proxy=self.proxy)
        if isinstance(client, Client):
            async with self.lock:
                phone = account["phone"]
                self.pool[phone] = (client, 1)
                self.phones.append(phone)
                await self.done.put(client)
                logger.debug(f"Telegram 账号池计数增加: {phone} => 1")
        else:
            await self.done.put(None)

    async def __aenter__(self):
        await self.test_network(self.proxy)
        asyncio.create_task(self.test_time(self.proxy))
        for a in self.accounts:
            phone = a["phone"]
            try:
                await self.lock.acquire()
                if phone in self.pool:
                    if isinstance(self.pool[phone], asyncio.Task):
                        self.lock.release()
                        await self.pool[phone]
                        await self.lock.acquire()
                    if isinstance(self.pool[phone], asyncio.Task):
                        continue
                    client, ref = self.pool[phone]
                    ref += 1
                    self.pool[phone] = (client, ref)
                    self.phones.append(phone)
                    await self.done.put(client)
                    logger.debug(f"Telegram 账号池计数增加: {phone} => {ref}")
                else:
                    self.pool[phone] = asyncio.create_task(self.loginer(a))
            finally:
                try:
                    self.lock.release()
                except RuntimeError:
                    pass
        return self

    def __aiter__(self):
        async def aiter():
            for _ in range(len(self.accounts)):
                client: Client = await self.done.get()
                if client:
                    yield client

        return aiter()

    async def __aexit__(self, type, value, tb):
        async with self.lock:
            for phone in self.phones:
                entry = self.pool.get(phone, None)
                if entry:
                    client, ref = entry
                    ref -= 1
                    self.pool[phone] = (client, ref)
                    logger.debug(f"Telegram 账号池计数降低: {phone} => {ref}")
