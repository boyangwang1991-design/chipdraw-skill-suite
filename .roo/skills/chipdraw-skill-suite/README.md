# chipdraw-skill-suite（芯片研发智能绘图 Skill Suite）

从 SoC 架构、IP 微架构、RTL 状态与数字时序，到晶体管级电路，基于统一入口、分层专业语义和确定性渲染后端，生成**可编辑、可验证、可追踪、可持续更新**的工程图形资产。

本目录是完整可安装的 Skill 套件（建设方案 §7）：

```text
chipdraw-skill-suite/
├── SKILL.md                    # 统一入口与路由（chip-diagram-router）
├── diagram-routing.md          # 路由决策细节
├── openai.yaml                 # 入口 agent 定义
├── skills/                     # 4 个专业子 Skill
│   ├── draw-soc-architecture/      # SoC 系统级绘图
│   ├── draw-ip-architecture/       # IP 微架构绘图
│   ├── draw-rtl-behavior/          # FSM / WaveDrom / 事务序列
│   └── draw-transistor-schematic/  # 晶体管原理图（Illustration / Engineering）
├── chipdiagram/                # 核心 Python 包（引擎/适配器/校验器/CLI）
├── assets/                     # 资产层（不直接触发）
│   ├── schemas/                # 8 个 JSON Schema（common/soc/ip/fsm/timing/sequence/circuit/view）
│   ├── libraries/              # AIXSILICON 明暗主题 + 4 个符号库
│   └── examples/               # 5 个 Golden Case
├── tests/                      # unit/golden/integration/visual 分层测试
├── pyproject.toml              # 工程配置（uv）
└── package.json                # 工程配置（wavedrom-cli）
```

## 快速开始

```bash
# 安装依赖（uv）
uv pip install -e ".[test]"

# 从结构化模型生成图形
uv run chipdiagram build assets/examples/pic-subsystem/pic.yaml \
  --view soc_overview --format drawio,svg,png --out docs/diagrams/pic

# 从 RTL 抽取 IP 结构
uv run chipdiagram extract rtl/pic_top.sv --type ip --top pic_top --out build/model/pic.yaml

# 校验但不生成
uv run chipdiagram validate assets/examples/pic-subsystem/pic.yaml --profile soc-signoff

# 比较两个版本
uv run chipdiagram diff old/manifest.yaml new/manifest.yaml --out reports/diagram-diff
```

## CLI 子命令

| 子命令 | 用途 |
|---|---|
| `chipdiagram build <input> --view <view> --format <fmt> --out <dir>` | 从结构化模型生成图形 |
| `chipdiagram extract <input> --type <type>` | 从 Markdown/RTL/FuseSoC/SystemRDL/IP-XACT/SPICE 抽取语义模型 |
| `chipdiagram validate <input> --profile <profile>` | Schema + 专业规则校验 |
| `chipdiagram diff <old> <new> --out <dir>` | 图形版本差异比较 |

## 依赖

- **Python 3.9+**、PyYAML、jsonschema（必需）
- **draw.io CLI**（导出 PNG/SVG/PDF，可选；缺失时降级为 `.drawio` + diagrams.net URL）
- **Graphviz `dot`**（FSM / 大型框图布局，可选）
- **wavedrom-cli**（数字时序 SVG/PNG，可选；缺失时输出 WaveJSON）
- **Xschem / ngspice**（Engineering Mode 电路，可选；缺失时输出 SPICE 网表 + ERC 报告）

## 测试

```bash
uv run python -m pytest tests -q
```

分层：`unit`（Schema/校验/模型）、`golden`（5 个 Golden Case）、`integration`（端到端流水线）、`visual`（Draw.io XML 结构）。

## 上游复用边界

- 通用绘图引擎**封装**自 drawio-skill（MIT License），位于 [`chipdiagram/engines/shared/`](chipdiagram/engines/shared/README.md)，保持只读快照便于上游同步；
- 芯片语义、Schema、适配器、校验器、渲染后端均为本项目独立实现；
- 遵循建设方案 §6/§15 的"封装不硬改"与"固定基线、季度评估"策略。
