"""布局编排：根据视图类型选择确定性布局引擎。

- SoC/IP 框图：Graphviz（封装 engines/shared/autolayout.py）或手绘网格
- FSM：Graphviz DOT
- Timing：WaveDrom 自带时间轴（无需图布局）
- Sequence：seqlayout.py 确定性几何
- Circuit：Xschem 网格放置
"""
from __future__ import annotations

from typing import Any

from ..views import ViewSelection
from .. import theme as theme_mod


def compute_view_layout(selection: ViewSelection, theme: dict[str, Any]) -> ViewSelection:
    """为视图计算布局（写入 selection 附加布局信息）。

    本函数根据视图类型选择布局策略。实际坐标计算由渲染引擎在生成时执行；
    这里负责记录布局方向/引擎选择，供渲染器与 QA 使用。
    """
    # 视图类型以 view_id 为准（timing/sequence/fsm 等），subtype 是 diagram 类型
    vtype = selection.view_id or selection.subtype or ""
    model = selection.model
    layout_cfg = model.get("layout") or {}

    if vtype == "timing":
        engine = "wavedrom"
        direction = "left_to_right"
    elif vtype == "sequence":
        engine = "seqlayout"
        direction = "top_to_bottom"
    elif vtype == "fsm":
        engine = "graphviz"
        direction = layout_cfg.get("direction", "top_to_bottom")
    elif _is_circuit(model):
        engine = "xschem"
        direction = layout_cfg.get("direction", "top_to_bottom")
    else:
        engine = "graphviz"
        direction = layout_cfg.get("direction", "left_to_right")

    # 记录布局信息（渲染器据此选择生成方式）
    selection.model.setdefault("_layout", {})
    selection.model["_layout"].update({
        "engine": engine,
        "direction": direction,
        "theme": theme.get("name", "aixsilicon-light"),
    })
    return selection


def _is_circuit(model: dict[str, Any]) -> bool:
    return model.get("diagram", {}).get("type") == "transistor_schematic"
