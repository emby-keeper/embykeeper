import asyncio
from .base import BotCheckin

from pyrogram.types import Message

from ...utils import async_partial
from ..lock import misty_monitors, misty_locks


class MistyCheckin(BotCheckin):
    ocr = "digit5-teko@v1"

    name = "Misty"
    bot_username = "EmbyMistyBot"
    bot_captcha_len = 5
    bot_checkin_caption_pat = "请输入验证码"
    bot_text_ignore = ["选择您要使用的功能", "欢迎使用", "选择功能"]

    async def start(self):
        misty_locks.setdefault(self.client.me.id, asyncio.Lock())
        lock = misty_locks.get(self.client.me.id, None)
        async with lock:
            return await super().start()

    async def send_checkin(self, retry=False):
        wr = async_partial(self.client.wait_reply, self.bot_username)
        for _ in range(3):
            try:
                if retry:
                    await asyncio.sleep(1)
                    msg = await wr("🛎每日签到")
                    if any(w in (msg.text or msg.caption) for w in ("上次签到", "验证码")):
                        break
                else:
                    msg: Message = await wr("/cancel")
                    if "选择您要使用的功能" in (msg.caption or msg.text):
                        await asyncio.sleep(1)
                        msg = await wr("🌏切换服务器")
                    if "选择您要使用的服务器" in (msg.text or msg.caption):
                        await asyncio.sleep(1)
                        msg = await wr("✨Misty")
                    if "选择您要使用的功能" in (msg.caption or msg.text):
                        await asyncio.sleep(1)
                        msg = await wr("🎲更多功能")
                    if "请选择功能" in msg.text or msg.caption:
                        await asyncio.sleep(1)
                        msg = await wr("🛎每日签到")
                        if any(w in (msg.text or msg.caption) for w in ("上次签到", "验证码")):
                            break
            except asyncio.TimeoutError:
                pass
        else:
            self.log.warning(f"签到失败: 无法进入签到页面.")
            await self.fail()

    async def cleanup(self):
        monitor = misty_monitors.get(self.client.me.id, None)
        if monitor:
            if not await monitor.init():
                self.log.warning(f"发生冲突: 无法重置 Misty 开注监控状态.")
                return False
        return True
