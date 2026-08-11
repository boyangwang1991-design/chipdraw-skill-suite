# 协议符号库

AXI/AHB/APB/CHI/NoC/TileLink 等总线协议的图形符号与边标签约定。

## 协议缩写

| 协议 | 全称 | 数据位宽（典型） |
|---|---|---|
| AXI | Advanced eXtensible Interface | 32/64/128/256/512/1024 |
| AXI-Lite | 轻量 AXI | 32/64 |
| AHB | Advanced High-performance Bus | 32/64/128 |
| APB | Advanced Peripheral Bus | 32/64 |
| CHI | Coherent Hub Interface | 32~512 |
| NoC | Network-on-Chip | 可变 |
| TileLink | Berkeley 互联协议 | 32/64/128/256 |

## 接口展开（collapse.axi_channels）

- 默认收敛为一条逻辑接口；
- 展开时五通道：AW（写地址）/ W（写数据）/ B（写响应）/ AR（读地址）/ R（读数据）；
- 边标签标注 `AXI:128b` 等。

## 方向语义

- Initiator/Target、Master/Slave、Source/Sink；
- 连接两端方向应互补（校验器检查）。

## 符号检索

需要官方协议图标时：

```bash
uv run python chipdiagram/engines/shared/shapesearch.py "axi"
```
