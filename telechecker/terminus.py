from loguru import logger

from .base import BotCheckin


class TerminusCheckin(BotCheckin):
    BOT_CHAT_ID = 1429576125
    BOT_NAME = '终点站'
    
    def _send_checkin(self):
        ret = self.client.send_message(chat_id=self.BOT_CHAT_ID, text='/cancel')
        ret.wait()
        super()._send_checkin()
    
    def _on_captcha(self, captcha: str):
        logger.debug(self.msg(f'接收到Captcha: {captcha}'))
        if len(captcha) != 2:
            self._send_checkin(retry=True)
        else:
            super()._on_captcha(captcha)
            
    def _on_text(self, text: str):
        if '没有活跃的会话' not in text:
            super()._on_text(text)
