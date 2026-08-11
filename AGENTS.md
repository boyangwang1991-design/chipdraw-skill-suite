# AGENTS

本仓库是**芯片研发智能绘图 Skill Suite**（chipdraw-skill-suite）的实现。

## 项目结构

完整套件位于 `.roo/skills/chipdraw-skill-suite/`，根目录保留本文档与建设方案。

```
chipdraw-skill-suite/            # 根（本 README/AGENTS 所在）
├── 芯片研发智能绘图Skill_Suite详细建设方案.md
├── reference/drawio-skill-main/ # 上游 drawio-skill（只读参考）
└── .roo/skills/chipdraw-skill-suite/   # 完整可安装 Skill 套件
```

## 关键约定

- **语言**：文档、注释、Issue 消息、SKILL.md 一律使用简体中文。
- **目录**：所有代码、Schema、示例、测试都放在 `.roo/skills/chipdraw-skill-suite/` 下，不散落根目录。
- **核心包**：`chipdiagram/`（引擎/适配器/校验器/CLI），通过 `chipdiagram` 命令或 `uv run chipdiagram ...` 调用。
- **Schema**：`schemas/` 七个 JSON Schema，`common.schema.json` 为公共 Envelope + 专用节点。
- **渲染后端**：Draw.io（SoC/IP）、Graphviz（FSM/大型框图）、WaveDrom（数字时序）、Xschem（晶体管工程图）。
- **质量门禁**：ERROR 阻断、WARNING 草稿+waiver、INFO 不阻断；推断标 `inferred` 不伪装事实。
- **上游复用**：`chipdiagram/engines/shared/` 封装上游 drawio-skill 脚本（只读），芯片语义独立实现，不硬改上游。

## 常用命令

```bash
cd .roo/skills/chipdraw-skill-suite
uv run chipdiagram --help
uv run python -m pytest tests -q
```
