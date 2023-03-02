from pyrogram import Client as _Client
from pyrogram.enums import SentCodeType
from pyrogram.errors import BadRequest
from pyrogram.types import User
from pyrogram.utils import ainput


class Client(_Client):
    async def authorize(self):
        if self.bot_token:
            return await self.sign_in_bot(self.bot_token)
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
            self.phone_code = await ainput(f'请在{code_target[sent_code.type]}接收"{self.phone_number}"的两步验证码: ')
        signed_in = await self.sign_in(self.phone_number, sent_code.phone_code_hash, self.phone_code)
        if isinstance(signed_in, User):
            return signed_in
        else:
            raise BadRequest("This account is not registered")
