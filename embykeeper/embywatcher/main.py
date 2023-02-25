import random
import string
from datetime import datetime

from loguru import logger

from .emby import Emby, EmbyObject
from .watcher import EmbyWatcher


def _gen_random_device_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=16))


def main(config):
    proxy = config.get("proxy", {})
    if proxy:
        proxy = {
            "proxy_type": proxy.get("type", "socks5"),
            "proxy_host": proxy.get("host", "127.0.0.1"),
            "proxy_port": proxy.get("port", "1080"),
        }
    for a in config.get("emby", ()):
        logger.info(f'登录到Emby: {a["url"]}')
        emby = Emby(
            url=a["url"],
            username=a["username"],
            password=a["password"],
            device_id=_gen_random_device_id(),
            jellyfin=a.get("jellyfin", False),
            **proxy,
        )
        info = emby.info()
        if info:
            logger.info(f'成功登录Emby: {info["ServerName"]} ({info["Version"]})')
            msg = lambda x: f'{x} ({info["ServerName"]})'
        else:
            logger.error(f'Emby ({a["url"]}) 无法获取元信息而跳过, 请重新检查配置.')
            continue
        watcher = EmbyWatcher(emby)
        obj: EmbyObject
        for i, obj in enumerate(watcher.get_oldest()):
            if i == 0:
                logger.info(msg(f'开始尝试播放 "{obj.name}".'))
            else:
                logger.warning(msg(f'发生错误, 重新开始尝试播放 "{obj.name}".'))
            try:
                if watcher.play(obj):
                    obj.update()
                    if obj.play_count < 1:
                        continue
                    last_played = watcher.get_last_played(obj)
                    if not last_played:
                        continue
                    last_played = last_played.strftime("%Y-%m-%d %H:%M:%S")
                    logger.info(
                        msg(f"成功播放视频, 当前该视频播放{obj.play_count}次, 上次播放于 {last_played}.")
                    )
                    break
            except KeyboardInterrupt as e:
                raise e from None
            except Exception as e:
                logger.debug(e)
                continue
            finally:
                watcher.hide_from_resume(obj)
        else:
            logger.error(msg(f"由于没有成功播放的视频, 保活失败, 请重新检查配置."))
