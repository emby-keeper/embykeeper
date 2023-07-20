from __future__ import annotations
from collections import OrderedDict
from contextlib import asynccontextmanager

from datetime import datetime
import asyncio
import inspect
from typing import AsyncGenerator, Optional, Union

from rich.prompt import Prompt
from appdirs import user_data_dir
from loguru import logger
import pyrogram
from pyrogram import raw, types, utils, filters, dispatcher
from pyrogram.enums import SentCodeType
from pyrogram.errors import (
    BadRequest,
    RPCError,
    Unauthorized,
    SessionPasswordNeeded,
    CodeInvalid,
    PhoneCodeInvalid,
)
from pyrogram.handlers import MessageHandler, RawUpdateHandler, DisconnectHandler
from pyrogram.handlers.handler import Handler
from aiocache import Cache

from .. import __name__, __version__
from ..utils import async_partial, to_iterable

logger = logger.bind(scheme="telegram")


def _name(self: Union[types.User, types.Chat]):
    return " ".join([n for n in (self.first_name, self.last_name) if n])


def _chat_name(self: types.Chat):
    if self.title:
        return self.title
    else:
        return _name(self)


setattr(types.User, "name", property(_name))
setattr(types.Chat, "name", property(_chat_name))


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
                                logger.warning(f"Telegram Error: {e}")
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
                            logger.opt(exception=e).error("更新回调函数内发生错误:")
                        break
            except pyrogram.StopPropagation:
                pass
            except Exception as e:
                logger.opt(exception=e).error("更新控制器错误:")


class Client(pyrogram.Client):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.cache = Cache()
        self.dispatcher = Dispatcher(self)

    async def authorize(self):
        if self.bot_token:
            return await self.sign_in_bot(self.bot_token)
        retry = False
        while True:
            try:
                sent_code = await self.send_code(self.phone_number)
                code_target = {
                    SentCodeType.APP: "Telegram客户端",
                    SentCodeType.SMS: "短信",
                    SentCodeType.CALL: "来电",
                    SentCodeType.FLASH_CALL: "闪存呼叫",
                    SentCodeType.FRAGMENT_SMS: "Fragment短信",
                    SentCodeType.EMAIL_CODE: "邮件",
                }
                if not self.phone_code:
                    if retry:
                        msg = f'验证码错误, 请重新输入 "{self.phone_number}" 的登录验证码 (按回车确认)'
                    else:
                        msg = f'请从{code_target[sent_code.type]}接收 "{self.phone_number}" 的登录验证码 (按回车确认)'
                    self.phone_code = Prompt.ask(" " * 23 + msg)
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
                        self.password = Prompt.ask(" " * 23 + msg, password=True)
                    try:
                        return await self.check_password(self.password)
                    except BadRequest:
                        self.password = None
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
            await self.cache.set(cache_id, ((offset_id, offset_date, offset_peer), cache + dialogs), ttl=120)
            for dialog in dialogs:
                yield dialog

                current += 1

                if current >= total:
                    return

    @asynccontextmanager
    async def catch_reply(self, chat_id: Union[int, str], outgoing=False):
        async def handler_func(client, message, future: asyncio.Future):
            future.set_result(message)

        future = asyncio.Future()
        filter = filters.chat(chat_id)
        if not outgoing:
            filter = filter & (~filters.outgoing)
        handler = MessageHandler(async_partial(handler_func, future=future), filter)
        await self.add_handler(handler, group=0)
        try:
            yield future
        finally:
            self.remove_handler(handler, group=0)

    async def wait_reply(
        self, chat_id: Union[int, str], send: str = None, timeout: float = 10, outgoing=False
    ):
        async with self.catch_reply(chat_id=chat_id, outgoing=outgoing) as f:
            if send:
                await self.send_message(chat_id, send)
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


class ClientsSession:
    pool = {}
    lock = asyncio.Lock()
    watch = None

    @classmethod
    def from_config(cls, config, **kw):
        accounts = config.get("telegram", [])
        for k, v in kw.items():
            accounts = [a for a in accounts if a.get(k, None) in to_iterable(v)]
        return cls(accounts=accounts, proxy=config.get("proxy", None), basedir=config.get("basedir", None))

    @classmethod
    async def watchdog(cls, timeout=120):
        logger.debug("Telegram 账号池 watchdog 启动.")
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
        print("\r正在停止...\r", end="", flush=True)
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
        print(f"Telegram 账号池停止.\r", end="")
        for v in cls.pool.values():
            if isinstance(v, tuple):
                client: Client = v[0]
                await client.storage.save()
                await client.storage.close()
                logger.debug(f'登出账号 "{client.phone_number}".')

    def __init__(self, accounts, proxy=None, basedir=None, quiet=False):
        self.accounts = accounts
        self.proxy = proxy
        self.basedir = basedir or user_data_dir(__name__)
        self.phones = []
        self.done = asyncio.Queue()
        self.quiet = quiet
        if not self.watch:
            self.__class__.watch = asyncio.create_task(self.watchdog())

    async def login(self, account, proxy):
        try:
            if not self.quiet:
                logger.info(f'登录至账号 "{account["phone"]}".')
            while True:
                try:
                    client = Client(
                        app_version=f"{__name__.capitalize()} {__version__}",
                        name=account["phone"],
                        api_id=account["api_id"],
                        api_hash=account["api_hash"],
                        phone_number=account["phone"],
                        proxy=proxy,
                        lang_code="zh",
                        workdir=self.basedir,
                    )
                    await client.start()
                except Unauthorized:
                    await client.storage.delete()
                except KeyError as e:
                    logger.warning(f'登录账号 "{client.phone_number}" 时发生异常, 可能是由于网络错误, 将在 3 秒后重试.')
                    await asyncio.sleep(3)
                else:
                    break
        except asyncio.CancelledError:
            raise
        except RPCError as e:
            logger.error(f'登录账号 "{client.phone_number}" 失败 ({e.MESSAGE.format(value=e.value)}), 将被跳过.')
        except Exception as e:
            logger.opt(exception=e).error(f'登录账号 "{client.phone_number}" 时发生异常, 将被跳过:')
        else:
            logger.debug(f'登录账号 "{client.phone_number}" 成功.')
            return client

    async def loginer(self, account):
        client = await self.login(account, self.proxy)
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
                client, ref = entry
                ref -= 1
                self.pool[phone] = (client, ref)
                logger.debug(f"Telegram 账号池计数降低: {phone} => {ref}")
