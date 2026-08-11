---
name: draw-ip-architecture
version: 1.0.0
description: IP 微架构绘图 Skill。当用户请求绘制 IP 功能框图、数据通路/控制通路、流水线、FIFO/Queue、Arbiter/MUX、AXI/AHB/APB 接口展开、寄存器接口、CDC/RDC 结构、ECC/Parity/Lockstep 安全机制、RTL Module/Instance 层级、位宽转换时使用。支持从 SystemVerilog 抽取 Module/Port/Instance，以 RTL/SystemRDL 为事实源，输出 Draw.io + Graphviz 的 IP 视图，并执行数据通路位宽、流水线、FIFO、CDC/RDC、安全机制规则校验。
license: MIT
homepage: https://github.com/AIXSILICON/chip-design-diagram-suite
compatibility: 需要 Python 3.9+、PyYAML、jsonschema；Graphviz dot、draw.io CLI 为可选依赖。
platforms: [macos, linux, windows]
metadata: {"hermes":{"tags":["ip","microarchitecture","datapath","pipeline","fifo","arbiter","cdc","rdc","systemverilog"],"category":"design"}}
---

# IP 微架构绘图

## Overview

生成 IP 微架构级视图，覆盖建设方案 §3.3 的全部视图类型。数据通路、控制通路、流水线、FIFO、Arbiter、寄存器接口、CDC/RDC、安全机制。

## 支持视图（建设方案 §3.3）

- IP 功能组成图（`ip_overview`）
- 数据通路与控制通路图（`datapath`）
- Pipeline Stage 图（`pipeline`）
- Buffer/FIFO/Queue 结构图（`buffer_fifo`）
- Arbiter、MUX、Decoder、Scheduler 图
- AXI/AHB/APB 等接口展开图（`interface_expanded`）
- 寄存器接口与控制路径图（`register_interface`）
- CDC/RDC 结构图（`cdc_rdc`）
- ECC、Parity、Lockstep、Watchdog 等安全机制图（`safety_mechanism`）
- RTL Module/Instance 层级图（`rtl_hierarchy`）
- 数据格式、位宽转换和 Pack/Unpack 图（`bitwidth_conversion`）

## 核心工作流

1. **取事实源**：优先已评审 HLD/LLD/RTL/SystemRDL；SystemVerilog 用 `uv run chipdiagram extract rtl/pic_top.sv --type ip`。
2. **归一化**：Module/Port/Interface/Datapath/Pipeline/Buffer/Arbiter/CDC/RDC/Safety。
3. **校验**（关键校验，建设方案 §3.3）：
   - Module 与 RTL 实例绑定；
   - Port 名称/方向/位宽与 RTL 一致；
   - 数据通路位宽匹配；位宽转换需明确 Converter；
   - 流水级编号、Latency、Valid/Ready 完整；
   - FIFO 深度/宽度与接口一致；
   - 多源驱动经 MUX/Arbiter；
   - CDC 经 Synchronizer/Handshake/Async FIFO；脉冲跨域需 Pulse Sync；
   - Reset Deassert 同步；寄存器字段绑定 SystemRDL；
   - 安全机制检测对象/故障响应/上报路径完整。
4. **图形约定**（建设方案 §3.3）：
   - 数据通路：蓝色粗实线；控制通路：紫色细实线；
   - Clock：绿色虚线；Reset：灰色虚线；Interrupt/Error：橙色实线；
   - CDC/RDC Block：黄色底色；Safety Mechanism：红色边框；
   - 输入端口左、输出端口右；Clock/Reset/Power 上/下侧；
   - 位宽、协议、Latency 作边标签，不用颜色单独表达。
5. **渲染**：`uv run chipdiagram build <model> --view <view> --format drawio,svg,png --out <out>`。
6. **QA 与发布**：结构 QA + Manifest/Validation。

## Bundled resources

| 文件 | 何时读取 |
|---|---|
| `references/ip-conventions.md` | 需要 IP 图形/布局约定细节 |
| `references/pipeline-and-datapath.md` | 需要流水线/数据通路建模细节 |
| `references/cdc-rdc.md` | 需要 CDC/RDC 结构处理规则 |
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
