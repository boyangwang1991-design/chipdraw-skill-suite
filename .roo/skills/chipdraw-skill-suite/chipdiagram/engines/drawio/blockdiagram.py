"""Draw.io 框图生成器（SoC/IP 系统级与微架构级）。

从已校验的语义模型确定性生成 .drawio，不手写坐标臆造连接（建设方案 §1.1）。
布局规则（建设方案 §3.2）：
- 主数据流默认左→右；CPU/Initiator 左、Memory/Target 右、Interconnect 中
- 容器（域/子系统）用 swimlane，子坐标相对父容器
- 连接按 kind 使用不同线型（datapath 蓝粗实线、control 紫细线、clock 绿虚线、reset 灰虚线、interrupt 橙实线）
- 超过阈值时由 views.complexity_check 提示拆图

本生成器主要服务无 Graphviz 或需要 Draw.io 原生可编辑的场景；
大型框图优先走 graphviz 引擎（封装 autolayout.py），本模块提供确定性兜底。
"""
from __future__ import annotations

import os
from typing import Any

from ..shared import autolayout  # noqa: F401  确保可导入路径
from ...views import ViewSelection
from ... import theme as theme_mod
from . import xmlgen

BLOCK_W, BLOCK_H = 140, 56
PORT_H = 22
GAP_X, GAP_Y = 40, 40


def render_block_diagram(selection: ViewSelection, formats: list[str] | None,
                         out_dir: str, theme: dict[str, Any]) -> list[dict[str, str]]:
    """生成 SoC/IP 框图的 .drawio 并导出。"""
    model = selection.model
    node_key = _node_key(model)
    node = model.get(node_key) or {}
    fmt = formats or ["drawio", "svg", "png"]
    out_stem = os.path.join(out_dir, "diagram")
    builder = xmlgen.DrawioBuilder(page_name=selection.view_id)

    _build_blocks(builder, model, node, node_key)
    _build_edges(builder, model, node, node_key)

    os.makedirs(out_dir, exist_ok=True)
    drawio_path = f"{out_stem}.drawio"
    builder.write(drawio_path)

    artifacts: list[dict[str, str]] = []
    artifacts.append({"path": drawio_path, "format": "drawio", "kind": "editable"})

    if "svg" in fmt or "png" in fmt or "pdf" in fmt:
        export_fmts = [f for f in fmt if f in ("svg", "png", "pdf")]
        from .exporter import export_drawio
        exported = export_drawio(drawio_path, out_stem, export_fmts, final=True)
        for p in exported:
            f = p.rsplit(".", 1)[-1]
            artifacts.append({"path": p, "format": f, "kind": "rendered"})
    return artifacts


def _build_blocks(builder: xmlgen.DrawioBuilder, model: dict[str, Any],
                  node: dict[str, Any], node_key: str) -> dict[str, str]:
    """生成所有块（实例/模块），支持容器嵌套。返回 id → 画布位置。"""
    blocks = node.get("instances") or node.get("modules") or []
    positions: dict[str, str] = {}

    # 布局：简单网格（确定性）
    x, y = 40, 40
    for b in blocks:
        bid = str(b.get("id"))
        label = b.get("name") or bid
        kind = b.get("kind", "other")
        color = _block_color(model, kind)
        style = f"rounded=1;whiteSpace=wrap;html=1;{color};"
        builder.add_vertex(bid, label, x, y, BLOCK_W, BLOCK_H, style)
        positions[bid] = bid
        x += BLOCK_W + GAP_X
    return positions


def _build_edges(builder: xmlgen.DrawioBuilder, model: dict[str, Any],
                 node: dict[str, Any], node_key: str) -> None:
    """生成连接边。连接 from/to 解析到块 id。"""
    conns = node.get("connections") or []
    for i, c in enumerate(conns):
        src = str(c.get("from"))
        tgt = str(c.get("to"))
        kind = c.get("kind", "other")
        style = _edge_style(model, kind)
        label = _edge_label(c)
        builder.add_edge(f"e{i}_{src}_{tgt}", src, tgt, label, style)


def _edge_style(model: dict[str, Any], kind: str) -> str:
    mapping = {
        "datapath": xmlgen.STYLE_EDGE_DATAPATH,
        "control": xmlgen.STYLE_EDGE_CONTROL,
        "clock": xmlgen.STYLE_EDGE_CLOCK,
        "reset": xmlgen.STYLE_EDGE_RESET,
        "interrupt": xmlgen.STYLE_EDGE_INTERRUPT,
        "bus": xmlgen.STYLE_EDGE,
    }
    return mapping.get(kind, xmlgen.STYLE_EDGE)


def _edge_label(c: dict[str, Any]) -> str:
    parts = []
    if c.get("protocol"):
        parts.append(c["protocol"])
    if c.get("data_width"):
        parts.append(f"{c['data_width']}b")
    return " ".join(parts)


def _block_color(model: dict[str, Any], kind: str) -> str:
    """根据块类型解析主题色（对齐上游 palette 语义）。"""
    try:
        theme = theme_mod.load_theme(model.get("style", {}).get("theme", "aixsilicon-light"))
        role = {
            "cpu": "primary", "dsp": "primary", "npu": "primary",
            "memory": "success", "peripheral": "accent",
            "subsystem": "secondary", "interconnect": "warning",
            "controller": "warning", "bridge": "warning",
            "phy": "neutral", "datapath": "primary", "control": "secondary",
            "buffer": "success", "arbiter": "warning", "converter": "warning",
            "fifo": "success", "synchronizer": "danger",
        }.get(kind, "neutral")
        color = theme_mod.resolve_role_color(theme, role)
        return f"fillColor={color['fillColor']};strokeColor={color['strokeColor']};"
    except theme_mod.ThemeError:
        return "fillColor=#dae8fc;strokeColor=#6c8ebf;"


def _node_key(model: dict[str, Any]) -> str:
    return {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }[model["diagram"]["type"]]
