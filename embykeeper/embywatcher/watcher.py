import asyncio
from datetime import datetime

from .emby import Connector, Emby, EmbyObject


def is_ok(co):
    if isinstance(co, tuple):
        co, *_ = co
    if 200 <= co < 300:
        return True

class EmbyWatcher:
    def __init__(self, emby: Emby):
        self.emby = emby

    def get_oldest(self, n=10):
        yield from self.emby.get_items(["Movie", "Episode"], limit=n, sort="DateCreated")

    def set_played(self, obj: EmbyObject):
        c: Connector = obj.connector
        return is_ok(c.post(f'/Users/{{UserId}}/PlayedItems/{obj.id}'))

    def hide_from_resume(self, obj:EmbyObject):
        c: Connector = obj.connector
        return is_ok(c.post(f'/Users/{{UserId}}/Items/{obj.id}/HideFromResume', hide=True))
    
    def get_last_played(self, obj: EmbyObject):
        last_played = obj.object_dict.get('UserData', {}).get('LastPlayedDate', None)
        return datetime.fromisoformat(last_played[:-2]) if last_played else None
    
    def play(self, obj: EmbyObject):
        c: Connector = obj.connector
        # 获取播放源
        resp = c.postJson(
            f"/Items/{obj.id}/PlaybackInfo",
            isPlayBack=True,
            AutoOpenLiveStream=True,
        )
        if not resp["MediaSources"]:
            return False
        else:
            play_session_id = resp["PlaySessionId"]
            media_source_id = resp["MediaSources"][0]["Id"]
        # 模拟播放
        timeout = c.timeout
        try:
            c.timeout = 5
            c.get(
                f"/Videos/{obj.id}/stream",
                static=True,
                playSessionId=play_session_id,
                MediaSourceId=media_source_id,
            )
        except asyncio.TimeoutError:
            pass
        finally:
            c.timeout = timeout
        # 设定播放状态
        playing_info = {
            'ItemId': obj.id,
            'PlayMethod': "DirectStream",
            "PlaySessionId": play_session_id,
            "MediaSourceId": media_source_id,
            "CanSeek": True
        }
        if not is_ok(c.post('/Sessions/Playing', **playing_info)):
            return False
        if not is_ok(c.post('/Sessions/Playing/Stopped', **playing_info)):
            return False
        return True
    