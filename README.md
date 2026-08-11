# chipdraw-skill-suite

芯片研发智能绘图 Skill Suite 仓库。

本仓库是 [`芯片研发智能绘图Skill_Suite详细建设方案.md`](芯片研发智能绘图Skill_Suite详细建设方案.md) 的落地实现：从 SoC 架构、IP 微架构、RTL 状态与数字时序，到晶体管级电路，基于统一入口、分层专业语义和确定性渲染后端，生成**可编辑、可验证、可追踪、可持续更新**的工程图形资产。

## 套件位置

完整 Skill 套件统一位于 **[`.roo/skills/chipdraw-skill-suite/`](.roo/skills/chipdraw-skill-suite/SKILL.md)**：

```
.roo/skills/chipdraw-skill-suite/
├── SKILL.md                    # 统一入口与路由（chip-diagram-router）
├── diagram-routing.md          # 路由决策细节
├── openai.yaml                 # 入口 agent 定义
├── diagram-common/             # 公共代码与资源包（不直接触发）
├── draw-soc-architecture/      # SoC 系统级绘图
├── draw-ip-architecture/       # IP 微架构绘图
├── draw-rtl-behavior/          # FSM / WaveDrom / 事务序列
├── draw-transistor-schematic/  # 晶体管原理图（Illustration / Engineering）
├── chipdiagram/                # 核心 Python 包（引擎/适配器/校验器/CLI）
├── schemas/                    # 7 个 JSON Schema
├── libraries/                  # AIXSILICON 明暗主题 + 4 个符号库
├── examples/                   # 5 个 Golden Case
├── tests/                      # unit/golden/integration/visual 分层测试
├── pyproject.toml / package.json
└── .venv/                      # uv 虚拟环境（可选）
```

## 快速开始

```bash
# 进入套件目录
cd .roo/skills/chipdraw-skill-suite

# 安装依赖（uv）
uv pip install -e ".[test]"

# 从结构化模型生成图形
uv run chipdiagram build examples/pic-subsystem/pic.yaml \
  --view soc_overview --format drawio,svg,png --out docs/diagrams/pic

# 从 RTL 抽取 IP 结构
uv run chipdiagram extract rtl/pic_top.sv --type ip --top pic_top --out build/model/pic.yaml

# 校验但不生成
uv run chipdiagram validate integration/soc.yaml --profile soc-signoff

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
cd .roo/skills/chipdraw-skill-suite
uv run python -m pytest tests -q
```

分层：`unit`（Schema/校验/模型）、`golden`（5 个 Golden Case）、`integration`（端到端流水线）、`visual`（Draw.io XML 结构）。

## 上游复用边界

- 通用绘图引擎**封装**自 [`reference/drawio-skill-main`](reference/drawio-skill-main/README.md)（MIT License），位于 [`chipdiagram/engines/shared/`](.roo/skills/chipdraw-skill-suite/chipdiagram/engines/shared/README.md)，保持只读快照便于上游同步；
- 芯片语义、Schema、适配器、校验器、渲染后端均为本项目独立实现；
- 遵循建设方案 §6/§15 的"封装不硬改"与"固定基线、季度评估"策略。
