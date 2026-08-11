"""FSM 引擎（建设方案 §3.4-A）。

输入：behavior 节点（states + transitions + initial_state）
输出：.dot、.svg（Graphviz 渲染）、.drawio（可编辑）

状态分类着色：normal 蓝、fault/error 红、reset 灰、recovery 绿。
条件/动作作为边标签；`inferred` 转换以虚线表示（建设方案 §3.4 FSM 校验）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from ...views import ViewSelection
from ..drawio.xmlgen import DrawioBuilder, STYLE_EDGE

STATE_COLORS = {
    "normal": "fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "fault": "fillColor=#f8cecc;strokeColor=#b85450;",
    "error": "fillColor=#f8cecc;strokeColor=#b85450;",
    "reset": "fillColor=#f5f5f5;strokeColor=#666666;",
    "recovery": "fillColor=#d5e8d4;strokeColor=#82b366;",
}


def render_fsm(selection: ViewSelection, formats: list[str] | None,
               out_dir: str, theme: dict[str, Any]) -> list[dict[str, str]]:
    """生成 FSM 的 .dot + .svg + .drawio。"""
    behavior = selection.model.get("behavior") or {}
    states = behavior.get("states", []) or []
    transitions = behavior.get("transitions", []) or []
    initial = behavior.get("initial_state", "")
    diagram = selection.model.get("diagram") or {}
    title = diagram.get("title") or diagram.get("id") or "fsm"
    os.makedirs(out_dir, exist_ok=True)

    dot_path = os.path.join(out_dir, "diagram.dot")
    _write_dot(dot_path, title, initial, states, transitions)

    artifacts: list[dict[str, str]] = []
    artifacts.append({"path": dot_path, "format": "dot", "kind": "editable"})

    # SVG（Graphviz dot）
    svg_path = os.path.join(out_dir, "diagram.svg")
    if _run_dot(dot_path, svg_path):
        artifacts.append({"path": svg_path, "format": "svg", "kind": "rendered"})

    # Draw.io 可编辑版
    drawio_path = os.path.join(out_dir, "diagram.drawio")
    _write_drawio(drawio_path, title, initial, states, transitions)
    artifacts.append({"path": drawio_path, "format": "drawio", "kind": "editable"})

    fmt = [f for f in (formats or ["drawio", "svg", "png"]) if f in ("png", "pdf")]
    if fmt:
        from ..drawio.exporter import export_drawio
        exported = export_drawio(drawio_path, os.path.join(out_dir, "diagram"), fmt, final=True)
        for p in exported:
            artifacts.append({"path": p, "format": p.rsplit(".", 1)[-1], "kind": "rendered"})
    return artifacts


def _write_dot(path: str, title: str, initial: str, states: list[dict[str, Any]],
               transitions: list[dict[str, Any]]) -> None:
    lines = [
        "digraph fsm {",
        f'  labelloc="t";',
        f'  label="{title}";',
        "  rankdir=TB;",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica"];',
    ]
    for s in states:
        sid = s.get("id")
        label = s.get("label") or sid
        color = STATE_COLORS.get(s.get("category", "normal"), STATE_COLORS["normal"])
        shape = "doublecircle" if str(sid) == str(initial) else "box"
        lines.append(f'  "{sid}" [label="{label}", shape={shape}, {color}];')
    for t in transitions:
        src = t.get("from")
        tgt = t.get("to")
        cond = t.get("condition", "")
        action = t.get("action", "")
        label = "; ".join(p for p in [cond, action] if p)
        source_kind = t.get("source", "inferred")
        style = "dashed" if source_kind == "inferred" else "solid"
        lines.append(f'  "{src}" -> "{tgt}" [label="{label}", style={style}];')
    lines.append("}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _write_drawio(path: str, title: str, initial: str, states: list[dict[str, Any]],
                  transitions: list[dict[str, Any]]) -> None:
    builder = DrawioBuilder(page_name=title)
    x, y = 40, 40
    positions: dict[str, str] = {}
    for s in states:
        sid = str(s.get("id"))
        label = s.get("label") or sid
        color = STATE_COLORS.get(s.get("category", "normal"), STATE_COLORS["normal"])
        shape = "ellipse;" if str(sid) == str(initial) else "rounded=1;"
        builder.add_vertex(sid, label, x, y, 130, 60, f"{shape}{color}")
        positions[sid] = sid
        x += 180
    for i, t in enumerate(transitions):
        src = str(t.get("from"))
        tgt = str(t.get("to"))
        cond = t.get("condition", "")
        action = t.get("action", "")
        label = "; ".join(p for p in [cond, action] if p)
        style = STYLE_EDGE
        if t.get("source") == "inferred":
            style = style.replace("rounded=1", "rounded=1;dashed=1")
        builder.add_edge(f"t{i}", src, tgt, label, style)
    builder.write(path)


def _run_dot(dot_path: str, svg_path: str) -> bool:
    import shutil
    dot_bin = shutil.which("dot")
    if dot_bin is None:
        return False
    try:
        proc = subprocess.run([dot_bin, "-Tsvg", "-o", svg_path, dot_path],
                              capture_output=True, text=True, timeout=120)
        return proc.returncode == 0 and os.path.isfile(svg_path)
    except Exception:  # noqa: BLE001
        return False
