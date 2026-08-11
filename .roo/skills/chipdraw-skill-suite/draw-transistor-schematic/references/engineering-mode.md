# Engineering Mode（工程原理图）

## 用途

基于 SPICE/CDL/PDK 符号生成或检查具有网络语义的原理图。

## 特点

- 以 SPICE/CDL 或结构化 Circuit YAML 为事实源；
- 使用 Xschem 作为原理图后端；
- Device 必须具有类型、模型、参数和端子；
- 输出 Xschem 源文件、SPICE 网表、SVG/PDF 和 ERC 报告；
- 需要 PDK 时由环境提供 PDK 路径和符号库，**Skill 不携带商业 PDK**。

## 工作流

1. 输入：SPICE/CDL（`chipdiagram extract`）或 Circuit YAML；
2. 校验：ERC（见 erc-rules.md）；
3. 生成：SPICE 网表 + `.sch` 骨架 + ERC 报告；
4. 工具链可用时：Xschem 打开 `.sch`，ngspice 仿真验证。

## PDK 处理

- PDK 路径、符号库通过环境/配置提供（`circuit.pdk`）；
- 不随 Skill 分发商业 PDK（许可证约束，建设方案 §16）；
- Manifest 记录 PDK 名称与版本。

## 输出

```
diagram.spice    # SPICE 网表（结构级，非仿真优化）
diagram.sch      # Xschem 源文件
erc.md           # ERC 报告
diagram.svg/pdf  # 工具链可用时渲染
```

> `_to_spice()` 生成结构级网表（不做晶体管尺寸优化），标注
> "NON-AUTHORITATIVE until validated against PDK"。
