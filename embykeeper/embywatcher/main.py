from __future__ import annotations

import asyncio
import random
import string
from typing import TYPE_CHECKING, Iterable, Union
from datetime import datetime, time, timezone
import uuid
import warnings

from aiohttp import ClientError, ClientConnectionError
from loguru import logger

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from embypy.objects import Episode, Movie

from ..utils import show_exception, next_random_datetime, truncate_str
from ..var import debug
from .emby import Emby, Connector, EmbyObject

if TYPE_CHECKING:
    from loguru import Logger

logger = logger.bind(scheme="embywatcher")


class PlayError(Exception):
    pass


def is_ok(co):
    """判定返回来自 emby 的响应为成功."""
    if isinstance(co, tuple):
        co, *_ = co
    if 200 <= co < 300:
        return True


async def get_random_media(emby: Emby):
    """获取随机视频."""
    while True:
        items = await emby.get_items(["Movie", "Episode"], limit=10, sort="Random", ascending=False)
        i: Union[Movie, Episode]
        for i in items:
            yield i


async def set_played(obj: EmbyObject):
    """设定已播放."""
    c: Connector = obj.connector
    return is_ok(await c.post(f"/Users/{{UserId}}/PlayedItems/{obj.id}"))


async def hide_from_resume(obj: EmbyObject):
    """从首页的"继续收看"部分隐藏."""
    c: Connector = obj.connector
    try:
        return is_ok(await c.post(f"/Users/{{UserId}}/Items/{obj.id}/HideFromResume", Hide=True))
    except RuntimeError:
        return False


def get_last_played(obj: EmbyObject):
    """获取上次播放时间."""
    last_played = obj.object_dict.get("UserData", {}).get("LastPlayedDate", None)
    return datetime.fromisoformat(last_played[:-2]) if last_played else None


async def play(obj: EmbyObject, loggeruser: Logger, time: float = 10):
    """模拟播放视频."""
    c: Connector = obj.connector

    await asyncio.sleep(random.uniform(1, 3))

    # 检查
    totalticks = obj.object_dict.get("RunTimeTicks")
    if not totalticks:
        raise PlayError("无法获取视频长度")
    if time:
        if totalticks < time * 10000000:
            raise PlayError("视频长度低于观看进度所需")
    else:
        time = totalticks / 10000000

    await asyncio.sleep(random.uniform(1, 3))

    # 获取页面信息
    resp = await c.getJson(
        f"/Videos/{obj.id}/AdditionalParts",
        Fields="PrimaryImageAspectRatio,UserData,CanDelete",
        IncludeItemTypes="Playlist,BoxSet",
        Recursive=True,
        SortBy="SortName",
    )

    await asyncio.sleep(random.uniform(1, 3))

    # 获取播放源
    resp = await c.postJson(
        f"/Items/{obj.id}/PlaybackInfo",
        UserID=c.userid,
        StartTimeTicks=0,
        IsPlayback=True,
        AutoOpenLiveStream=True,
        MaxStreamingBitrate=42000000,
    )
    play_session_id = resp.get("PlaySessionId", "")
    if "MediaSources" in resp:
        media_source_id = resp["MediaSources"][0]["Id"]
        direct_stream_id = resp["MediaSources"][0].get("DirectStreamUrl", None)
    else:
        media_source_id = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(32))
        direct_stream_id = None

    await asyncio.sleep(random.uniform(1, 3))

    # 模拟播放
    playing_info = lambda tick: {
        "VolumeLevel": 100,
        "CanSeek": True,
        "BufferedRanges": [{"start": 0, "end": tick}] if tick else [],
        "IsPaused": False,
        "ItemId": obj.id,
        "MediaSourceId": media_source_id,
        "PlayMethod": "DirectStream",
        "PlaySessionId": play_session_id,
        "PlaybackStartTimeTicks": datetime.now().timestamp() * 10000000,
        "PlaylistIndex": 0,
        "PlaylistLength": 1,
        "PositionTicks": tick,
        "RepeatMode": "RepeatNone",
    }

    task = asyncio.create_task(c.get_stream_noreturn(direct_stream_id or f"/Videos/{obj.id}/stream"))

    await asyncio.sleep(random.uniform(1, 3))

    if not is_ok(await c.post("Sessions/Playing", MediaSourceId=media_source_id, data=playing_info(0.1))):
        raise PlayError("无法开始播放")

    t = time
    last_report_t = t
    while t > 0:
        if last_report_t and last_report_t - t > (5 if debug else 30):
            loggeruser.info(f'正在播放: "{truncate_str(obj.name, 10)}" (还剩 {t:.0f} 秒).')
            last_report_t = t
        st = random.uniform(2, 5)
        await asyncio.sleep(st)
        t -= st
        tick = int((time - t) * 10000000)
        payload = playing_info(tick)
        try:
            resp = await asyncio.wait_for(
                c.post("/Sessions/Playing/Progress", data=payload, EventName="timeupdate"), 10
            )
        except (
            ClientError,
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            asyncio.IncompleteReadError,
        ) as e:
            if isinstance(e, asyncio.IncompleteReadError):
                await c._reset_session()
            loggeruser.debug(f"播放状态设定错误: {e}")
        else:
            if not is_ok(resp):
                loggeruser.debug(f"播放状态设定错误: {resp}")

    await asyncio.sleep(random.uniform(1, 3))

    if not is_ok(await c.post("/Sessions/Playing/Stopped", data=playing_info(time * 10000000))):
        raise PlayError("无法停止播放")
    else:
        loggeruser.info(f"播放完成, 共 {time} 秒.")

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        loggeruser.warning(f"模拟播放时, 访问流媒体文件失败.")
        show_exception(e)
    return True


async def login(config, continuous=False):
    """登录账号."""
    for a in config.get("emby", ()):
        if not continuous == a.get("continuous", False):
            continue
        logger.info(f'登录账号: "{a["username"]}" 至服务器: "{a["url"]}"')
        emby = Emby(
            url=a["url"],
            username=a["username"],
            password=a["password"],
            jellyfin=a.get("jellyfin", False),
            proxy=config.get("proxy", None),
            ua=a.get("ua", None),
            device=a.get("device", None),
            client=a.get("client", None),
            device_id=str(uuid.uuid4()).upper(),
        )
        try:
            info = await emby.info()
        except (ConnectionError, RuntimeError, ClientConnectionError) as e:
            logger.error(f'Emby ({a["url"]}) 连接错误, 请重新检查配置: {e}')
            continue
        if info:
            loggeruser = logger.bind(server=info["ServerName"], username=a["username"])
            loggeruser.info(
                f'成功登录至服务器 "{a["url"]}" ({"Jellyfin" if a.get("jellyfin", False) else "Emby"} {info["Version"]}).'
            )
            yield (
                emby,
                loggeruser,
                a.get("time", None if continuous else [120, 240]),
                True if continuous else a.get("allow_multiple", True),
            )
        else:
            logger.error(f'Emby ({a["url"]}) 无法获取元信息而跳过, 请重新检查配置.')
            continue


async def watch(emby: Emby, loggeruser: Logger, time: float, retries: int = 5):
    """
    主执行函数 - 观看一个视频.
    参数:
        emby: Emby 客户端
        time: 模拟播放时间
        progress: 播放后设定的观看进度
        loggeruser: 日志器
        retries: 最大重试次数
    """
    retry = 0
    while True:
        try:
            async for obj in get_random_media(emby):
                if isinstance(time, Iterable):
                    t = random.uniform(*time) + 10
                else:
                    t = time + 10
                loggeruser.info(f'开始尝试播放 "{truncate_str(obj.name, 10)}" ({t:.0f} 秒).')
                while True:
                    try:
                        await play(obj, loggeruser, time=t)

                        obj = await obj.update("UserData")

                        if obj.play_count < 1:
                            raise PlayError("尝试播放后播放数低于1")

                        last_played = get_last_played(obj)
                        if not last_played:
                            raise PlayError("尝试播放后无记录")

                        last_played = (
                            last_played.replace(tzinfo=timezone.utc)
                            .astimezone(tz=None)
                            .strftime("%m-%d %H:%M")
                        )

                        prompt = (
                            f"[yellow]成功播放视频[/], "
                            + f"当前该视频播放 {obj.play_count} 次, "
                            + f"上次播放于 {last_played} UTC."
                        )
                        loggeruser.bind(notify="成功保活.").info(prompt)
                        return True
                    except (ClientError, OSError, asyncio.IncompleteReadError) as e:
                        retry += 1
                        if retry > retries:
                            loggeruser.warning(f"超过最大重试次数, 保活失败: {e}.")
                            return False
                        else:
                            if isinstance(e, asyncio.IncompleteReadError):
                                await emby.connector._reset_session()
                            rt = random.uniform(30, 60)
                            loggeruser.info(f"连接失败, 等待 {rt:.0f} 秒后重试: {e}.")
                            await asyncio.sleep(rt)
                    except PlayError as e:
                        retry += 1
                        if retry > retries:
                            loggeruser.warning(f"超过最大重试次数, 保活失败: {e}.")
                            return False
                        else:
                            rt = random.uniform(30, 60)
                            loggeruser.info(f"发生错误, 等待 {rt:.0f} 秒后重试其他视频: {e}.")
                            await asyncio.sleep(rt)
                        break
                    finally:
                        try:
                            if not await asyncio.shield(asyncio.wait_for(hide_from_resume(obj), 5)):
                                loggeruser.debug(f"未能成功从最近播放中隐藏视频.")
                        except asyncio.TimeoutError:
                            loggeruser.debug(f"从最近播放中隐藏视频超时.")
                        else:
                            loggeruser.info(f"已从最近播放中隐藏该视频.")
            else:
                loggeruser.warning(f"由于没有成功播放视频, 保活失败, 请重新检查配置.")
                return False
        except (ClientError, OSError, asyncio.IncompleteReadError) as e:
            retry += 1
            if retry > retries:
                loggeruser.warning(f"超过最大重试次数, 保活失败: {e}.")
                return False
            else:
                if isinstance(e, asyncio.IncompleteReadError):
                    await emby.connector._reset_session()
                rt = random.uniform(30, 60)
                loggeruser.info(f"连接失败, 等待 {rt:.0f} 秒后重试: {e}.")
                await asyncio.sleep(rt)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            loggeruser.warning(f"发生错误, 保活失败.")
            show_exception(e, regular=False)
            return False


async def watch_multiple(emby: Emby, loggeruser: Logger, time: float, retries: int = 5):
    if isinstance(time, Iterable):
        req_time = random.uniform(*time) + 10
    else:
        req_time = time + 10
    loggeruser.info(f"开始播放视频 (允许播放多个), 共需播放 {req_time:.0f} 秒.")
    played_time = 0
    played_videos = 0
    retry = 0
    while True:
        try:
            async for obj in get_random_media(emby):
                totalticks = obj.object_dict.get("RunTimeTicks")
                if not totalticks:
                    rt = random.uniform(30, 60)
                    loggeruser.info(
                        f'无法获取视频 "{truncate_str(obj.name, 10)}" 长度, 等待 {rt:.0f} 秒后重试.'
                    )
                    await asyncio.sleep(rt)
                    continue
                totaltime = totalticks / 10000000
                if req_time - played_time > totaltime:
                    play_time = totaltime
                else:
                    play_time = max(req_time - played_time, 10)
                loggeruser.info(f'开始尝试播放 "{truncate_str(obj.name, 10)}" ({play_time:.0f} 秒).')
                while True:
                    try:
                        await play(obj, loggeruser, time=play_time)

                        obj = await obj.update("UserData")

                        if obj.play_count < 1:
                            raise PlayError("尝试播放后播放数低于1")

                        last_played = get_last_played(obj)
                        if not last_played:
                            raise PlayError("尝试播放后无记录")

                        last_played = (
                            last_played.replace(tzinfo=timezone.utc)
                            .astimezone(tz=None)
                            .strftime("%m-%d %H:%M")
                        )

                        prompt = (
                            f"[yellow]成功播放视频[/], "
                            + f"当前该视频播放 {obj.play_count} 次, "
                            + f"上次播放于 {last_played} UTC."
                        )
                        loggeruser.info(prompt)
                        played_videos += 1
                        played_time += play_time

                        if played_time >= req_time - 1:
                            loggeruser.bind(notify="成功保活.").info(
                                f"保活成功, 共播放 {played_videos} 个视频."
                            )
                            return True
                        else:
                            loggeruser.info(f"还需播放 {req_time - played_time:.0f} 秒.")
                            rt = random.uniform(30, 60)
                            loggeruser.info(f"等待 {rt:.0f} 秒后播放下一个.")
                            await asyncio.sleep(rt)
                            break
                    except (ClientError, OSError, asyncio.IncompleteReadError) as e:
                        retry += 1
                        if retry > retries:
                            loggeruser.warning(f"超过最大重试次数, 保活失败: {e}.")
                            return False
                        else:
                            if isinstance(e, asyncio.IncompleteReadError):
                                await emby.connector._reset_session()
                            rt = random.uniform(30, 60)
                            loggeruser.info(f"连接失败, 等待 {rt:.0f} 秒后重试: {e}.")
                            await asyncio.sleep(rt)
                    except PlayError as e:
                        retry += 1
                        if retry > retries:
                            loggeruser.warning(f"超过最大重试次数, 保活失败: {e}.")
                            return False
                        else:
                            rt = random.uniform(30, 60)
                            loggeruser.info(f"发生错误, 等待 {rt:.0f} 秒后重试其他视频: {e}.")
                            await asyncio.sleep(rt)
                        break
                    finally:
                        try:
                            if not await asyncio.shield(asyncio.wait_for(hide_from_resume(obj), 5)):
                                loggeruser.debug(f"未能成功从最近播放中隐藏视频.")
                        except asyncio.TimeoutError:
                            loggeruser.debug(f"从最近播放中隐藏视频超时.")
                        else:
                            loggeruser.info(f"已从最近播放中隐藏该视频.")
            else:
                loggeruser.warning(f"由于没有成功播放视频, 保活失败, 请重新检查配置.")
                return False
        except (ClientError, OSError, asyncio.IncompleteReadError) as e:
            retry += 1
            if retry > retries:
                loggeruser.warning(f"超过最大重试次数, 保活失败: {e}.")
                return False
            else:
                if isinstance(e, asyncio.IncompleteReadError):
                    await emby.connector._reset_session()
                rt = random.uniform(30, 60)
                loggeruser.info(f"连接失败, 等待 {rt:.0f} 秒后重试: {e}.")
                await asyncio.sleep(rt)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            loggeruser.warning(f"发生错误, 保活失败.")
            show_exception(e, regular=False)
            return False


async def watch_continuous(emby: Emby, loggeruser: Logger):
    """
    主执行函数 - 持续观看.

    参数:
        emby: Emby 客户端
        loggeruser: 日志器
    """
    while True:
        try:
            async for obj in get_random_media(emby):
                totalticks = obj.object_dict.get("RunTimeTicks")
                if not totalticks:
                    rt = random.uniform(30, 60)
                    loggeruser.info(f"无法获取视频长度, 等待 {rt:.0f} 秒后重试.")
                    await asyncio.sleep(rt)
                    continue
                totaltime = totalticks / 10000000
                loggeruser.info(f'开始尝试播放 "{truncate_str(obj.name, 10)}" (长度 {totaltime:.0f} 秒).')
                try:
                    await play(obj, loggeruser, time=0)
                except PlayError as e:
                    rt = random.uniform(30, 60)
                    loggeruser.info(f"发生错误, 等待 {rt:.0f} 秒后重试: {e}.")
                    await asyncio.sleep(rt)
                    continue
                finally:
                    try:
                        if not await asyncio.shield(asyncio.wait_for(hide_from_resume(obj), 2)):
                            loggeruser.debug(f"未能成功从最近播放中隐藏视频.")
                    except asyncio.TimeoutError:
                        loggeruser.debug(f"从最近播放中隐藏视频超时.")
        except (ClientError, OSError, asyncio.IncompleteReadError) as e:
            if isinstance(e, asyncio.IncompleteReadError):
                await emby.connector._reset_session()
            rt = random.uniform(30, 60)
            loggeruser.info(f"连接失败, 等待 {rt:.0f} 秒后重试: {e}.")
            await asyncio.sleep(rt)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            loggeruser.warning(f"发生错误, 停止持续播放.")
            show_exception(e, regular=False)
            return False


async def watcher(config: dict, debug=False):
    """入口函数 - 观看一个视频."""

    async def wrapper(emby: Emby, loggeruser: Logger, time: float, multiple: bool):
        try:
            if not debug:
                wait = random.uniform(180, 360)
                loggeruser.info(f"播放视频前随机等待 {wait:.0f} 秒.")
                await asyncio.sleep(wait)
            else:
                loggeruser.warning("处于调试模式, 播放前模拟挑选随机等待被跳过.")
            if isinstance(time, Iterable):
                tm = max(time) * 2
            else:
                tm = time * 2
            if multiple:
                return await asyncio.wait_for(watch_multiple(emby, loggeruser, time), max(tm, 180))
            else:
                return await asyncio.wait_for(watch(emby, loggeruser, time), max(tm, 180))
        except asyncio.TimeoutError:
            loggeruser.warning(f"一定时间内未完成播放, 保活失败.")
            return False

    logger.info("开始执行 Emby 保活.")
    tasks = []
    async for emby, loggeruser, time, multiple in login(config):
        tasks.append(wrapper(emby, loggeruser, time, multiple))
    if not tasks:
        logger.info("没有指定相关的 Emby 服务器, 跳过保活.")
    results = await asyncio.gather(*tasks)
    fails = len(tasks) - sum(results)
    if fails:
        logger.error(f"保活失败 ({fails}/{len(tasks)}).")


async def watcher_schedule(
    config: dict, start_time=time(11, 0), end_time=time(23, 0), days: int = 7, debug: bool = False
):
    """计划任务 - 观看一个视频."""
    while True:
        dt = next_random_datetime(start_time, end_time, interval_days=days)
        logger.bind(scheme="embywatcher").info(f"下一次保活将在 {dt.strftime('%m-%d %H:%M %p')} 进行.")
        await asyncio.sleep((dt - datetime.now()).total_seconds())
        await watcher(config, debug=debug)


async def watcher_continuous(config: dict):
    """入口函数 - 持续观看."""

    async def wrapper(emby: Emby, loggeruser: Logger, time: float):
        if time:
            if isinstance(time, Iterable):
                time = random.uniform(*time)
            loggeruser.info(f"即将连续播放视频, 持续 {time:.0f} 秒.")
        else:
            loggeruser.info(f"即将无限连续播放视频.")
        try:
            await asyncio.wait_for(watch_continuous(emby, loggeruser), time)
        except asyncio.TimeoutError:
            loggeruser.info(f"连续播放结束.")
            return True
        else:
            return False

    logger.info("开始执行 Emby 持续观看.")
    tasks = []
    async for emby, loggeruser, time, _ in login(config, continuous=True):
        tasks.append(wrapper(emby, loggeruser, time))
    if not tasks:
        logger.info("没有指定相关的 Emby 服务器, 跳过持续观看.")
    return await asyncio.gather(*tasks)


async def watcher_continuous_schedule(
    config: dict, start_time=time(11, 0), end_time=time(23, 0), days: int = 1
):
    """计划任务 - 持续观看."""

    t = asyncio.create_task(watcher_continuous(config))
    while True:
        dt = next_random_datetime(start_time, end_time, interval_days=days)
        logger.bind(scheme="embywatcher").info(
            f"持续观看结束后, 将在 {dt.strftime('%m-%d %H:%M %p')} 再次开始."
        )
        await asyncio.sleep((dt - datetime.now()).total_seconds())
        if not t.done():
            t.cancel()
        t = asyncio.create_task(watcher_continuous(config))
