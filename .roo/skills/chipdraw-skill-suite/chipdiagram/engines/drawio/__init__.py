"""Draw.io 引擎：SoC/IP 框图、事务序列图、可编辑交付。

- xmlgen.py       Draw.io XML 生成基础（对齐上游 xml-authoring.md）
- blockdiagram.py SoC/IP 框图确定性生成
- sequence.py     事务序列图（封装上游 seqlayout.py）
- exporter.py     draw.io CLI 导出与降级
"""
from .blockdiagram import render_block_diagram  # noqa: F401
from .sequence import render_sequence  # noqa: F401

__all__ = ["render_block_diagram", "render_sequence"]
