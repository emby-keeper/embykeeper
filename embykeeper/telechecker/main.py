from __future__ import annotations

import asyncio
from datetime import datetime
from functools import lru_cache
import inspect
import pkgutil
import random
import re
from typing import List, Type
from importlib import import_module

from loguru import logger

from ..utils import next_random_datetime
from . import __name__ as __product__
from .link import Link
from .tele import ClientsSession

from .bots._base import BaseBotCheckin, CheckinResult

logger = logger.bind(scheme="telegram")


def get_spec(type: str):
    """服务模块路径解析."""
    if type == "checkiner":
        sub = "bots"
        suffix = "checkin"
    elif type == "monitor":
        sub = "monitor"
        suffix = "monitor"
    elif type == "messager":
        sub = "messager"
        suffix = "messager"
    else:
        raise ValueError(f"{type} is not a valid service.")
    return sub, suffix


@lru_cache
def get_names(type: str, allow_ignore=False) -> List[str]:
    """列出服务中所有可用站点."""
    sub, _ = get_spec(type)
    results = []
    typemodule = import_module(f"{__product__}.{sub}")
    for _, mn, _ in pkgutil.iter_modules(typemodule.__path__):
        module = import_module(f"{__product__}.{sub}.{mn}")
        if not allow_ignore:
            if not getattr(module, "__ignore__", False):
                results.append(mn)
        else:
            if (not mn == "_base") and (not mn.startswith("test")):
                results.append(mn)
    return results


def get_cls(type: str, names: List[str] = None) -> List[Type]:
    """获得服务特定站点的所有类."""
    sub, suffix = get_spec(type)
    if names == None:
        names = get_names(type)
    results = []
    if type == "checkiner" and "sgk" in names:
        sgk_names = [n for n in get_names(type, allow_ignore=True) if n.endswith("sgk")]
        names = list(set(sgk_names))
    if "all" in names:
        all_names = get_names(type, allow_ignore=True)
        names = list(set(all_names))
    for name in names:
        match = re.match(r"templ_(\w+)<(\w+)>", name)
        if match:
            try:
                module = import_module(f"{__product__}.{sub}._templ_{match.group(1).lower()}")
                func = getattr(module, "use", None)
                if not func:
                    logger.warning(f'您配置的 "{type}" 不支持模板 "{match.group(1)}".')
                    continue
                results.append(func(bot_username=match.group(2), name=f"@{match.group(2)}"))
            except ImportError:
                all_names = get_names(type)
                logger.warning(f'您配置的 "{type}" 不支持站点 "{name}", 请从以下站点中选择:')
                logger.warning(", ".join(all_names))
        else:
            try:
                module = import_module(f"{__product__}.{sub}.{name.lower()}")
                for cn, cls in inspect.getmembers(module, inspect.isclass):
                    if (name.replace("_", "").replace("_old", "") + suffix).lower() == cn.lower():
                        results.append(cls)
            except ImportError:
                all_names = get_names(type)
                logger.warning(f'您配置的 "{type}" 不支持站点 "{name}", 请从以下站点中选择:')
                logger.warning(", ".join(all_names))
    return results


def extract(clss: List[Type]) -> List[Type]:
    """对于嵌套类, 展开所有子类."""
    extracted = []
    for cls in clss:
        ncs = [c for c in cls.__dict__.values() if inspect.isclass(c)]
        if ncs:
            extracted.extend(ncs)
        else:
            extracted.append(cls)
    return extracted


async def _checkin_task(checkiner: BaseBotCheckin, sem, wait=0):
    """签到器壳, 用于随机等待开始."""
    if wait > 0:
        checkiner.log.debug(f"随机启动等待: 将等待 {wait:.2f} 分钟以启动.")
    await asyncio.sleep(wait * 60)
    async with sem:
        return await checkiner._start()


async def _gather_task(tasks, username):
    return username, await asyncio.gather(*tasks)


async def checkiner(config: dict, instant=False):
    """签到器入口函数."""
    logger.debug("正在启动每日签到模块, 请等待登录.")
    async with ClientsSession.from_config(config) as clients:
        coros = []
        async for tg in clients:
            log = logger.bind(scheme="telechecker", username=tg.me.name)
            logger.info("已连接到 Telegram, 签到器正在初始化.")
            clses = extract(get_cls("checkiner", names=config.get("service", {}).get("checkiner", None)))
            if not clses:
                log.warning("没有任何有效签到站点, 签到将跳过.")
                continue
            if not await Link(tg).auth("checkiner", log_func=log.error):
                continue
            sem = asyncio.Semaphore(int(config.get("concurrent", 1)))
            checkiners: List[BaseBotCheckin] = [
                cls(
                    tg,
                    retries=config.get("retries", 4),
                    timeout=config.get("timeout", 240),
                    nofail=config.get("nofail", True),
                    basedir=config.get("basedir", None),
                    proxy=config.get("proxy", None),
                    config=config.get("checkiner", {}).get(cls.__module__.rsplit(".", 1)[-1], {}),
                    instant=instant,
                )
                for cls in clses
            ]
            tasks = []
            names = []
            for c in checkiners:
                names.append(c.name)
                wait = 0 if instant else random.uniform(0, int(config.get("random", 15)))
                task = asyncio.create_task(_checkin_task(c, sem, wait))
                tasks.append(task)
            coros.append(asyncio.ensure_future(_gather_task(tasks, username=tg.me.name)))
            if names:
                log.debug(f'已启用签到器: {", ".join(names)}')
        while coros:
            done, coros = await asyncio.wait(coros, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                try:
                    username, results = await t
                except asyncio.CancelledError:
                    continue
                log = logger.bind(scheme="telechecker", username=username)
                failed = []
                ignored = []
                successful = []
                checked = []
                for i, c in enumerate(checkiners):
                    if results[i] == CheckinResult.IGNORE:
                        ignored.append(c)
                    elif results[i] == CheckinResult.SUCCESS:
                        successful.append(c)
                    elif results[i] == CheckinResult.CHECKED:
                        checked.append(c)
                    else:
                        failed.append(c)
                spec = f"共{len(checkiners)}个"
                if successful:
                    spec += f", {len(successful)}成功"
                if checked:
                    spec += f", {len(checked)}已签到而跳过"
                if failed:
                    spec += f", {len(failed)}失败"
                if ignored:
                    spec += f", {len(ignored)}跳过"
                if failed:
                    if successful:
                        msg = "签到部分失败"
                    else:
                        msg = "签到失败"
                    log.error(f"{msg} ({spec}): {', '.join([f.name for f in failed])}")
                else:
                    log.bind(notify=True).info(f"签到成功 ({spec}).")


async def checkiner_schedule(config: dict, start_time=None, end_time=None, days: int = 1, instant=False):
    """签到器计划任务."""
    while True:
        dt = next_random_datetime(start_time, end_time, interval_days=days)
        logger.bind(scheme="telechecker").info(f"下一次签到将在 {dt.strftime('%m-%d %H:%M %p')} 进行.")
        await asyncio.sleep((dt - datetime.now()).total_seconds())
        await checkiner(config, instant=instant)


async def monitorer(config: dict):
    """监控器入口函数."""
    logger.debug("正在启动消息监控模块.")
    jobs = []
    async with ClientsSession.from_config(config, monitor=True) as clients:
        async for tg in clients:
            log = logger.bind(scheme="telemonitor", username=tg.me.name)
            logger.info("已连接到 Telegram, 监控器正在初始化.")
            clses = extract(get_cls("monitor", names=config.get("service", {}).get("monitor", None)))
            if not clses:
                log.warning("没有任何有效监控站点, 监控将跳过.")
            if not await Link(tg).auth("monitorer", log_func=log.error):
                continue
            names = []
            for cls in clses:
                cls_config = config.get("monitor", {}).get(cls.__module__.rsplit(".", 1)[-1], {})
                jobs.append(
                    asyncio.create_task(
                        cls(
                            tg,
                            nofail=config.get("nofail", True),
                            basedir=config.get("basedir", None),
                            proxy=config.get("proxy", None),
                            config=cls_config,
                        )._start()
                    )
                )
                names.append(cls.name)
            if names:
                log.debug(f'已启用监控器: {", ".join(names)}')
        await asyncio.gather(*jobs)


async def messager(config: dict):
    """自动水群入口函数."""
    logger.debug("正在启动自动水群模块.")
    messagers = []
    async with ClientsSession.from_config(config, send=True) as clients:
        async for tg in clients:
            log = logger.bind(scheme="telemessager", username=tg.me.name)
            logger.info("已连接到 Telegram, 自动水群正在初始化.")
            clses = extract(get_cls("messager", names=config.get("service", {}).get("messager", None)))
            if not clses:
                log.warning("没有任何有效自动水群站点, 自动水群将跳过.")
            if not await Link(tg).auth("messager", log_func=log.error):
                continue
            for cls in clses:
                cls_config = config.get("messager", {}).get(cls.__module__.rsplit(".", 1)[-1], {})
                messagers.append(
                    cls(
                        {"api_id": tg.api_id, "api_hash": tg.api_hash, "phone": tg.phone_number},
                        me=tg.me,
                        nofail=config.get("nofail", True),
                        proxy=config.get("proxy", None),
                        basedir=config.get("basedir", None),
                        config=cls_config,
                    )
                )
    await asyncio.gather(*[m._start() for m in messagers])
