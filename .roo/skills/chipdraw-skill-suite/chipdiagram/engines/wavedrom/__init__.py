"""WaveDrom 引擎：数字信号时序权威渲染（建设方案 §3.4-B）。

YAML 时序模型 → WaveJSON → SVG/PNG。
- wavedrom-cli（Node）缺失时：降级为输出 WaveJSON（浏览器可渲染）
- 协议规则/来源标记在 validation 中体现
"""
from .timing import render_timing  # noqa: F401

__all__ = ["render_timing"]
