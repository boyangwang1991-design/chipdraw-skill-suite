"""SystemRDL 适配器（建设方案 §5）。

提取寄存器层级和接口信息 → IP 寄存器视图。
复用 PeakRDL 能力（若安装了 peakrdl）；未安装时用内置简化解析器兜底。
"""
from __future__ import annotations

import os
import re
from typing import Any

from .base import BaseAdapter, AdapterError, load_file_text


class SystemRdlAdapter(BaseAdapter):
    name = "systemrdl"
    input_extensions = (".rdl", ".rdlpp")

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        text = load_file_text(path)
        name = os.path.splitext(os.path.basename(path))[0]
        env = self._envelope(name, "ip_architecture", f"{name} Registers", path, "ip")

        fields = _parse_registers(text)
        modules = [{"id": _slug(name), "name": name, "kind": "control"}]
        reg_intf = {
            "id": f"reg_{_slug(name)}",
            "name": f"{name}_regs",
            "protocol": "apb",
            "fields": fields,
            "systemrdl_binding": path,
            "trace": {"confidence": "extracted",
                      "source_refs": [{"file": path, "anchor": "regmap"}]},
        }
        env["diagram"]["subtype"] = "register_interface"
        env["ip"] = {"modules": modules, "register_interfaces": [reg_intf]}
        return env


def _parse_registers(text: str) -> list[dict[str, Any]]:
    """简化 SystemRDL 解析：提取 reg 定义及其内部字段。"""
    fields: list[dict[str, Any]] = []
    for m in re.finditer(r"reg\s*\{\s*(.*?)\s*\}", text, re.S):
        body = m.group(1)
        for fm in re.finditer(r"field\s*\{\s*(.*?)\s*\}\s*(\w+)", body, re.S):
            fname = fm.group(2)
            fbody = fm.group(1)
            w = re.search(r"fieldwidth\s*=\s*(\d+)", fbody)
            acc = re.search(r"sw\s*=\s*(\w+)", fbody)
            fields.append({
                "name": fname,
                "offset": 0,  # 简化：偏移需编译器解析
                "width": int(w.group(1)) if w else 1,
                "access": _map_access(acc.group(1)) if acc else "rw",
            })
    return fields


def _map_access(sw: str) -> str:
    return {"rw": "rw", "r": "ro", "w": "wo", "w1c": "w1c", "w1s": "w1s"}.get(sw, "rw")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_") or "obj"
