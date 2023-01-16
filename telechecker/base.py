import re
from threading import Event

import ddddocr
from loguru import logger
from telegram.client import Telegram
from thefuzz import fuzz

ocr = ddddocr.DdddOcr(beta=True, show_ad=False)

class BotCheckin:
    BOT_CHAT_ID = None
    BOT_NAME = 'Bot'
    
    def __init__(self, client: Telegram, retries=10):
        self.client = client
        self.retries = retries
        self.ok = Event()
        self._downloaded_file_ids = []
        self._retries = 0
        
    def msg(self, line):
        return f'{self.BOT_NAME}> {line} ({self.client.username})'
    
    def checkin(self):
        self.client.add_update_handler('updateNewMessage', self._message_handler)
        self.client.add_update_handler('updateFile', self._captcha_handler)
        self._send_checkin()
        
    def _on_text(self, text: str):
        if any(s in text for s in ('失败', '错误', '超时')):
            return self._send_checkin(retry=True)
        elif any(s in text for s in ('成功', '通过', '完成')):
            self.ok.set()
            matches = re.search(r'(\d+)[^\d]*(\d+)', text)
            if matches:
                logger.warning(self.msg(f'签到成功: + {matches.group(1)} 分 -> {matches.group(2)} 分.'))
        elif any(s in text for s in ('只能', '已经', '下次', '过了')):
            self.ok.set()
            logger.warning(self.msg(f'今日已经签到过了.'))
        else:
            logger.warning(self.msg(f'接收到异常返回信息: {text}'))

    def _on_captcha(self, captcha: str):
        ret = self.client.send_message(chat_id=self.BOT_CHAT_ID, text=captcha)
        ret.wait()

    def _send_checkin(self, retry=False, cmd='/checkin'):
        if retry:
            self._retries += 1
        else:
            self._retries = 0
        if self._retries <= self.retries:
            ret = self.client.send_message(chat_id=self.BOT_CHAT_ID, text=cmd)
            ret.wait()
                
    def _message_parser(self, message, ignore=()):
        if message['is_outgoing']:
            return
        # 接收图片 - 读取或下载
        if 'photo' in message['content'] and 'photo' not in ignore:
            photo = message['content']['photo']['sizes'][0]['photo']
            if 'local' in photo:
                self._captcha_parser(photo['local']['path'])
            else:    
                self._download_photo(photo)
            return 'photo'
        # 接收文字 - 回调
        if 'text' in message['content'] and 'text' not in ignore:
            text = message['content']['text']['text']
            self._on_text(text)
            return 'text'
    
    def _message_handler(self, update):
        if 'message' in update:
            if update['message']['chat_id'] == self.BOT_CHAT_ID:
                self._message_parser(update['message'])
    
    def _captcha_parser(self, path):
        with open(path, 'rb') as f:
            image = f.read()
        self._on_captcha(ocr.classification(image))
    
    def _download_photo(self, photo):
        file_id = photo['id']
        self._downloaded_file_ids.append(file_id)
        ret = self.client.call_method(method_name='downloadFile', params={'file_id': file_id, 'priority': 1})
        ret.wait()
        if ret.error:
            logger.warning(self.msg(f'读取验证码图片异常错误.'))
    
    def _captcha_handler(self, update):
        if update['file']['id'] in self._downloaded_file_ids:
            if update['file']['local']['is_downloading_completed']:
                self._captcha_parser(update['file']['local']['path'])                
    
    def _download_history(self, limit=100):
        messages = []
        message_id = 0
        while True:
            ret = self.client.get_chat_history(self.BOT_CHAT_ID, from_message_id=message_id)
            ret.wait()
            updates = ret.update['messages']
            if not len(updates):
                break
            else:
                messages.extend(updates)
                message_id = messages[-1]['id']
            if len(messages) >= limit:
                break
        return messages[:limit]
            
    def _parse_history(self):
        for m in reversed(self._download_history()):
            self._message_parser(m, ignore=['text'])
            
class AnswerBotCheckin(BotCheckin):
    def __init__(self, client: Telegram, retries=10):
        super().__init__(client, retries)
        self._message = None
        self._answers = []
    
    def _on_captcha(self, captcha: str):
        match = [(a, fuzz.ratio(a['text'], captcha)) for a in self._answers]
        max_a, max_r = max(match, key=lambda x:x[1])
        if max_r < 75:
            logger.info(self.msg(f'未能找到对应 "{captcha}" 的按键, 正在重试.'))
            return self._send_checkin(retry=True)
        self._trigger_answer(max_a)
        
    def _message_parser(self, message, ignore=()):
        # 识别具有answers的消息
        if 'reply_markup' in message and 'answer' not in ignore:
            for row in message['reply_markup']['rows']:
                self._answers.extend(row)
            self._message = message
            return 'answer'
        super()._message_parser(message, ignore=ignore)
    
    def _trigger_answer(self, answer, message=None):
        if not message:
            message = self._message
        ret = self.client.call_method(
                method_name='getCallbackQueryAnswer',
                params={'chat_id': message['chat_id'],
                        'message_id': message['id'],
                        'payload': {
                            '@type': 'callbackQueryPayloadData',
                            'data': answer['type']['data']}})
        ret.wait()
        if ret.error:
            logger.info(self.msg('按键点击失败, 正在重试.'))
            return self._send_checkin(retry=True)
        
    def _parse_history(self):
        history = self._download_history()
        for m in reversed(history):
            self._message_parser(m, ignore=['photo', 'text'])
        for m in reversed(history):
            t = self._message_parser(m, ignore=['answer', 'text'])
            if t == 'photo':
                break