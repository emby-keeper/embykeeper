from loguru import logger

from .base import BotCheckin


class TerminusCheckin(BotCheckin):
    BOT_USER_ID = 1429576125
    BOT_NAME = "终点站"

    def _send_checkin(self):
        ret = self.client.send_message(chat_id=self.BOT_USER_ID, text="/cancel")
        ret.wait()
        super()._send_checkin()

    def _on_captcha(self, captcha: str):
        logger.debug(self.msg(f"接收到Captcha: {captcha}"))
        if len(captcha) != 2:
            self._send_checkin(retry=True)
        else:
            super()._on_captcha(captcha)

    def _on_text(self, text: str):
        if not any(s in text for s in ("会话已取消", "没有活跃的会话")):
            super()._on_text(text)
