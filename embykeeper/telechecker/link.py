import asyncio
import io
import random
import uuid

import tomli
from loguru import logger
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.raw.functions.messages import DeleteHistory
from pyrogram.types import Message
from rich.text import Text


class Link:
    bot = "embykeeper_auth_bot"

    def __init__(self, client: Client):
        self.client = client
        self.log = logger.bind(scheme="telelink", username=self.client.me.first_name)

    @property
    def instance(self):
        rd = random.Random()
        rd.seed(uuid.getnode())
        return uuid.UUID(int=rd.getrandbits(128))
    
    async def post(self, cmd, condition=None):
        handler, results, ok = self.get_handler(cmd, condition)
        handler = MessageHandler(handler, filters.text & filters.bot & filters.user(self.bot))
        self.client.add_handler(handler)
        messages = [
            await self.client.send_message(self.bot, f"/start"),
            await self.client.send_message(self.bot, cmd),
        ]
        try:
            await asyncio.wait_for(ok.wait(), 10)
            return results
        finally:
            self.client.remove_handler(handler)
            for m in messages:
                await m.delete(revoke=False)
    
    @staticmethod
    def get_handler(cmd, condition=None):
        results = {}
        ok = asyncio.Event()

        async def _handler(client: Client, message: Message):
            try:
                toml = tomli.loads(message.text)
            except tomli.TOMLDecodeError:
                return await message.delete(revoke=False)
            else:
                if toml.get("command", None) == cmd:
                    if condition is None:
                        cond = True
                    elif asyncio.iscoroutinefunction(condition):
                        cond = await condition(toml)
                    elif callable(condition):
                        cond = condition(toml)
                    if cond:
                        results.update(toml)
                        ok.set()
                        return await message.delete(revoke=False)
                message.continue_propagation()

        return _handler, results, ok
    
    async def auth(self, service: str):
        try:
            results = await self.post(f"/auth {service} {self.instance}")
        except asyncio.TimeoutError:
            self.log.warning(f'服务 {service.capitalize()} 认证超时.')
            return False
        status = results.get("status", None)
        errmsg = results.get("errmsg", None)
        if status == "error":
            self.log.warning(f'服务 {service.capitalize()} 认证错误: {errmsg}.')
            return False
        elif status == "ok":
            return True
        else:
            self.log.warning(f'服务 {service.capitalize()} 认证出现未知错误.')
            return False
        
    async def captcha(self):
        try:
            results = await self.post(f"/captcha")
        except asyncio.TimeoutError:
            self.log.warning(f'请求跳过验证码超时.')
            return None, None
        status = results.get("status", None)
        errmsg = results.get("errmsg", None)
        token = results.get("token", None)
        proxy = results.get("proxy", None)
        if status == "error":
            self.log.warning(f'请求跳过验证码错误: {errmsg}.')
            return None, None
        elif status == "ok":
            return token, proxy
        else:
            self.log.warning(f'请求跳过验证码出现未知错误.')
            return None, None


    async def sendlog(self, message):
        if self.client.is_connected:
            message = await self.client.send_message(self.bot, f"/log {self.instance} {message}")
            await message.delete(revoke=False)

    async def delete_history(self):
        peer = await self.client.resolve_peer(self.bot)
        await self.client.invoke(DeleteHistory(peer=peer, max_id=0, revoke=False))

class TelegramStream(io.TextIOWrapper):
    def __init__(self, link: Link = None):
        super().__init__(io.BytesIO(), line_buffering=True)
        self.link = link

    def write(self, message):
        message = Text.from_markup(message).plain
        if message.endswith("\n"):
            message = message[:-1]
        if message:
            asyncio.create_task(self.link.sendlog(message))
        super().write(message + "\n")
