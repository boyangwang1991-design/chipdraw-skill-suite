# 晶体管符号库

晶体管/电路级绘图使用的器件符号与默认样式（建设方案 §3.5）。

## Illustration Mode 符号

| 器件 | draw.io style | 颜色 |
|---|---|---|
| PMOS | `shape=process` | primary 蓝 |
| NMOS | `shape=process` | success 绿 |
| Resistor | `shape=resistor` | warning 黄 |
| Capacitor | `shape=capacitor` | accent 橙 |
| Supply / Ground | `ellipse` | neutral 灰 |

## Engineering Mode

- MOS 器件必须带模型（`pmos_1v8` 等）与端子（g/d/s/b）；
- 参数用字符串（`w: 2.0um`、`l: 0.18um`）；
- 子电路实例 `X<name>` 引用 `.subckt` 定义；
- 符号库由 PDK 提供（`circuit.pdk.symbol_library`），本仓不携带商业 PDK。

## 输出标注

- Illustration：`NON-SIMULATABLE ILLUSTRATION`；
- Engineering：SPICE 网表 + ERC 报告 + Xschem `.sch`。
