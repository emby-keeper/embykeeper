import asyncio
from typing import AsyncGenerator, Optional

from loguru import logger
from pyrogram import Client as _Client
from pyrogram import raw, types, utils
from pyrogram.enums import SentCodeType
from pyrogram.errors import BadRequest, PhoneCodeExpired, PhoneCodeInvalid, RPCError, Unauthorized

from .. import __name__, __version__
from ..utils import to_iterable

logger = logger.bind(scheme="telegram")


class Client(_Client):
    async def authorize(self):
        if self.bot_token:
            return await self.sign_in_bot(self.bot_token)
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
                    self.phone_code = await utils.ainput(
                        " " * 29 + f'请在{code_target[sent_code.type]}接收"{self.phone_number}"的两步验证码: '
                    )
                signed_in = await self.sign_in(self.phone_number, sent_code.phone_code_hash, self.phone_code)
            except PhoneCodeInvalid or PhoneCodeExpired:
                pass
            else:
                break
        if isinstance(signed_in, types.User):
            return signed_in
        else:
            raise BadRequest("该账户尚未注册")

    async def get_dialogs(
        self, limit: int = 0, exclude_pinned=None, folder_id=None
    ) -> Optional[AsyncGenerator["types.Dialog", None]]:
        current = 0
        total = limit or (1 << 31) - 1
        limit = min(100, total)

        offset_date = 0
        offset_id = 0
        offset_peer = raw.types.InputPeerEmpty()

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

            for dialog in dialogs:
                yield dialog

                current += 1

                if current >= total:
                    return


class ClientsSession:
    pool = {}
    lock = asyncio.Lock()

    @classmethod
    def from_config(cls, config, **kw):
        accounts = config.get("telegram", [])
        for k, v in kw.items():
            accounts = [a for a in accounts if a.get(k, None) in to_iterable(v)]
        return cls(accounts=accounts, proxy=config.get("proxy", None))

    def __init__(self, accounts, proxy=None):
        self.accounts = accounts
        self.proxy = proxy
        self.phones = []
        self.done = asyncio.Queue()
        self.tasks = []

    @staticmethod
    async def login(account, proxy):
        logger.info(f'登录账号 "{account["phone"]}".')
        try:
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
                    )
                    await client.start()
                except Unauthorized:
                    await client.storage.delete()
                except Exception:
                    raise
                else:
                    break
        except RPCError as e:
            logger.error(f'登录账号 "{client.phone_number}" 失败 ({e.MESSAGE.format(value=e.value)}), 将被跳过.')
        except Exception as e:
            logger.exception(f'登录账号 "{client.phone_number}" 时发生异常, 将被跳过:')
        else:
            return client

    async def loginer(self, account):
        client = await self.login(account, self.proxy)
        if isinstance(client, Client):
            async with self.lock:
                phone = account["phone"]
                self.pool[phone] = (client, 1)
                self.phones.append(phone)
                await self.done.put(client)

    async def __aenter__(self):
        for a in self.accounts:
            async with self.lock:
                phone = a["phone"]
                if phone in self.pool:
                    client, ref = self.pool[phone]
                    ref += 1
                    self.pool[ref] = (client, ref)
                    await self.done.put(client)
                else:
                    self.pool[phone] = None
                    self.tasks.append(asyncio.create_task(self.loginer(a)))
        return self

    def __aiter__(self):
        async def aiter():
            for _ in range(len(self.accounts)):
                yield await self.done.get()

        return aiter()

    async def __aexit__(self, type, value, tb):
        for phone in self.phones:
            async with self.lock:
                entry = self.pool.get(phone, None)
                if not entry:
                    continue
                client, ref = entry
                ref -= 1
                if ref:
                    self.pool[phone] = (client, ref)
                else:
                    logger.info(f"正在登出: {client.me.first_name}.")
                    try:
                        await client.stop(block=True)
                    except ConnectionError:
                        pass
                    finally:
                        self.pool.pop(phone, "None")
