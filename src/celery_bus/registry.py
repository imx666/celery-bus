"""
registry.py
===========
Celery task 注册表 —— 单一事实源（SSOT）。

独立包版本：提供 TaskRegistry.register() API，业务方自行注册 task。
不内置任何业务 task。

使用方式::

    from celery_bus.registry import TaskRegistry

    TaskRegistry.register(
        "news.filter",
        app="alchemist",
        queue="news_filter_queue",
        import_path="news_pipeline.filter.cwkr",
    )
    spec = TaskRegistry.get("news.filter")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class TaskSpec:
    """单个 celery task 的注册信息。

    字段:
        name            : celery task 全名，唯一主键；worker 侧 @app.task(name=...) 必须一致。
                          建议格式 "<业务域>.<动作>"，e.g. "news.enrich"
        app             : 归属哪个 Celery 实例名（项目侧自定义，e.g. "alchemist"）
        queue           : 该 task 独占的队列名
        import_path     : worker 侧任务实体所在的 python 模块（供 app.conf.imports 使用）
        schedule        : celery.schedules 对象（crontab / timedelta）。None 表示非定时
        schedule_kwargs : beat 投递任务时带的默认 kwargs（仅当 schedule 非 None 时生效）
        description     : 人类可读说明，仅用于文档 / 自检
    """

    name: str
    app: str
    queue: str
    import_path: str
    schedule: Optional[Any] = None
    schedule_kwargs: dict = field(default_factory=dict)
    description: str = ""


class TaskRegistry:
    """
    Celery task 注册表。

    使用方式::

        TaskRegistry.register("news.filter", app="alchemist", queue="news_filter_queue",
                              import_path="news_pipeline.filter.cwkr")
        spec = TaskRegistry.get("news.filter")
    """

    _tasks: dict[str, TaskSpec] = {}

    @classmethod
    def register(
        cls,
        name: str,
        *,
        app: str,
        queue: str,
        import_path: str,
        schedule: Optional[Any] = None,
        schedule_kwargs: Optional[dict] = None,
        description: str = "",
    ) -> TaskSpec:
        """注册一个 task，返回对应的 TaskSpec。"""
        spec = TaskSpec(
            name=name,
            app=app,
            queue=queue,
            import_path=import_path,
            schedule=schedule,
            schedule_kwargs=schedule_kwargs or {},
            description=description,
        )
        cls._tasks[name] = spec
        return spec

    @classmethod
    def get(cls, name: str) -> TaskSpec:
        """按 task 全名取注册信息，未注册直接抛错。"""
        if name not in cls._tasks:
            raise KeyError(
                f"celery task {name!r} 未注册，请先调用 TaskRegistry.register()"
            )
        return cls._tasks[name]

    @classmethod
    def specs_of(cls, app_name: str) -> list[TaskSpec]:
        """返回归属指定 app 的所有 TaskSpec。"""
        return [s for s in cls._tasks.values() if s.app == app_name]

    @classmethod
    def all_names(cls) -> list[str]:
        """返回所有已注册的 task 名。"""
        return list(cls._tasks.keys())

    @classmethod
    def all_tasks(cls) -> dict[str, TaskSpec]:
        """返回完整注册表副本。"""
        return dict(cls._tasks)

    @classmethod
    def clear(cls) -> None:
        """清空注册表（测试用）。"""
        cls._tasks.clear()

    @classmethod
    def validate(cls) -> list[str]:
        """
        自检注册表一致性，返回错误列表（空列表 = 健康）。

        校验项：
        - name / queue / import_path 不能为空
        - 不允许两条 spec 共享同一个 queue
        - schedule_kwargs 非空时 schedule 不能为 None
        """
        errors: list[str] = []
        queue_owner: dict[str, str] = {}
        for name, spec in cls._tasks.items():
            if not spec.name:
                errors.append(f"{name}: name 不能为空")
            if not spec.queue:
                errors.append(f"{name}: queue 不能为空")
            if not spec.import_path:
                errors.append(f"{name}: import_path 不能为空")
            if spec.queue in queue_owner and queue_owner[spec.queue] != name:
                errors.append(
                    f"queue {spec.queue!r} 被多 task 占用: "
                    f"{queue_owner[spec.queue]} vs {name}"
                )
            queue_owner[spec.queue] = name
            if spec.schedule_kwargs and spec.schedule is None:
                errors.append(f"{name}: 设置了 schedule_kwargs 但 schedule 为 None，不会生效")
        return errors
