"""
config.py
=========
Celery 5.x 规范的基础配置。

项目侧通过 ``build_app()`` 传入 broker，差异配置（app 名 / imports / routes /
beat_schedule）由 apps.py 和 beat.py 从 TaskRegistry 派生后注入，不写在这里。
"""
from __future__ import annotations


class BaseCeleryConfig:
    # -------- 序列化 / 时区 --------
    enable_utc = True
    timezone = "Asia/Shanghai"
    accept_content = ["application/json"]
    task_serializer = "json"
    result_serializer = "json"

    # -------- broker 连接 --------
    broker_connection_retry_on_startup = True
    broker_pool_limit = 100

    # -------- worker 行为 --------
    worker_disable_rate_limits = True
    # 一进程一任务模型：并发靠 supervisord numprocs 横向扩，不靠单进程多 slot。
    # solo pool + prefetch=1 + acks_late 三者配合，彻底规避 prefetch 导致的任务预取坑。
    worker_prefetch_multiplier = 1

    # -------- 可靠性 --------
    task_acks_late = True
    task_reject_on_worker_lost = True

    # -------- 结果 --------
    result_expires = 3600

    # -------- 监控（Flower 需要） --------
    # worker 持续发送任务/心跳事件到 broker，Flower 订阅即可看到实时数据。
    worker_send_task_events = True
    task_send_sent_event = True
