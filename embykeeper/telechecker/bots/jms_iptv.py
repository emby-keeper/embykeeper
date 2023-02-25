from loguru import logger

from .base import AnswerBotCheckin


class JMSIPTVCheckin(AnswerBotCheckin):
    BOT_USER_ID = 5765103582
    BOT_NAME = "卷毛鼠IPTV"

    def _on_captcha(self, captcha: str):
        logger.debug(self.msg(f"接收到Captcha: {captcha}"))
        if len(captcha) != 5:
            self._send_checkin(retry=True)
        else:
            super()._on_captcha(captcha.upper())
