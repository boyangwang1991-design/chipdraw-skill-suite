# ERC 规则（建设方案 §3.5 工程校验）

## 规则清单

| 规则码 | 规则 | 严重度 |
|---|---|---|
| `CIRCUIT_DEVICE_DUP` | 器件 id 重复 | ERROR |
| `CIRCUIT_NET_DUP` | 网络名重复 | ERROR |
| `CIRCUIT_MOS_TERMINALS` | MOS 四端（g/d/s/b）连接不完整 | ERROR |
| `CIRCUIT_BULK_RULE` | Bulk 连接不符合常规（PMOS bulk 接电源/NMOS 接地） | WARNING |
| `CIRCUIT_POWER_SHORT_RISK` | 器件端子同时连接电源与地（非 R/C/L） | ERROR |
| `CIRCUIT_GATE_DANGLING` | MOS Gate 悬空或未声明网络 | ERROR |
| `CIRCUIT_SUBCKT_PORT_COUNT` | 子电路实例端口数与定义不一致 | ERROR |
| `CIRCUIT_SUBCKT_NO_MODEL` | 子电路实例缺少 model | WARNING |

## 电源/地网络

- 电源网络：`vdd`、`vcc`、`vdd!`、`avdd`、`vdda`；
- 地网络：`vss`、`gnd`、`gnd!`、`0`、`vssa`。

## 处理原则

- **ERC 错误阻断正式输出**；
- 告警进入 waiver 流程（`diagrams/waivers/`）；
- Engineering Mode 必须在 ERC 通过后才发布正式原理图。

## 与校验器对应

`chipdiagram.validators.circuit_validator` 实现以上全部规则，`xschem.circuit._render_engineering`
在生成时自动调用并输出 `erc.md`。
