"""Graphviz 引擎：大型有向图、FSM、依赖图自动布局。

- fsm.py           FSM → DOT/SVG/Draw.io
- blockdiagram.py  SoC/IP 大型框图（封装上游 autolayout.py 确定性布局）
"""
from .blockdiagram import render_block_diagram  # noqa: F401
from .fsm import render_fsm  # noqa: F401

__all__ = ["render_block_diagram", "render_fsm"]
