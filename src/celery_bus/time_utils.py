"""
time_utils.py
=============
时间工具：北京时区转换。

与 honeycomb-bus 保持同名同签名，两个包可互换。
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytz

BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def trans_to_beijing_time(timestamp_ms, precision="ms") -> str:
    """将毫秒级时间戳转换为北京时间字符串。

    precision:
        "mms" — 微秒级  "%Y-%m-%d %H:%M:%S.%f"
        "ms"  — 毫秒级  "%Y-%m-%d %H:%M:%S.%f"[:-3]
        "s"   — 秒级    "%Y-%m-%d %H:%M:%S"
    """
    if precision == "mms":
        timestamp_s = timestamp_ms / 1000.0
    else:
        timestamp_s = int(timestamp_ms) / 1000.0

    utc_time = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
    beijing_time = utc_time.astimezone(BEIJING_TZ)

    if precision == "mms":
        return beijing_time.strftime("%Y-%m-%d %H:%M:%S.%f")
    elif precision == "ms":
        return beijing_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif precision == "s":
        return beijing_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        raise ValueError(f"不支持的精度: {precision}")
