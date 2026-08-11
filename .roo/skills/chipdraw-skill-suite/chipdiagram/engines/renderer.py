"""渲染调度器：按视图类型调用专业后端（建设方案 §6）。

| 引擎 | 主要用途 | 必须输出 |
| --- | --- | --- |
| Draw.io | SoC/IP 框图、序列图、可编辑交付 | .drawio、SVG/PNG/PDF |
| Graphviz | 大型有向图、FSM、依赖图自动布局 | DOT、SVG |
| WaveDrom | 数字信号时序 | WaveJSON、SVG/PNG |
| Xschem | 晶体管/电路工程原理图 | .sch、SPICE、SVG/PDF |

渲染器不得重新解释设计语义；它只接收已校验的标准模型和布局策略。
"""
from __future__ import annotations

import os
from typing import Any

from ..views import ViewSelection


def render_view(selection: ViewSelection, formats: list[str] | None,
                out_dir: str, theme: dict[str, Any]) -> list[dict[str, str]]:
    """渲染单个视图，返回产物列表 [{path, format, kind, stats?}]。"""
    layout = selection.model.get("_layout") or {}
    engine = layout.get("engine", "graphviz")
    # 视图类型以 view_id 为准（timing/sequence/fsm 等），subtype 是 diagram 类型
    vtype = selection.view_id or selection.subtype or ""

    if vtype == "timing":
        from .wavedrom import render_timing
        return render_timing(selection, formats=formats, out_dir=out_dir, theme=theme)
    if vtype == "sequence":
        from .drawio import render_sequence
        return render_sequence(selection, formats=formats, out_dir=out_dir, theme=theme)
    if vtype == "fsm":
        from .graphviz import render_fsm
        return render_fsm(selection, formats=formats, out_dir=out_dir, theme=theme)
    if engine == "xschem":
        from .xschem import render_circuit
        return render_circuit(selection, formats=formats, out_dir=out_dir, theme=theme)
    if engine == "graphviz":
        from .graphviz import render_block_diagram
        return render_block_diagram(selection, formats=formats, out_dir=out_dir, theme=theme)
    # 兜底：Draw.io 生成
    from .drawio import render_block_diagram
    return render_block_diagram(selection, formats=formats, out_dir=out_dir, theme=theme)
