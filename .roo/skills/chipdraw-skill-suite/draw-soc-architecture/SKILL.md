---
name: draw-soc-architecture
version: 1.0.0
description: SoC 系统级绘图 Skill。当用户请求绘制 SoC 顶层框图、总线互联（AXI/AHB/APB/CHI/NoC/TileLink）、地址空间、时钟复位、电源域、中断网络、安全/保密域、FuseSoC 依赖、Chiplet 拓扑时使用。以 SoC Integration YAML/FuseSoC/IP-XACT 为权威事实源，输出 Draw.io + Graphviz 的 SOC 多视图，并执行协议/位宽/地址/跨域/中断规则校验。
license: MIT
homepage: https://github.com/AIXSILICON/chip-design-diagram-suite
compatibility: 需要 Python 3.9+、PyYAML、jsonschema；Graphviz dot（大型框图）、draw.io CLI（导出）为可选依赖。
platforms: [macos, linux, windows]
metadata: {"hermes":{"tags":["soc","architecture","bus","interconnect","interrupt","power-domain","fusesoc"],"category":"design"}}
---

# SoC 系统级绘图

## Overview

生成 SoC/Subsystem/互联/域视图，覆盖建设方案 §3.2 的全部视图类型。**以结构化事实（SSOT）为准**，避免大模型手写坐标和臆造连接。

## 支持视图（建设方案 §3.2）

| 视图 ID | 内容 | 默认详细度 |
|---|---|---|
| `soc_overview` | CPU/DSP/NPU/Memory/Peripheral/Subsystem 总览 | IP 实例级 |
| `bus_interconnect` | AXI/AHB/APB/CHI/NoC/TileLink 连接 | 逻辑接口级 |
| `address_map` | Initiator、Target、Address Window | 地址窗口级 |
| `clock_reset` | Clock Source、Divider、Gate、Reset Controller、域关系 | Clock/Reset Domain 级 |
| `power_domain` | Power Domain、Switch、Isolation、Retention、Level Shifter | 电源域级 |
| `interrupt_network` | IRQ Source、Aggregator、PIC/PLIC/CLIC/GIC、CPU/Safety Island | 中断源与汇聚级 |
| `safety_security` | Safety/Security Domain、Firewall、Monitor、Lockstep | 机制级 |
| `fusesoc_dependency` | Core、Dependency、Target、Generator | Core 依赖级 |
| `chiplet_topology` | Die、D2D、NoC、Memory Die、PHY | Die 级 |

## 核心工作流

1. **选视图**：根据用户请求选择视图 ID（见上表）。
2. **取事实源**：优先 SoC Integration YAML（推荐权威来源）；FuseSoC `.core` 用于依赖视图；IP-XACT 作为交换格式。
3. **归一化**：`uv run chipdiagram extract <input> --type soc` 或直接加载 YAML。
4. **校验**（关键校验，建设方案 §3.2）：
   - 接口端点是否存在；
   - Initiator/Target、Master/Slave、Source/Sink 方向合法；
   - 协议类型、版本、数据/地址/ID 位宽兼容；
   - 地址窗口重叠、越界或无上游可达；
   - 跨时钟域 CDC、跨复位域 RDC、跨电源域 Isolation/Retention/Level Shifter；
   - 跨安全/保密域经允许的 Bridge/Firewall；
   - 中断重复编号、悬空、多驱动；
   - Mandatory Port 悬空；FuseSoC 依赖缺失或循环。
5. **布局**：主数据流左→右；CPU/Initiator 左、Memory/Target 右、Interconnect 中；CRG/Power/Safety Manager 顶部；Subsystem 用容器；不同域用淡色容器 + 图例。
6. **渲染**：`uv run chipdiagram build <model> --view <view> --format drawio,svg,png --out <out>`。
7. **QA**：结构检查（重叠/线穿块/标签裁切）+ 对象数量一致。
8. **发布**：Manifest + Validation 报告。

## 图形约定

- 超过 20 个可见 Block 或 35 条连接时触发自动拆图建议；
- 所有连接采用正交路由，不穿越 Block；
- 总线默认收敛为一条逻辑接口，不自动展开 AXI 五通道（`collapse.axi_channels`）。

## Bundled resources

| 文件 | 何时读取 |
|---|---|
| `references/soc-conventions.md` | 需要 SoC 布局/图形约定细节 |
| `references/protocols.md` | 需要总线协议位宽/时序/方向规则 |
| `references/domain-rules.md` | 需要跨域（CDC/RDC/电源/安全）处理规则 |
| `agents/openai.yaml` | 需要 OpenAI-compatible agent 集成 |

## 输出

```
<view-name>/
├── source.yaml
├── model.normalized.yaml
├── diagram.drawio
├── diagram.svg / .png / .pdf
├── validation.json / .md
└── manifest.yaml
```
