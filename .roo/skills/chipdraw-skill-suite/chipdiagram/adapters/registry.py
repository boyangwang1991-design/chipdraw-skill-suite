"""适配器注册表与分发入口。

根据输入文件扩展名选择适配器，把输入归一化为统一语义模型。
"""
from __future__ import annotations

from typing import Any, Optional

from .base import BaseAdapter, AdapterError, find_adapter
from .markdown_adapter import MarkdownAdapter
from .fusesoc_adapter import FusesocAdapter
from .systemverilog_adapter import SystemVerilogAdapter
from .systemrdl_adapter import SystemRdlAdapter
from .ipxact_adapter import IPXactAdapter
from .spice_adapter import SpiceAdapter
from .drawio_adapter import DrawioAdapter

ALL_ADAPTERS: list[BaseAdapter] = [
    MarkdownAdapter(),
    FusesocAdapter(),
    SystemVerilogAdapter(),
    SystemRdlAdapter(),
    IPXactAdapter(),
    SpiceAdapter(),
    DrawioAdapter(),
]

ADAPTER_BY_NAME = {a.name: a for a in ALL_ADAPTERS}


def extract_input(path: str, **kwargs: Any) -> dict[str, Any]:
    """根据扩展名选择适配器并抽取模型。"""
    adapter = find_adapter(path, ALL_ADAPTERS)
    if adapter is None:
        raise AdapterError(
            f"无法识别输入类型: {path}。支持: {', '.join(a.name for a in ALL_ADAPTERS)}")
    return adapter.extract(path, **kwargs)


def adapter_for(path: str) -> Optional[BaseAdapter]:
    return find_adapter(path, ALL_ADAPTERS)
