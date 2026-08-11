# Illustration Mode（示意图）

## 用途

规格、培训、评审和 PPT 中的 CMOS 反相器、NAND/NOR、Latch、Level Shifter、SRAM Bitcell 等原理示意。

## 特点

- 使用 Draw.io/SVG 输出；
- 强调可读性和结构说明；
- 允许简化 Bulk、模型和参数；
- 输出必须标注 `NON-SIMULATABLE ILLUSTRATION`；
- **不生成权威 SPICE 网表**。

## 符号简化

| 对象 | 允许简化 |
|---|---|
| MOS 器件 | 用 process 形状，标注 P/N 与模型名 |
| Bulk 连接 | 可省略或用默认假设 |
| 参数 | 可省略 W/L |
| 模型 | 可只写 `pmos/nmos` |

## 输出标注

- 标题固定标注 `NON-SIMULATABLE ILLUSTRATION`；
- Manifest 的 circuit.mode = `illustration`；
- 防止被误当工程网表（建设方案 §16 风险控制）。
