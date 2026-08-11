# SoC 图形约定（建设方案 §3.2 布局规则）

## 布局规则

- 主数据流默认从左到右；
- CPU/Initiator 放左侧，Memory/Target/外设放右侧；
- Interconnect/NoC 位于中间主干；
- CRG、Power Manager、Safety Manager 优先放顶部；
- 外部接口和 PHY 靠页面边缘；
- Subsystem 使用容器表达层级；
- 不同 Power/Safety/Security Domain 使用淡色容器和清晰图例；
- 总线默认收敛为一条逻辑接口，不自动展开 AXI 五通道；
- 超过 20 个可见 Block 或 35 条连接时，触发自动拆图建议；
- 所有连接采用正交路由，不穿越 Block。

## 容器表达

| 元素 | 表达方式 |
|---|---|
| Subsystem / Die / Chiplet | swimlane 容器，子坐标相对父容器 |
| Power/Safety/Security Domain | 淡色容器 + 图例 |
| 外部接口 / PHY | 靠边缘的 neutral 色块 |

## 颜色（对齐 aixsilicon-light 主题）

| 块类型 | palette role |
|---|---|
| CPU / DSP / NPU | primary（蓝） |
| Memory | success（绿） |
| Peripheral | accent（橙） |
| Subsystem | secondary（紫） |
| Interconnect / Controller / Bridge | warning（黄） |
| PHY / 外部 | neutral（灰） |
