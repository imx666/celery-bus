# celery-bus

基于 Celery 的任务总线基础设施层，提供注册、发送、构建、调度与监控能力。

## 模块

| 模块 | 说明 |
|---|---|
| `registry` | `TaskSpec` + `TaskRegistry`（class-based SSOT，对标 honeycomb-bus） |
| `boss` | `CeleryBoss` + `init_boss` / `send_celery_task` 兼容函数 |
| `apps` | `build_app()` 工厂，从 `TaskRegistry` 派生 imports / task_routes |
| `config` | `BaseCeleryConfig`（Celery 5.x） |
| `beat` | `build_beat_schedule()` + `attach_beat_schedule()` |
| `inspector` | `FlowerClient`：读侧查询 + `apply_task()` 触发侧预留 |
| `time_utils` | `trans_to_beijing_time()`（与 honeycomb-bus 同名同签名） |

## 快速开始

```python
from celery_bus.registry import TaskRegistry
from celery_bus.boss import init_boss, send_celery_task
from celery_bus.apps import build_app

# 1. 注册 task（项目启动时）
TaskRegistry.register(
    "news.filter",
    app="alchemist",
    queue="news_filter_queue",
    import_path="news_pipeline.filter.cwkr",
)

# 2. 构建 Celery 实例（worker 侧）
APP = build_app("alchemist", broker_url="redis://...")

# 3. 初始化发送端（sender 侧）
init_boss("redis://...")

# 4. 发送任务
send_celery_task("news.filter", "news_filter_queue", kwargs_dict={...})
```

## 安装（UV + git）

```toml
[tool.uv.sources]
celery-bus = { git = "ssh://git@github.com/imx666/celery-bus.git" }
```
