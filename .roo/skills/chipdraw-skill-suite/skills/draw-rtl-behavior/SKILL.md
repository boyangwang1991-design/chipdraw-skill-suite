---
name: draw-rtl-behavior
version: 1.0.0
description: RTL 行为级绘图 Skill（FSM / WaveDrom 数字时序 / 事务序列）。当用户请求绘制状态机、数字时序图、握手波形、Reset/Clock 时序、中断时序、CDC 时序、协议事务序列（CPU→DMA→Interconnect→Memory、中断源→PIC→CLIC、UVM Sequence→Driver→DUT→Monitor→Scoreboard）时使用；也适用于"画个波形""看下这个握手时序""这个状态机有哪些状态"等行为级描述。以 RTL/SVA/Testplan/协议规格为事实源，输出 Graphviz DOT/SVG（FSM）、WaveJSON/SVG/PNG（时序）、Draw.io 序列图（事务），并执行可达性/一致性/协议规则校验。
license: MIT
homepage: https://github.com/AIXSILICON/chip-design-diagram-suite
compatibility: 需要 Python 3.9+、PyYAML、jsonschema；Graphviz dot（FSM）、wavedrom-cli（时序）、draw.io CLI（导出）为可选依赖。
platforms: [macos, linux, windows]
metadata: {"hermes":{"tags":["fsm","wavedrom","timing","sequence","state-machine","handshake","rtl"],"category":"design"}}
---

# RTL 行为级绘图：FSM / WaveDrom / 事务序列

## Overview

该 Skill 内部包含三个后端（FSM / Timing / Sequence），共享行为级元数据、输入追踪和质量出口（建设方案 §3.4）。

## 视图类型

| 视图 ID | 后端 | 输出 |
|---|---|---|
| `fsm` | Graphviz | `.dot`、`.svg`、`.drawio` |
| `timing` | WaveDrom | `.wave.json`、`.svg`、`.png` |
| `sequence` | seqlayout | `.drawio`、`.mmd` |

## A. FSM 视图（建设方案 §3.4-A）

输入模型：
```yaml
behavior:
  initial_state: idle
  states:
    - {id: idle, category: normal}
    - {id: transfer, category: normal}
    - {id: error, category: fault}
  transitions:
    - {from: idle, to: transfer, condition: "start && cfg_valid", action: clear_count}
    - {from: transfer, to: idle, condition: last_beat, action: set_done_irq, source: rtl}
```

**FSM 校验**：初始状态存在且唯一；Transition 端点存在；不可达/无出口/孤立状态；冲突或重复条件；Default/Error/Recovery 路径；状态编码重复或不完整；从 RTL 抽取时比较 case 分支/状态寄存器/跳转条件；不确定条件标为 `inferred`。

## B. WaveDrom 数字时序视图（建设方案 §3.4-B，对齐 WaveDrom Tutorial）

适用场景：AXI/APB/AHB 读写、Ready/Valid 握手、Reset Assertion/Deassertion、Clock Gating、中断产生/锁存/清除、CDC 握手、Pipeline 周期、Fault 时序。

输入模型（含全部高级能力）：
```yaml
behavior:
  clock:
    name: pclk
    period: 10ns
    # wave: "P......."   # 可选；缺省自动按信号周期生成 p/P/n/N 时钟
    # polarity: positive # positive / negative
    # edge_marker: true  # 带/不带边沿标记
  signals:
    - {name: psel, wave: "0.1...0"}
    - {name: penable, wave: "0..1..0"}
    - {name: paddr, wave: "x.3...x", data: ["ADDR"]}
    # 分组（嵌套数组，可嵌套）
    - ["Master", [{name: write, wave: "01.0...."}, {name: read, wave: "0...1..0"}]]
    # 每信号 period/phase（DDR 等）
    - {name: DQ, wave: "z.........5555z.", data: ["D0", "D1", "D2", "D3"], phase: 0.5}
    # node 锚点 + edge 箭头
    - {name: A, wave: "01........0....", node: ".a........j"}
  markers:
    - {cycle: 2, text: setup}
    - {cycle: 3, text: access}
  edges: ["a~b t1", "c->d 建立时间"]
  config: {hscale: 1, skin: narrow}   # 可选
  head: {text: "APB Write", tick: 0}  # 图上方标题/标尺
  foot: {text: "Figure 100", tock: 9} # 图下方说明
  origin: spec        # spec / simulation / inferred
```

**时序校验**：data 数量 = wave 中引用字符数（数字 `2-9` 与 `=`；`x/z` 不引用、`.` 延续、`|` 分隔，勿误判 `x2...x`）；node 与 wave 长度一致；显式时钟 wave 语法合法；Clock 与时间标尺存在；必选信号缺失；协议规则（如 APB Setup/Access）；Ready/Valid 数据稳定性冲突；Reset 释放与 Clock 关系；来源标注（规范/仿真/AI 推断）。

**wave 书写约定**（WaveDrom 渲染语义，详见 `references/timing.md`）：连续同电平必须用 `.` 延续（`"1."` 而非 `"11"`，后者渲染出 glitch 跳变沿）；首字符没有前态可延续，必须为显式电平（`0/1/x/z` 或数据字符），不得以 `.` 开头；连续数字（`2-9`/`=`）表示连续 data 拍，属合法写法。wave 字符索引即周期号，建模时先列事件表（各握手/数据事件的周期号）再按索引逐字符书写，写完后回对：同通道带 data 信号的有效字符（`.` 展开后）必须覆盖整个 `*valid` 为高窗口——VALID 不得先于数据置起，等待态期间数据须稳定（防 off-by-one 错位）。校验器报 WARNING：TIMING_WAVE_GLITCH / TIMING_WAVE_LEADING_DOT / TIMING_HANDSHAKE_DATA_UNCOVERED。

**参考资产**：`assets/libraries/wavedrom-examples/`（官方能力清单与 WaveJSON 示例，只读），建模前可按需阅读。

## C. 事务序列视图（建设方案 §3.4-C）

表达 Actor/Module 之间的消息次序，不承担逐周期电平表达。

典型场景：CPU→DMA→Interconnect→Memory；Interrupt Source→PIC→CLIC；Power Manager→CRG→Subsystem Reset；Bus Error→Monitor→Fault Manager；UVM Sequence→Driver→DUT→Monitor→Scoreboard。

输出优先为可编辑 Draw.io 序列图，并附 Mermaid 版本用于文档内嵌。

## 工作流

1. **选视图**：FSM / Timing / Sequence。
2. **取事实源**：RTL、SVA、Testplan、协议规格；SystemVerilog 用 `uv run chipdiagram extract rtl/dma.sv --type rtl_behavior`。
3. **归一化**：行为模型（states/transitions 或 clock/signals 或 participants/messages）。
4. **校验**：见上各节。
5. **渲染**：`uv run chipdiagram build <model> --view fsm|timing|sequence --format drawio,svg,png --out <out>`。
6. **QA 与发布**：结构 QA + Manifest/Validation。

## Bundled resources

| 文件 | 何时读取 |
|---|---|
| `references/fsm.md` | 需要 FSM 建模/校验细节 |
| `references/timing.md` | 需要 WaveDrom 建模/协议规则细节 |
| `references/sequence.md` | 需要事务序列建模细节 |
| `agents/openai.yaml` | 需要 OpenAI-compatible agent 集成 |

## 输出

```
<view-name>/
├── model.normalized.yaml
├── diagram.dot / .wave.json / .drawio
├── diagram.svg / .png
├── validation.json / .md
└── manifest.yaml
```
