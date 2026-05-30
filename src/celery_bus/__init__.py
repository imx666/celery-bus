"""
celery-bus
==========
基于 Celery 的任务总线基础设施层。

提供：注册（TaskRegistry）/ 发送（CeleryBoss）/ 构建（build_app）/
调度（build_beat_schedule）/ 监控（FlowerClient）。

快速开始::

    from celery_bus.registry import TaskRegistry
    from celery_bus.boss import init_boss, send_celery_task
    from celery_bus.apps import build_app
    from celery_bus.beat import attach_beat_schedule
    from celery_bus.inspector import FlowerClient
"""

from celery_bus.registry import TaskSpec, TaskRegistry
from celery_bus.boss import CeleryBoss, init_boss, get_boss, send_celery_task
from celery_bus.apps import build_app
from celery_bus.beat import build_beat_schedule, attach_beat_schedule
from celery_bus.inspector import FlowerClient, FlowerTaskTracker
from celery_bus.config import BaseCeleryConfig

__all__ = [
    # registry
    "TaskSpec",
    "TaskRegistry",
    # boss
    "CeleryBoss",
    "init_boss",
    "get_boss",
    "send_celery_task",
    # apps
    "build_app",
    # beat
    "build_beat_schedule",
    "attach_beat_schedule",
    # inspector
    "FlowerClient",
    "FlowerTaskTracker",
    # config
    "BaseCeleryConfig",
]
