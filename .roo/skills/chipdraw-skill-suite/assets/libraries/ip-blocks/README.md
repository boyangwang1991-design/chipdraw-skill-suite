# IP 符号库

IP 微架构级绘图使用的块类型与默认样式（建设方案 §3.3 图形约定）。

| 块类型 | draw.io style | 颜色 |
|---|---|---|
| Datapath | `rounded=1` | primary 蓝 |
| Control | `rounded=1` | secondary 紫 |
| Pipeline Stage | `rounded=1`（等宽泳道） | primary |
| Buffer / FIFO / Queue | `rounded=1` | success 绿 |
| Async FIFO | `rounded=1`（黄底标注） | warning 黄 |
| Arbiter | `rhombus` | warning 黄 |
| MUX / Decoder | `rhombus` | warning 黄 |
| Converter（位宽/时钟） | `rounded=1` | warning 黄 |
| Synchronizer | `rounded=1` | danger 红 |
| Safety Mechanism | `rounded=1`（红色边框） | danger |

## 线型约定（建设方案 §3.3）

| 连接类型 | 样式 |
|---|---|
| 数据通路 | 蓝色粗实线（`strokeWidth=3`） |
| 控制通路 | 紫色细实线 |
| Clock | 绿色虚线 |
| Reset | 灰色虚线 |
| Interrupt/Error | 橙色实线 |

> 位宽、协议、Latency 作为边标签，不用颜色单独表达。
