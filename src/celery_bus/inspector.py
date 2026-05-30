"""
inspector.py
============
Flower HTTP API 客户端 —— 读侧（查状态）+ 触发侧（预留）。

无项目侧依赖，连接参数全部通过构造函数注入或从环境变量读取。

用法::

    from celery_bus.inspector import FlowerClient

    client = FlowerClient()                       # 走环境变量默认值
    client = FlowerClient(host="x.x.x.x", port=5555)

    # 读侧
    workers = client.get_all_workers()
    tasks   = client.get_all_tasks(task_length=20)
    client.show_task_info(task_id)

    # 触发侧（预留，需 Flower >= 1.0）
    task_id = client.apply_task("news.filter", kwargs={"normalized": {...}})

环境变量::

    FLOWER_HOST         Flower 服务地址（默认 127.0.0.1）
    FLOWER_PORT         Flower 端口（默认 5555）
    SUPERVISOR_USER     HTTP Basic Auth 用户名
    SUPERVISOR_PASS     HTTP Basic Auth 密码
"""
from __future__ import annotations

import os
from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth

from .time_utils import trans_to_beijing_time


class FlowerClient:
    """Flower HTTP API 客户端。"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[str | int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 10.0,
    ):
        host = host or os.getenv("FLOWER_HOST", "127.0.0.1")
        port = port or os.getenv("FLOWER_PORT", "5555")
        username = username or os.getenv("SUPERVISOR_USER")
        password = password or os.getenv("SUPERVISOR_PASS")

        self.flower_url = f"http://{host}:{port}"
        self.auth = HTTPBasicAuth(username, password) if username else None
        self.timeout = timeout
        self._task_cache: dict[str, dict] = {}

    # ======================== 读侧 ========================

    def get_all_workers(self) -> list[dict]:
        """获取所有 worker 列表。"""
        url = f"{self.flower_url}/workers?json=1"
        resp = requests.get(url, timeout=self.timeout, auth=self.auth)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_worker_info(self, worker_name: str) -> Optional[dict]:
        """获取单个 worker 详情。"""
        url = f"{self.flower_url}/api/worker/{worker_name}"
        try:
            resp = requests.get(url, timeout=self.timeout, auth=self.auth)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"[flower] 获取 worker 信息失败: {e}")
            return None

    def get_all_tasks(self, task_length: int = 10) -> dict[str, dict]:
        """
        通过 Flower DataTables 接口拉取最近 task_length 条任务，结果缓存到内部。

        返回 dict[task_id, task_info]。
        """
        data = {
            "draw": "1",
            "columns[6][data]": "received",
            "columns[6][name]": "",
            "columns[6][searchable]": "true",
            "columns[6][orderable]": "true",
            "columns[6][search][value]": "",
            "columns[6][search][regex]": "false",
            "order[0][column]": "6",
            "order[0][dir]": "desc",
            "start": "0",
            "length": str(task_length),
            "search[value]": "",
            "search[regex]": "false",
        }
        url = f"{self.flower_url}/tasks/datatable"
        try:
            resp = requests.post(url, data=data, auth=self.auth, verify=False, timeout=self.timeout)
            json_data = resp.json()
        except requests.exceptions.RequestException as e:
            print(f"[flower] 请求失败: {e}")
            return {}

        self._task_cache = {}
        for item in json_data.get("data", []):
            received = item.get("received")
            started = item.get("started")
            startup_interval = (
                round(started - received, 6)
                if received is not None and started is not None
                else None
            )
            self._task_cache[item.get("uuid")] = {
                "worker": item.get("worker"),
                "state": item.get("state"),
                "received": trans_to_beijing_time(received * 1000, precision="mms") if received else None,
                "started": trans_to_beijing_time(started * 1000, precision="mms") if started else None,
                "startup_interval": startup_interval,
            }
        return self._task_cache

    def show_task_info(self, task_id: str) -> None:
        """打印单条 task 的可读摘要（从内部缓存读取）。"""
        info = self._task_cache.get(task_id)
        if not info:
            print(f"未找到任务信息: {task_id}\n")
            return
        print(f"任务ID: {task_id}")
        print(f"  工作节点: {info.get('worker', '未知')}")
        print(f"  任务状态: {info.get('state', '未知')}")
        print(f"  接收时间: {info.get('received', '未知')}")
        print(f"  开始时间: {info.get('started', '未知')}")
        print(f"  启动间隔: {info.get('startup_interval', 0)} 秒")
        print("-" * 80 + "\n")

    # ======================== 触发侧（预留） ========================

    def apply_task(
        self,
        task_name: str,
        args: Optional[list[Any]] = None,
        kwargs: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        通过 Flower HTTP API 触发一个 celery task（预留项）。

        调用 ``POST /api/task/apply/{task_name}``，需要 Flower >= 1.0 且开启
        ``--enable_events``。相比直连 broker，这条路适合：
          - 外部系统（无 broker 访问权限）需要投递任务
          - 管理后台 / 运维脚本的手动触发

        Args:
            task_name : celery task 全名（与 worker @app.task(name=...) 一致）
            args      : 位置参数列表（通常不用）
            kwargs    : 关键字参数 dict

        Returns:
            成功返回 task_id 字符串，失败返回 None。
        """
        url = f"{self.flower_url}/api/task/apply/{task_name}"
        payload: dict[str, Any] = {}
        if args:
            payload["args"] = args
        if kwargs:
            payload["kwargs"] = kwargs
        try:
            resp = requests.post(url, json=payload, auth=self.auth, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json().get("task-id")
        except requests.exceptions.RequestException as e:
            print(f"[flower] apply_task 失败: {e}")
            return None


# 向后兼容别名（旧代码 import FlowerTaskTracker 不受影响）
FlowerTaskTracker = FlowerClient


if __name__ == "__main__":
    client = FlowerClient()
    tracks = client.get_all_tasks(task_length=20)
    for tid in tracks:
        client.show_task_info(tid)
