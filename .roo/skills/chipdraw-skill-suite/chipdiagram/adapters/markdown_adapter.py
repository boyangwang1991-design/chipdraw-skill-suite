"""自然语言 / Markdown 适配器（建设方案 §5）。

从 Markdown/规格文档中提取候选 Block、关系、状态、时序，输出标注为
`inferred` 的 YAML 模型。关键连接需用户或事实源确认（建设方案 §2.3）。

推断启发式（保守，避免臆造）：
- 识别表格中的模块/端口/连接
- 识别标题层级作为层级
- 所有对象 trace.confidence=inferred
"""
from __future__ import annotations

import os
import re
from typing import Any

from .base import BaseAdapter, AdapterError, load_file_text


class MarkdownAdapter(BaseAdapter):
    name = "markdown"
    input_extensions = (".md", ".markdown", ".txt")

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        text = load_file_text(path)
        diagram_type = kwargs.get("diagram_type") or "soc_architecture"
        node_key = {
            "soc_architecture": "soc",
            "ip_architecture": "ip",
            "rtl_behavior": "behavior",
            "transistor_schematic": "circuit",
        }.get(diagram_type, "soc")

        title = _first_heading(text) or os.path.splitext(os.path.basename(path))[0]
        diagram_id = _slugify(title)

        env = self._envelope(diagram_id, diagram_type, title, path, node_key)
        model: dict[str, Any] = env

        if node_key == "soc":
            model["soc"] = _extract_soc(text, kwargs.get("kind_map") or {})
        elif node_key == "ip":
            model["ip"] = _extract_ip(text)
        elif node_key == "behavior":
            model["behavior"] = _extract_behavior(text)
        elif node_key == "circuit":
            model["circuit"] = _extract_circuit(text)

        # 来源标记：所有推断对象
        _mark_inferred(model, node_key)
        return model


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return None


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9_-]+", "-", name.lower())
    return s.strip("-") or "diagram"


def _mark_inferred(model: dict[str, Any], node_key: str) -> None:
    """给所有对象加 trace.confidence=inferred。"""
    node = model.get(node_key) or {}
    for entries in node.values():
        if isinstance(entries, list):
            for e in entries:
                if isinstance(e, dict):
                    e.setdefault("trace", {})["confidence"] = "inferred"


def _extract_soc(text: str, kind_map: dict[str, str]) -> dict[str, Any]:
    """从表格中提取实例与连接。"""
    instances: list[dict[str, Any]] = []
    connections: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in _table_rows(text):
        if len(row) < 2:
            continue
        name = row[0].strip()
        if not name:
            continue
        # 第一列作块，第二列作类型/方向提示
        kind = _guess_kind(name, row[1], kind_map)
        if name not in seen:
            seen.add(name)
            instances.append({"id": _slugify(name), "name": name, "kind": kind})
        # 第三列可能是连接目标
        if len(row) >= 3 and row[2].strip():
            tgt = row[2].strip()
            if tgt != name:
                connections.append({
                    "id": f"c_{_slugify(name)}_{_slugify(tgt)}",
                    "from": _slugify(name), "to": _slugify(tgt), "kind": "bus",
                })
    return {"instances": instances, "connections": connections}


def _extract_ip(text: str) -> dict[str, Any]:
    modules: list[dict[str, Any]] = []
    ports: list[dict[str, Any]] = []
    for row in _table_rows(text):
        if len(row) >= 2:
            name = row[0].strip()
            if name and name not in {m.get("name") for m in modules}:
                modules.append({"id": _slugify(name), "name": name, "kind": "other"})
    return {"modules": modules, "ports": ports}


def _extract_behavior(text: str) -> dict[str, Any]:
    states: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    state_names: set[str] = set()
    for row in _table_rows(text):
        if len(row) >= 2:
            s = row[0].strip()
            if s and s.lower() not in ("state", "from", "source", "名称"):
                if s not in state_names:
                    state_names.add(s)
                    states.append({"id": _slugify(s), "category": "normal"})
    return {
        "initial_state": states[0]["id"] if states else "",
        "states": states,
        "transitions": transitions,
    }


def _extract_circuit(text: str) -> dict[str, Any]:
    return {"mode": "illustration", "devices": [], "nets": []}


def _table_rows(text: str) -> list[list[str]]:
    """提取 Markdown 表格行（跳过表头与分隔行）。"""
    rows: list[list[str]] = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
            continue  # 表头分隔行
        rows.append(cells)
    return rows


def _guess_kind(name: str, hint: str, kind_map: dict[str, str]) -> str:
    h = hint.lower()
    known = {
        "cpu": "cpu", "dsp": "dsp", "npu": "npu", "memory": "memory", "ram": "memory",
        "sram": "memory", "dram": "memory", "flash": "memory", "peripheral": "peripheral",
        "uart": "peripheral", "spi": "peripheral", "i2c": "peripheral", "gpio": "peripheral",
        "subsystem": "subsystem", "interconnect": "interconnect", "noc": "interconnect",
        "axi": "interconnect", "bridge": "bridge", "phy": "phy", "controller": "controller",
        "dma": "controller", "interrupt": "controller",
    }
    if kind_map.get(name):
        return kind_map[name]
    for k, v in known.items():
        if k in name.lower() or k in h:
            return v
    return "other"
