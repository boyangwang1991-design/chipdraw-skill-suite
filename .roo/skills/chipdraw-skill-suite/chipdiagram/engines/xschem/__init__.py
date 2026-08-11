"""Xschem 引擎：晶体管/电路工程原理图后端（建设方案 §3.5）。

Engineering Mode：
- 以 SPICE/CDL 或结构化 Circuit YAML 为事实源
- 输出 .sch（Xschem 源）、.spice（网表）、SVG/PDF、ERC 报告
- 需要 PDK 时由环境提供 PDK 路径和符号库，Skill 不携带商业 PDK

Illustration Mode：
- Draw.io/SVG 示意输出，强调可读性
- 必须标注 NON-SIMULATABLE ILLUSTRATION，不生成权威 SPICE 网表
"""
from .circuit import render_circuit  # noqa: F401

__all__ = ["render_circuit"]
