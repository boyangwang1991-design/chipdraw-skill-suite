# diagram-common（公共资源包）

本目录是芯片绘图套件的公共代码与资源包，**不作为用户直接触发入口**
（建设方案 §2.2）。它指向仓库根部的共享实现：

| 资源 | 位置 | 用途 |
|---|---|---|
| 核心包 | `chipdiagram/`（仓库根） | 模型/校验/视图/渲染/发布/CLI |
| Schema | `schemas/` | 七个 JSON Schema |
| 主题与符号 | `libraries/` | AIXSILICON 明暗主题、SoC/IP/协议/晶体管符号 |
| 上游脚本 | `chipdiagram/engines/shared/` | 封装自 drawio-skill 的通用引擎 |
| 示例 | `examples/` | 5 个 Golden Case |
| 测试 | `tests/` | unit/golden/integration/visual |

## 使用

各专业子 Skill 通过 `uv run chipdiagram ...` 调用共享 CLI，不重复实现引擎逻辑。
