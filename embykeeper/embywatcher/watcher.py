import asyncio
from datetime import datetime
from typing import Union

from embypy.objects import Episode, Movie
from loguru import logger

from .emby import Connector, Emby, EmbyObject


def is_ok(co):
    if isinstance(co, tuple):
        co, *_ = co
    if 200 <= co < 300:
        return True


class EmbyWatcher:
    def __init__(self, emby: Emby):
        self.emby = emby

    async def get_oldest(self, n=10):
        items = await self.emby.get_items(["Movie", "Episode"], limit=n, sort="DateCreated")
        i: Union[Movie, Episode]
        for i in items:
            yield i

    @staticmethod
    async def set_played(obj: EmbyObject):
        c: Connector = obj.connector
        return is_ok(await c.post(f"/Users/{{UserId}}/PlayedItems/{obj.id}"))

    @staticmethod
    async def hide_from_resume(obj: EmbyObject):
        c: Connector = obj.connector
        return is_ok(await c.post(f"/Users/{{UserId}}/Items/{obj.id}/HideFromResume", hide=True))

    @staticmethod
    def get_last_played(obj: EmbyObject):
        last_played = obj.object_dict.get("UserData", {}).get("LastPlayedDate", None)
        return datetime.fromisoformat(last_played[:-2]) if last_played else None

    @staticmethod
    async def send_playing(obj: EmbyObject, playing_info):
        c: Connector = obj.connector
        while True:
            await c.post("/Sessions/Playing", **playing_info)
            asyncio.sleep(10)

    async def play(self, obj: EmbyObject, time=800, progress=1000):
        c: Connector = obj.connector
        # 检查
        if obj.object_dict.get('RunTimeTicks') < max(progress, time) * 10000000:
            return False
        # 获取播放源
        resp = await c.postJson(f"/Items/{obj.id}/PlaybackInfo", isPlayBack=True, AutoOpenLiveStream=True)
        if not resp["MediaSources"]:
            return False
        else:
            play_session_id = resp["PlaySessionId"]
            media_source_id = resp["MediaSources"][0]["Id"]
        # 模拟播放
        playing_info = {
            "ItemId": obj.id,
            "PlayMethod": "DirectStream",
            "PlaySessionId": play_session_id,
            "MediaSourceId": media_source_id,
            'PositionTicks': 10000000 * progress,
            "CanSeek": True,
        }
        send_playing_task = asyncio.create_task(self.send_playing(obj, playing_info))
        timeout = c.timeout
        try:
            c.timeout = time
            await c.get(
                f"/Videos/{obj.id}/stream",
                static=True,
                playSessionId=play_session_id,
                MediaSourceId=media_source_id,
            )
        except asyncio.TimeoutError:
            pass
        finally:
            c.timeout = timeout
        send_playing_task.cancel()
        if not is_ok(await c.post("/Sessions/Playing/Stopped", **playing_info)):
            return False
        return True
