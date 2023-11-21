from datetime import datetime, timedelta
import random
import re

import asyncio
from cachetools import TTLCache
from pyrogram.types import Message, User, Chat
from pyrogram.enums import ChatMemberStatus, MessageServiceType, MessagesFilter

from ..lock import pornemby_alert, pornemby_messager_mids
from .base import Monitor


class PornembyAlertMonitor(Monitor):
    name = "Pornemby 风险急停监控"
    chat_name = "Pornemby"
    additional_auth = ["pornemby_pack"]
    allow_edit = True
    debug_no_log = True

    user_alert_keywords = ["脚本", "真人", "admin", "全是", "举报", "每次", "机器人", "report"]
    admin_alert_keywords = ["不要", "封", "ban", "warn", "踢", "抓"]
    alert_reply_keywords = ["真人", "脚本", "每次", "在吗", "机器", "封", "warn", "ban"]
    alert_reply_except_keywords = ["不要回复", "别回复", "勿回复"]
    reply_words = ["?" * (i + 1) for i in range(3)] + ["嗯?", "欸?", "🤔"]
    reply_interval = 7200

    async def init(self):
        self.lock = asyncio.Lock()
        self.last_reply = None
        self.member_status_cache = TTLCache(maxsize=128, ttl=86400)
        self.member_status_cache_lock = asyncio.Lock()
        return True

    async def check_admin(self, chat: Chat, user: User):
        async with self.member_status_cache_lock:
            if not user.id in self.member_status_cache:
                member = await self.client.get_chat_member(chat.id, user.id)
                self.member_status_cache[user.id] = member.status
        if self.member_status_cache[user.id] in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return True

    def check_keyword(self, message: Message, keywords):
        content = message.text or message.caption
        if content:
            return any([re.search(k, content) for k in keywords])

    def set_alert(self, time: int = None):
        async def doit():
            if time:
                self.log.warning(f"Pornemby 风险急停被触发, 停止操作 {time} 秒.")
            else:
                self.log.bind(notify=True).error("Pornemby 风险急停被触发, 所有操作永久停止.")
            async with self.lock:
                if time:
                    pornemby_alert[self.client.me.id] = True
                    await asyncio.sleep(time)
                    self.log.info(f"Pornemby 风险急停结束.")
                    pornemby_alert[self.client.me.id] = False
                else:
                    pornemby_alert[self.client.me.id] = True

        asyncio.create_task(doit())

    async def check_pinned(self, message: Message):
        if message.service == MessageServiceType.PINNED_MESSAGE:
            return message.pinned_message
        elif (not message.text) and (not message.media) and (not message.service) and (not message.game):
            async for message in self.client.search_messages(message.chat.id, filter=MessagesFilter.PINNED):
                return message
        else:
            return None

    async def on_trigger(self, message: Message, key, reply):
        # 管理员回复水群消息: 永久停止, 若存在关键词即回复
        # 用户回复水群消息, 停止 3600 秒, 若存在关键词即回复
        if message.reply_to_message_id in pornemby_messager_mids.get(self.client.me.id, []):
            if await self.check_admin(message.chat, message.from_user):
                self.set_alert()
            else:
                self.set_alert(3600)
            if self.check_keyword(message, self.alert_reply_keywords):
                if not self.check_keyword(message, self.alert_reply_except_keywords):
                    if (not self.last_reply) or (
                        self.last_reply < datetime.now() - timedelta(seconds=self.reply_interval)
                    ):
                        await asyncio.sleep(random.uniform(5, 15))
                        await message.reply(random.choice(self.reply_words))
                        self.last_reply = datetime.now()
            return

        # 置顶消息, 若不在列表中停止 3600 秒, 否则停止 86400 秒
        pinned = await self.check_pinned(message)
        if pinned:
            if self.check_keyword(pinned, self.user_alert_keywords + self.admin_alert_keywords):
                self.set_alert(86400)
            else:
                self.set_alert(3600)
            return

        # 管理员发送消息, 若不在列表中停止 3600 秒, 否则停止 86400 秒
        # 用户发送列表中消息, 停止 1800 秒
        if await self.check_admin(message.chat, message.from_user):
            if self.check_keyword(message, self.user_alert_keywords + self.admin_alert_keywords):
                self.set_alert(86400)
            else:
                self.set_alert(3600)
        else:
            if self.check_keyword(message, self.user_alert_keywords):
                self.set_alert(1800)
