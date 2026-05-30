"""
boss.py
=======
Celery 任务发送端。

独立包版本改造要点：
- broker_url 通过 CeleryBoss 构造函数传入，无 import-time 副作用
- logger 可注入，默认用 stdlib logging
- 保留模块级兼容函数（init_boss / get_boss / send_celery_task）供平滑迁移

用法::

    boss = CeleryBoss(broker_url="redis://:pwd@host:6379/0")
    task_id = boss.send("news.filter", "news_filter_queue", kwargs_dict={...})
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from celery import Celery
from celery.result import AsyncResult

_LOGGER = logging.getLogger(__name__)


class CeleryBoss:
    """
    Celery 任务总线发送端。

    内部持有一个仅用于 send_task 的轻量 Celery 实例，不注册任何 task。
    """

    def __init__(self, broker_url: str, *, logger=None):
        self._app: Celery = Celery(broker=broker_url, backend=broker_url)
        self.logger = logger or _LOGGER

    def send(
        self,
        task_name: str,
        task_queue: str,
        kwargs_dict: Optional[dict[str, Any]] = None,
        task_id: Optional[str] = None,
        *,
        target_broker_url: Optional[str] = None,
    ) -> Optional[str]:
        """发送一个 celery task。

        Args:
            task_name        : celery task 全名（需与 worker 侧 @app.task(name=...) 一致）
            task_queue       : 目标队列名
            kwargs_dict      : 任务 kwargs；会自动注入 task_sent_at 时间戳
            task_id          : 自定义 task_id；None 时由 Celery 自动生成
            target_broker_url: 临时覆盖 broker 地址（跨 broker 投递场景）

        Returns:
            成功返回 task_id 字符串，失败返回 None。
        """
        kwargs_dict = dict(kwargs_dict or {})
        kwargs_dict.setdefault("task_sent_at", time.time())

        if target_broker_url is not None:
            self._app.conf.broker_url = target_broker_url
            safe_host = target_broker_url.split("@")[-1]
            self.logger.info(f"[celery-boss] 切换 broker -> {safe_host}")

        started = time.time()
        try:
            result: AsyncResult = self._app.send_task(
                task_name,
                kwargs=kwargs_dict,
                queue=task_queue,
                task_id=task_id,
            )
        except Exception as exc:
            elapsed = round(time.time() - started, 6)
            self.logger.error(
                f"[celery-boss] send FAIL task={task_name} queue={task_queue} "
                f"elapsed={elapsed}s err={exc}"
            )
            return None

        elapsed = round(time.time() - started, 6)
        self.logger.debug(
            f"[celery-boss] send OK task={task_name} queue={task_queue} "
            f"task_id={result.id} elapsed={elapsed}s"
        )
        return result.id


# ======================== 模块级兼容 API ========================
# 对标 honeycomb_bus.boss 的 init_boss / get_boss / send_honeycomb_task 模式。

_default_boss: CeleryBoss | None = None


def init_boss(broker_url: str, *, logger=None) -> CeleryBoss:
    """初始化默认 CeleryBoss 单例（项目启动时调用一次）。"""
    global _default_boss
    _default_boss = CeleryBoss(broker_url, logger=logger)
    return _default_boss


def get_boss() -> CeleryBoss:
    """获取默认 CeleryBoss 单例。"""
    if _default_boss is None:
        raise RuntimeError("请先调用 celery_bus.boss.init_boss(broker_url) 初始化")
    return _default_boss


def send_celery_task(
    task_name: str,
    task_queue: str,
    kwargs_dict: Optional[dict[str, Any]] = None,
    task_id: Optional[str] = None,
    logger=None,
    target_celery_broker_url: Optional[str] = None,
) -> Optional[str]:
    """模块级发送函数（兼容旧版签名）。需先调用 init_boss()。"""
    boss = get_boss()
    if logger is not None:
        boss.logger = logger
    return boss.send(
        task_name,
        task_queue,
        kwargs_dict=kwargs_dict,
        task_id=task_id,
        target_broker_url=target_celery_broker_url,
    )
