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
        username = f"{self.client.me.first_name} {self.client.me.last_name}"
        self.log = logger.bind(scheme="telelink", username=username)

    @property
    def instance(self):
        rd = random.Random()
        rd.seed(uuid.getnode())
        return uuid.UUID(int=rd.getrandbits(128))

    @staticmethod
    async def delete_messages(messages):
        async def delete(m):
            try:
                await m.delete(revoke=False)
            except asyncio.CancelledError:
                pass

        return await asyncio.gather(*[delete(m) for m in messages])

    async def post(self, cmd, condition=None, timeout=10):
        results = {}
        ok = asyncio.Event()
        handler = self.get_handler(cmd, results, ok, condition)
        handler = MessageHandler(handler, filters.text & filters.bot & filters.user(self.bot))
        self.client.add_handler(handler)
        messages = []
        messages.append(await self.client.send_message(self.bot, f"/start quiet"))
        await asyncio.sleep(0.5)
        messages.append(await self.client.send_message(self.bot, cmd))
        try:
            await asyncio.wait_for(ok.wait(), timeout=timeout)
        except asyncio.CancelledError:
            try:
                await asyncio.wait_for(self.delete_messages(messages), 1.0)
            except asyncio.TimeoutError:
                pass
            finally:
                raise
        else:
            await self.delete_messages(messages)
            return results
        finally:
            self.client.remove_handler(handler)

    async def preprocess(self, post, name):
        try:
            results = await post
        except asyncio.TimeoutError:
            self.log.warning(f"{name}超时.")
            return None
        status, errmsg = [results.get(p, None) for p in ("status", "errmsg")]
        if status == "error":
            self.log.warning(f"{name}错误: {errmsg}.")
            return None
        elif status == "ok":
            return results
        else:
            self.log.warning(f"{name}出现未知错误.")
            return None

    @staticmethod
    def get_handler(cmd, results, ok, condition=None):
        async def _handler(client: Client, message: Message):
            try:
                toml = tomli.loads(message.text)
            except tomli.TOMLDecodeError:
                await message.delete(revoke=False)
                return
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
                        await message.delete(revoke=False)
                        return
                message.continue_propagation()

        return _handler

    async def auth(self, service: str):
        post = self.post(f"/auth {service} {self.instance}")
        results = await self.preprocess(post, name=f"服务 {service.capitalize()} 认证")
        return bool(results)

    async def captcha(self):
        post = self.post("/captcha", timeout=240)
        results = await self.preprocess(post, name="请求跳过验证码")
        if results:
            return [results.get(p, None) for p in ("token", "proxy", "useragent")]
        else:
            return None, None, None

    async def sendlog(self, message):
        post = self.post(f"/log {self.instance} {message}")
        results = await self.preprocess(post, name="发送日志到 Telegram ")
        return bool(results)


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
