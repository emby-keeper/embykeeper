# 该文件用于同机器人 Messager, Monitor 和 Bots 之间的异步锁和通讯

import asyncio

from cachetools import TTLCache

ocrs = TTLCache(maxsize=1024, ttl=3600)
ocrs_lock = asyncio.Lock()

misty_monitors = {}
misty_locks = {}

pornemby_status = {"nohp": None}
