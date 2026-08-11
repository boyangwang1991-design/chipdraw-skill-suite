---
name: chip-diagram-router
description: 芯片研发智能绘图统一入口与路由器，为芯片设计全层级（SoC/IP/RTL行为/晶体管）生成可编辑、可验证、可追踪的工程图形。当用户请求绘制芯片相关的框图、SoC 架构、IP 微架构、FSM 状态机、数字时序图（WaveDrom）、事务序列图、晶体管原理图、寄存器接口图、CDC/RDC 结构图、地址映射图时使用；也适用于从 RTL/FuseSoC/SystemRDL/IP-XACT/SPICE 抽取图形。识别设计层级与视图类型、判断输入来源、路由到一个或多个专业子 Skill，建立输出目录与 Manifest，汇总子图与校验结果。即使描述只是“画个架构图”“生成时序”“画状态机”“画个芯片框图”“这个 SoC 长什么样”等口语化表达，也应触发本 Skill 判断是否属于芯片领域，再由本 Skill 决定路由或降级。
license: MIT
compatibility: 需要 Python 3.9+、PyYAML、jsonschema；draw.io CLI（导出 PNG/SVG/PDF）、Graphviz dot（FSM/大型框图布局）、wavedrom-cli（数字时序）为可选依赖。
platforms: [macos, linux, windows]
metadata: {"hermes":{"tags":["chip","soc","ip","fsm","wavedrom","sequence","transistor","diagram"],"category":"design"}}
---

# 芯片研发智能绘图 —— 统一入口与路由

## Overview

理解用户的芯片绘图请求，识别设计层级与视图类型，选择并编排专业子 Skill，生成**可编辑、可验证、可追踪**的工程图形资产（建设方案 §3.1）。

## 何时使用 / 何时不使用

**使用**：SoC 架构、IP 微架构、FSM、数字时序、事务序列、晶体管原理图，以及从 RTL/FuseSoC/SystemRDL/IP-XACT/SPICE 抽取图形。

**不使用**：与芯片设计无关的通用流程图/思维导图（转通用绘图 Skill）；已确认工程原理图需要商业 EDA 平台（如 Virtuoso）；图片/白板照片中无法可靠识别的对象（必须人工复核后转结构化输入）。

## 路由规则（建设方案 §3.1）

| 用户意图或输入 | 路由目标 |
|---|---|
| “画 SoC 顶层、总线、地址、中断、安全岛” | `draw-soc-architecture` |
| “画某 IP 内部模块、流水线、FIFO、CDC” | `draw-ip-architecture` |
| “画状态机、时序、握手、读写事务” | `draw-rtl-behavior` |
| “画 CMOS 门、MOS 网络、SPICE 子电路” | `draw-transistor-schematic` |
| 同时要求 SoC 框图和中断时序 | 先 SoC，再调用 RTL behavior 生成关联子图 |
| 无法判断工程原理图还是文档示意图 | 要求用户在 `illustration` 与 `engineering` 中选择 |

## 统一执行流水线（建设方案 §2.3）

```
输入资产 → 任务识别与路由 → 抽取并归一化语义模型 → Schema与专业规则校验
        → 视图选择与复杂度控制 → 自动布局与专业后端渲染 → 结构校验与视觉QA
        → 发布图形、报告与Manifest
```

## 核心工作流

1. **识别请求**：设计层级（L1 SoC / L2 IP / L3 RTL 行为 / L4 晶体管）与视图类型（框图/互联/FSM/时序/序列/原理图）。
2. **确定输入来源**：自然语言（inferred）、YAML SSOT（推荐）、RTL、FuseSoC、SystemRDL、IP-XACT、SPICE。
3. **路由**：按上表选择一个或多个专业子 Skill。
4. **归一化**：使用 `chipdiagram` 核心包将输入归一化为统一语义模型（公共 Envelope + 专业节点）。
5. **校验**：Schema 校验（Gate 1）+ 专业规则校验（Gate 2）。ERROR 阻断，WARNING 允许草稿。
6. **视图与复杂度**：应用 View Filter；超过阈值自动拆图建议。
7. **渲染**：调用对应后端（Draw.io / Graphviz / WaveDrom / Xschem）。
8. **QA 与发布**：结构 QA（Gate 3/4）+ Manifest/Validation 报告（Gate 5）。

## 命令

```bash
# 从结构化模型生成
uv run chipdiagram build assets/examples/pic-subsystem/pic.yaml --view interrupt_network --format drawio,svg,png --out docs/diagrams/pic

# 从 RTL 抽取 IP 结构
uv run chipdiagram extract rtl/pic_top.sv --type ip --top pic_top --out build/diagram-model/pic.yaml

# 校验但不生成
uv run chipdiagram validate assets/examples/pic-subsystem/pic.yaml --profile soc-signoff

# 比较两个版本
uv run chipdiagram diff old/manifest.yaml new/manifest.yaml --out reports/diagram-diff
```

## 输出目录约定（建设方案 §3.1）

```
docs/diagrams/<design-name>/
├── index.md
├── diagram-set.yaml
├── manifest.yaml
├── validation-summary.md
└── <view-name>/...
```

## 路由器禁止事项（建设方案 §3.1）

- 不直接手写大规模 Draw.io XML（交给确定性生成器）；
- 不把未知端口或网络当成已确认事实（输出 TBD）；
- 不用 WaveDrom 代替事务序列图；
- 不用 Draw.io 作为 Engineering Mode 晶体管网表的权威源；
- 不在一个 Skill 上下文加载所有层级的详细参考资料。

## 失败处理原则（建设方案 §2.3）

- 事实不完整 → 显式输出 `TBD` 和待确认项，不静默补全关键连接；
- Schema 错误、端点不存在、电气短路等严重问题 → 阻断生成；
- 轻微布局或非关键悬空 → 允许带告警输出草稿；
- 所有自动推断在 Manifest 中记录来源和置信度；
- 原始输入、归一化模型、最终输出之间必须能追踪。

## 套件结构

本 Skill 统一放在 `chipdraw-skill-suite/` 目录，主 `SKILL.md` 为统一入口（路由），专业子 Skill 位于 `skills/`，公共资源位于 `assets/`，核心包位于 `chipdiagram/`：

```
chipdraw-skill-suite/
├── SKILL.md                    # 统一入口与路由
├── diagram-routing.md          # 路由决策细节
├── openai.yaml                 # 入口 agent 定义
├── skills/                     # 4 个专业子 Skill
│   ├── draw-soc-architecture/      # SoC 系统级绘图
│   ├── draw-ip-architecture/       # IP 微架构绘图
│   ├── draw-rtl-behavior/          # FSM / WaveDrom / 事务序列
│   └── draw-transistor-schematic/  # 晶体管原理图
├── chipdiagram/                # 核心 Python 包（引擎/适配器/校验器/CLI）
├── assets/                     # 资产层（不直接触发）
│   ├── schemas/                # 8 个 JSON Schema
│   ├── libraries/              # 主题与符号库、wavedrom-examples 官方示例
│   └── examples/               # Golden Case
├── tests/                      # 单元/黄金/集成/视觉测试
├── pyproject.toml              # 工程配置
└── README.md
```

每个专业子 Skill 目录包含其自身的 `SKILL.md`、`references/` 与 `agents/`。
路由规则见下表，详细决策见 `diagram-routing.md`。
**上下文控制**：只加载当前绘图类型相关的参考资料，不在一个 Skill 上下文加载所有层级的 references（建设方案 §3.1/§7）。

## Bundled resources

| 文件 | 何时读取 |
|---|---|
| `diagram-routing.md` | 需要详细路由决策或边界情况时 |
| `openai.yaml` | 需要与 OpenAI-compatible agent 集成时 |
| `<sub-skill>/SKILL.md` | 已路由到对应专业子 Skill 时 |
| `assets/libraries/wavedrom-examples/` | 需要 WaveDrom 数字时序建模参考（官方能力清单、wave 字符、分组/箭头/period/phase/head-foot 示例）时 |

## Prerequisites

- Python 3.9+，`uv pip install -e ".[test]"` 安装依赖
- draw.io CLI（导出 PNG/SVG/PDF）—— 缺失时降级为 `.drawio` XML + diagrams.net URL
- Graphviz `dot`（FSM / 大型框图布局）—— 缺失时回退 Draw.io 网格
- wavedrom-cli（数字时序 SVG/PNG）—— 缺失时输出 WaveJSON
- Xschem + ngspice + PDK 符号库（Transistor Engineering Mode）—— 缺失时输出 SPICE 网表 + ERC 报告
