from loguru import logger

from .base import AnswerBotCheckin


class LJYYCheckin(AnswerBotCheckin):
    BOT_CHAT_ID = 1794080358
    BOT_NAME = "垃圾影音"

    def checkin(self):
        super().checkin()
        self._parse_history()

    def _send_checkin(self, retry=False):
        for a in self._answers:
            self._trigger_answer(a)
            break
        super()._send_checkin(retry=retry)

    def _on_captcha(self, captcha: str):
        logger.debug(self.msg(f"接收到Captcha: {captcha}"))
        if len(captcha) != 4:
            self._send_checkin(retry=True)
        else:
            super()._on_captcha(captcha)
