# 总线协议规则（建设方案 §3.2）

## 协议位宽约束

| 协议 | 数据位宽 | 地址位宽 | ID 位宽 |
|---|---|---|---|
| AXI | 32/64/128/256/512/1024 | 32/40/48/64 | 4/5/6/8/10/16 |
| AXI-Lite | 32/64 | 32/64 | — |
| AHB | 32/64/128 | 32 | — |
| APB | 32/64 | 32 | — |
| CHI | 32~512 | 40~56 | 4~12 |
| TileLink | 32/64/128/256 | 32~56 | — |

> 校验器按此表做位宽合法性检查（WARNING）。协议别名：AXI4→AXI、AXI4-Lite→AXI-Lite。

## 方向语义

- Initiator/Target（AXI、CHI）
- Master/Slave（AHB、APB）
- Source/Sink（流式接口）

连接两端应满足方向互补；非法 role 记 ERROR。

## 地址窗口

- base 与 size 用十六进制（如 `0x4000_0000`）；
- 窗口重叠 → ERROR；
- 无上游可达路径 → WARNING。

## 图例：接口展开

- 默认收敛为一条逻辑接口（`collapse.axi_channels: true`）；
- 需要逐通道展开时（`interface_expanded` 视图）才展示 AW/W/B/AR/R 五通道。
