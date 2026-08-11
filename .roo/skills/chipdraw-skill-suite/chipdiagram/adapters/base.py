"""适配器基类与注册表。

所有适配器把外部输入归一化为统一的芯片图形语义模型（建设方案 §5）。
输入优先级（冲突时）：
    项目指定 SSOT > 已评审结构化文件 > RTL/SPICE 实现事实 > 已评审规格
    > 未评审文档 > 现有图形 > 自然语言与图片推断
项目可在 diagram-policy.yaml 中覆盖。
"""
from __future__ import annotations

import os
from typing import Any, Optional


class AdapterError(Exception):
    """适配器错误。"""


class BaseAdapter:
    """输入适配器基类。"""

    name = "base"
    input_extensions: tuple[str, ...] = ()

    def accepts(self, path: str) -> bool:
        return path.lower().endswith(self.input_extensions)

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """把输入文件归一化为语义模型字典。子类实现。"""
        raise NotImplementedError

    def _envelope(self, diagram_id: str, diagram_type: str, title: str,
                  source_path: str, node_key: str) -> dict[str, Any]:
        """构造公共 Envelope 骨架。"""
        return {
            "schema_version": "1.0",
            "diagram": {"id": diagram_id, "type": diagram_type, "title": title},
            "provenance": {
                "sources": [{"path": source_path, "role": "extracted"}],
                "generator": "chip-design-diagram-suite",
            },
            node_key: {},
        }


def find_adapter(path: str, adapters: list[BaseAdapter]) -> Optional[BaseAdapter]:
    """根据扩展名选择适配器。"""
    for a in adapters:
        if a.accepts(path):
            return a
    return None


def load_file_text(path: str) -> str:
    if not os.path.isfile(path):
        raise AdapterError(f"输入文件不存在: {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()
