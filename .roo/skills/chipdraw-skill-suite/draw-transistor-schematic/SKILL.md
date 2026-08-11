---
name: draw-transistor-schematic
version: 1.0.0
description: 晶体管级绘图 Skill。当用户请求绘制 CMOS 门、MOS 网络、反相器、NAND/NOR、Latch、Level Shifter、SRAM Bitcell、SPICE/CDL 子电路原理图时使用。必须区分 Illustration Mode（Draw.io/SVG 示意图，标注 NON-SIMULATABLE ILLUSTRATION）与 Engineering Mode（基于 SPICE/CDL/PDK 符号，Xschem 后端，输出 .sch/SPICE/SVG/PDF/ERC 报告），并执行 ERC（Bulk 错接、悬空 Gate、电源短路、四端完整、子电路端口一致）校验。
license: MIT
homepage: https://github.com/AIXSILICON/chip-design-diagram-suite
compatibility: Engineering Mode 需要外部 Xschem、ngspice、PDK 符号库；Illustration Mode 仅需 draw.io CLI。
platforms: [macos, linux, windows]
metadata: {"hermes":{"tags":["transistor","cmos","mos","spice","xschem","schematic","erc","pdk"],"category":"design"}}
---

# 晶体管级绘图

## Overview

该 Skill 必须区分两种模式（建设方案 §3.5）。**严禁将示意图误当工程网表**。

## Illustration Mode

**用途**：规格、培训、评审和 PPT 中的 CMOS 反相器、NAND/NOR、Latch、Level Shifter、SRAM Bitcell 等原理示意。

- 使用 Draw.io/SVG 输出；
- 强调可读性和结构说明；
- 允许简化 Bulk、模型和参数；
- 输出必须标注 `NON-SIMULATABLE ILLUSTRATION`；
- 不生成权威 SPICE 网表。

## Engineering Mode

**用途**：基于 SPICE/CDL/PDK 符号生成或检查具有网络语义的原理图。

- 以 SPICE/CDL 或结构化 Circuit YAML 为事实源；
- 使用 Xschem 作为原理图后端；
- Device 必须具有类型、模型、参数和端子；
- 输出 Xschem 源文件、SPICE 网表、SVG/PDF 和 ERC 报告；
- 需要 PDK 时由环境提供 PDK 路径和符号库，Skill 不携带商业 PDK。

## 输入模型（工程校验，建设方案 §3.5）

```yaml
circuit:
  mode: engineering
  ports:
    - {name: a, direction: input}
    - {name: y, direction: output}
    - {name: vdd, kind: power}
    - {name: vss, kind: ground}
  devices:
    - id: mp0
      type: pmos
      model: pmos_1v8
      parameters: {w: 2.0um, l: 0.18um}
      terminals: {g: a, d: y, s: vdd, b: vdd}
    - id: mn0
      type: nmos
      model: nmos_1v8
      parameters: {w: 1.0um, l: 0.18um}
      terminals: {g: a, d: y, s: vss, b: vss}
```

## 工程校验 / ERC

- Device、Net、Port 名称唯一；
- MOS 四端连接完整；
- Bulk 连接满足项目规则；
- 电源和地不存在直接短路；
- 无悬空 Gate 或未声明网络；
- Model 和 Symbol 可解析；
- 参数单位和数值格式合法；
- Subcircuit 实例端口数与定义一致；
- Schematic Netlist 与输入 SPICE/CDL 结构一致；
- ERC 错误阻断正式输出，告警进入 waiver 流程。

## 工作流

1. **确认模式**：无法判断时要求用户在 `illustration` 与 `engineering` 中选择。
2. **取事实源**：SPICE/CDL（`uv run chipdiagram extract <file>.sp --type circuit`）或 Circuit YAML。
3. **校验**：运行 ERC 检查。
4. **渲染**：
   - Illustration：`uv run chipdiagram build <model> --view schematic_illustration --out <out>`
   - Engineering：`uv run chipdiagram build <model> --view schematic_engineering --out <out>`
5. **QA 与发布**：ERC 报告 + Manifest/Validation。

## 模式标记（风险控制，建设方案 §16）

- Illustration 输出必须标注 `NON-SIMULATABLE ILLUSTRATION`；
- Engineering 输出必须声明 PDK 来源与版本；
- 两种模式的 Manifest 都记录 mode 字段，防止误用。

## Bundled resources

| 文件 | 何时读取 |
|---|---|
| `references/illustration-mode.md` | 需要 Illustration 模式符号/绘制细节 |
| `references/engineering-mode.md` | 需要 Engineering 模式 Xschem/SPICE/PDK 流程 |
| `references/erc-rules.md` | 需要 ERC 规则细节 |
| `agents/openai.yaml` | 需要 OpenAI-compatible agent 集成 |

## 输出

```
<view-name>/
├── model.normalized.yaml
├── diagram.drawio（Illustration） 或 diagram.sch + diagram.spice（Engineering）
├── diagram.svg / .png / .pdf
├── erc.md
├── validation.json / .md
└── manifest.yaml
```
