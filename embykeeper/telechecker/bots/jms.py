from loguru import logger

from .base import AnswerBotCheckin


class JMSCheckin(AnswerBotCheckin):
    BOT_CHAT_ID = 1723810586
    BOT_NAME = "卷毛鼠"

    def _on_captcha(self, captcha: str):
        logger.debug(self.msg(f"接收到Captcha: {captcha}"))
        if len(captcha) != 4:
            self._send_checkin(retry=True)
        else:
            for letter in captcha:
                for answer in self._answers:
                    if answer["text"] == letter:
                        self._trigger_answer(answer)
                        break
                else:
                    logger.info(self.msg(f'未能找到对应 "{letter}" 的按键, 正在重试.'))
                    return self._send_checkin(retry=True)
