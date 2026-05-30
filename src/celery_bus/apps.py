"""
apps.py
=======
Celery 实例工厂。

从 TaskRegistry 派生 imports / task_routes，确保 worker 启动入口和注册表始终同步。

用法::

    from celery_bus.apps import build_app
    from celery_bus.registry import TaskRegistry

    TaskRegistry.register("news.filter", app="alchemist", ...)
    APP_ALCHEMIST = build_app("alchemist", broker_url="redis://...")

worker 启动::

    celery -A your_project.celery_app:APP_ALCHEMIST worker -l info -Q news_filter_queue
"""
from __future__ import annotations

import logging
from typing import Optional

from celery import Celery

from .config import BaseCeleryConfig
from .registry import TaskRegistry

_LOGGER = logging.getLogger(__name__)


class _CeleryTraceRuntimePrecisionFilter(logging.Filter):
    """将 Celery success-log 里的 runtime 四舍五入到 4 位，避免超长浮点数。"""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, dict) and isinstance(args.get("runtime"), float):
            rounded = dict(args)
            rounded["runtime"] = round(args["runtime"], 4)
            record.args = rounded
        return True


def _install_trace_filter() -> None:
    logger = logging.getLogger("celery.app.trace")
    if not any(isinstance(f, _CeleryTraceRuntimePrecisionFilter) for f in logger.filters):
        logger.addFilter(_CeleryTraceRuntimePrecisionFilter())


def build_app(app_name: str, broker_url: str, *, celery_name: Optional[str] = None) -> Celery:
    """
    构建单个 Celery 实例，imports / task_routes 全部从 TaskRegistry 派生。

    Args:
        app_name    : 业务 app 名，用于从 TaskRegistry 过滤归属该 app 的 task
        broker_url  : broker（同时作为 backend）连接 URL
        celery_name : Celery 实例名（``celery -A`` 的入口标识）；
                      默认为 ``"celery_bus_{app_name}"``

    Returns:
        已配置好 imports / task_routes 的 Celery 实例。
    """
    _install_trace_filter()

    specs = TaskRegistry.specs_of(app_name)
    if not specs:
        _LOGGER.warning(f"[celery-bus] build_app: app={app_name!r} 下无已注册 task，"
                        "请确认 TaskRegistry.register() 已在 build_app() 之前调用")

    name = celery_name or f"celery_bus_{app_name}"
    app = Celery(name, broker=broker_url, backend=broker_url)
    app.config_from_object(BaseCeleryConfig)

    # imports 去重（多 task 可能来自同一模块）
    app.conf.imports = tuple(sorted({s.import_path for s in specs}))
    app.conf.task_routes = {s.name: {"queue": s.queue} for s in specs}

    return app
