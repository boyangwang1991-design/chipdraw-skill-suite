"""输入适配器子包：把多种输入归一化为统一的芯片图形语义模型。

- markdown_adapter        自然语言 / Markdown 规格 → inferred 模型
- fusesoc_adapter         FuseSoC .core → 依赖/工程视图
- systemverilog_adapter   SystemVerilog module/port/instance/enum → IP/行为模型
- systemrdl_adapter       SystemRDL → IP 寄存器视图（复用 PeakRDL 能力）
- ipxact_adapter          IP-XACT XML → SoC/IP 模型
- spice_adapter           SPICE/CDL → Circuit 模型（Engineering Mode 权威输入）
- drawio_adapter          现有 .drawio → Graph 模型（重构 / Diff / 风格复用）
"""
