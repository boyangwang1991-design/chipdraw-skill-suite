"""现有 `.drawio` 适配器（建设方案 §5）。

提取 Cell、Edge、Label 和页面 → Graph 模型。
用于重构、Diff、风格复用；不自动视为设计 SSOT。
"""
from __future__ import annotations

import os
import re
from typing import Any
from xml.etree import ElementTree as ET

from .base import BaseAdapter, AdapterError, load_file_text


class DrawioAdapter(BaseAdapter):
    name = "drawio"
    input_extensions = (".drawio", ".xml")

    def accepts(self, path: str) -> bool:
        if not path.lower().endswith(self.input_extensions):
            return False
        try:
            text = load_file_text(path)
        except AdapterError:
            return False
        return "<mxfile" in text or "<mxGraphModel" in text

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        text = load_file_text(path)
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise AdapterError(f"Draw.io XML 解析失败 {path}: {exc}") from exc

        name = os.path.splitext(os.path.basename(path))[0]
        env = self._envelope(name, "soc_architecture", name, path, "soc")
        cells, edges = _extract_cells(root)
        env["diagram"]["subtype"] = "soc_overview"
        env["soc"] = {
            "instances": [{"id": str(c.get("id")), "name": c.get("value") or str(c.get("id")),
                           "kind": "other", "trace": {"confidence": "extracted"}}
                          for c in cells],
            "connections": [{
                "id": str(e.get("id")), "from": str(e.get("source")), "to": str(e.get("target")),
                "kind": "bus", "trace": {"confidence": "extracted"},
            } for e in edges],
        }
        return env


def _extract_cells(root: ET.Element) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cells: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for cell in root.iter("mxCell"):
        cid = cell.get("id")
        if cid in ("0", "1"):
            continue
        value = cell.get("value")
        if cell.get("edge") == "1":
            if cell.get("source") and cell.get("target"):
                edges.append(cell)
        else:
            cells.append({"id": cid, "value": value})
    return cells, edges
