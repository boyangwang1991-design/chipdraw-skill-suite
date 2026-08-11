"""Graphviz 布局的 SoC/IP 框图（封装上游 autolayout.py）。

大型框图（>~15 节点）不应手放坐标；将图描述为 JSON，交给上游
autolayout.py 用 Graphviz 计算节点位置 + 正交边路由，输出 .drawio。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from ...views import ViewSelection
from ..drawio.xmlgen import STYLE_EDGE_DATAPATH, STYLE_EDGE_CONTROL, STYLE_EDGE_CLOCK, STYLE_EDGE_RESET, STYLE_EDGE_INTERRUPT
from ..drawio import blockdiagram as drawio_block

SHARED_DIR = os.path.join(os.path.dirname(__file__), "..", "shared")


def render_block_diagram(selection: ViewSelection, formats: list[str] | None,
                         out_dir: str, theme: dict[str, Any]) -> list[dict[str, str]]:
    """优先用 Graphviz 布局生成 .drawio；Graphviz 缺失时回退 Draw.io 网格。"""
    graph = _to_autolayout_graph(selection.model)
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "diagram.graph.json")
    drawio_path = os.path.join(out_dir, "diagram.drawio")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, ensure_ascii=False, indent=2)

    script = os.path.join(SHARED_DIR, "autolayout.py")
    ok = False
    if os.path.isfile(script):
        try:
            proc = subprocess.run(
                [sys.executable, script, json_path, "-o", drawio_path],
                capture_output=True, text=True, timeout=120)
            ok = proc.returncode == 0 and os.path.isfile(drawio_path)
        except Exception:  # noqa: BLE001
            ok = False
    if not ok:
        # 回退：Draw.io 网格生成
        return drawio_block.render_block_diagram(selection, formats, out_dir, theme)

    artifacts: list[dict[str, str]] = [{"path": drawio_path, "format": "drawio", "kind": "editable"}]
    fmt = [f for f in (formats or ["drawio", "svg", "png"]) if f in ("svg", "png", "pdf")]
    if fmt:
        from ..drawio.exporter import export_drawio
        exported = export_drawio(drawio_path, os.path.join(out_dir, "diagram"), fmt, final=True)
        for p in exported:
            artifacts.append({"path": p, "format": p.rsplit(".", 1)[-1], "kind": "rendered"})
    return artifacts


def _to_autolayout_graph(model: dict[str, Any]) -> dict[str, Any]:
    """把 SoC/IP 模型转换为 autolayout.py 的 graph.json 输入。"""
    node_key = {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
    }.get(model["diagram"]["type"], "soc")
    node = model.get(node_key) or {}
    blocks = node.get("instances") or node.get("modules") or []

    layout_cfg = model.get("layout") or {}
    direction = "LR" if layout_cfg.get("direction", "left_to_right") == "left_to_right" else "TB"

    nodes = []
    for b in blocks:
        bid = str(b.get("id"))
        kind = b.get("kind", "other")
        color = _role_for(kind)
        style = f"rounded=1;whiteSpace=wrap;html=1;{color};"
        nodes.append({
            "id": bid,
            "label": b.get("name") or bid,
            "style": style,
            "width": 140,
            "height": 56,
        })

    edges = []
    for i, c in enumerate(node.get("connections") or []):
        style = _edge_style(c.get("kind", "other"))
        label = " ".join(p for p in [c.get("protocol"), _w(c)] if p)
        edges.append({
            "source": str(c.get("from")),
            "target": str(c.get("to")),
            "label": label,
            "style": style,
        })

    return {"direction": direction, "nodes": nodes, "edges": edges}


def _w(c: dict[str, Any]) -> str:
    return f"{c['data_width']}b" if c.get("data_width") else ""


def _role_for(kind: str) -> str:
    mapping = {
        "cpu": "fillColor=#dae8fc;strokeColor=#6c8ebf;",
        "dsp": "fillColor=#dae8fc;strokeColor=#6c8ebf;",
        "npu": "fillColor=#dae8fc;strokeColor=#6c8ebf;",
        "memory": "fillColor=#d5e8d4;strokeColor=#82b366;",
        "peripheral": "fillColor=#ffe6cc;strokeColor=#d79b00;",
        "subsystem": "fillColor=#e1d5e7;strokeColor=#9673a6;",
        "interconnect": "fillColor=#fff2cc;strokeColor=#d6b656;",
        "controller": "fillColor=#fff2cc;strokeColor=#d6b656;",
        "bridge": "fillColor=#fff2cc;strokeColor=#d6b656;",
        "phy": "fillColor=#f5f5f5;strokeColor=#666666;",
        "datapath": "fillColor=#dae8fc;strokeColor=#6c8ebf;",
        "control": "fillColor=#e1d5e7;strokeColor=#9673a6;",
        "buffer": "fillColor=#d5e8d4;strokeColor=#82b366;",
        "fifo": "fillColor=#d5e8d4;strokeColor=#82b366;",
        "arbiter": "fillColor=#fff2cc;strokeColor=#d6b656;",
        "converter": "fillColor=#fff2cc;strokeColor=#d6b656;",
        "synchronizer": "fillColor=#f8cecc;strokeColor=#b85450;",
    }
    return mapping.get(kind, "fillColor=#f5f5f5;strokeColor=#666666;")


def _edge_style(kind: str) -> str:
    mapping = {
        "datapath": STYLE_EDGE_DATAPATH,
        "control": STYLE_EDGE_CONTROL,
        "clock": STYLE_EDGE_CLOCK,
        "reset": STYLE_EDGE_RESET,
        "interrupt": STYLE_EDGE_INTERRUPT,
    }
    return mapping.get(kind, "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;")
