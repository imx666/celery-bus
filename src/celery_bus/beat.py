"""
beat.py
=======
Celery Beat 调度工具（Option A：包提供 builder，项目侧提供 schedule 数据）。

beat_schedule 数据通过 TaskSpec.schedule / schedule_kwargs 字段定义在项目的
TaskRegistry 里，本模块只负责把它们派生成 Celery 所需的 dict 格式并挂载。

beat 启动（项目侧）::

    celery -A your_project.celery_beat:APP_ALCHEMIST beat -l info

项目侧 celery_beat.py 示例::

    from celery_bus.beat import attach_beat_schedule
    from your_project.celery_app import APP_ALCHEMIST

    attach_beat_schedule(APP_ALCHEMIST, "alchemist")
"""
from __future__ import annotations

from celery import Celery

from .registry import TaskRegistry


def build_beat_schedule(app_name: str) -> dict:
    """
    从 TaskRegistry 过滤出 schedule != None 的 TaskSpec，构建 beat_schedule dict。

    entry key 取 task 名最后一段（e.g. "news.enrich" -> "enrich"），
    便于在 beat 日志中快速对齐。若两个 task 尾段相同，直接抛错而非静默覆盖。
    """
    schedule: dict = {}
    for spec in TaskRegistry.specs_of(app_name):
        if spec.schedule is None:
            continue
        entry: dict = {
            "task": spec.name,
            "schedule": spec.schedule,
            "options": {"queue": spec.queue},
        }
        if spec.schedule_kwargs:
            entry["kwargs"] = dict(spec.schedule_kwargs)

        short_key = spec.name.split(".")[-1]
        if short_key in schedule:
            raise RuntimeError(
                f"beat_schedule key 冲突: {short_key!r} 已存在 "
                f"({schedule[short_key]['task']} vs {spec.name})，"
                f"请为其中一个 task 改名或使用不同的尾段"
            )
        schedule[short_key] = entry
    return schedule


def attach_beat_schedule(app: Celery, app_name: str) -> None:
    """将 beat_schedule 挂载到已有的 Celery 实例上。

    在项目侧 celery_beat.py 的模块级调用，beat 进程启动时会读取 app.conf.beat_schedule。
    """
    app.conf.beat_schedule = build_beat_schedule(app_name)
