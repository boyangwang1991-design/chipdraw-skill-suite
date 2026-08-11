# FSM 建模与校验（建设方案 §3.4-A）

## 输入模型

```yaml
behavior:
  initial_state: idle
  encoding: binary            # one_hot / binary / gray / unknown
  states:
    - {id: idle, category: normal}
    - {id: transfer, category: normal}
    - {id: error, category: fault}
  transitions:
    - {from: idle, to: transfer, condition: "start && cfg_valid", action: clear_count, source: rtl}
    - {from: transfer, to: error, condition: bus_error, action: set_error_irq, source: rtl}
```

## 状态分类

- `normal`：常规状态（蓝）；
- `fault` / `error`：故障状态（红）；
- `reset`：复位状态（灰）；
- `recovery`：恢复状态（绿）。

## 校验规则

- 初始状态必须存在且唯一；
- 所有 Transition 端点必须存在（起点/终点在 states 中）；
- 检查不可达状态（从 initial BFS）、无出口状态、孤立状态；
- 检查同一状态下明显冲突或重复条件；
- 检查 Default/Error/Recovery 路径（缺失记 WARNING）；
- 可选检查状态编码是否重复或不完整；
- 从 RTL 提取时，比较 `case` 分支、状态寄存器和跳转条件；
- **不确定条件必须标为 `inferred`，不能伪装成 RTL 事实**（虚线渲染）。

## 渲染

- 初始状态用双圈（doublecircle）；
- `inferred` 转移用虚线；
- 条件 + 动作作为边标签。
