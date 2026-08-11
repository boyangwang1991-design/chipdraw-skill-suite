# IP 图形约定（建设方案 §3.3）

## 线型/颜色语义

| 连接类型 | 表达 |
|---|---|
| 数据通路 | 蓝色粗实线 |
| 控制通路 | 紫色细实线 |
| Clock | 绿色虚线 |
| Reset | 灰色虚线 |
| Interrupt / Error | 橙色实线 |
| CDC/RDC Block | 黄色底色 |
| Safety Mechanism | 红色边框 |

> 位宽、协议、Latency 作为边标签，**不用颜色单独表达**（色弱与黑白打印可读性，建设方案 §16）。

## 端口布局

- 输入端口在左侧，输出端口在右侧；
- Clock/Reset/Power 端口优先置于上侧或下侧；
- Pipeline Stage 使用等宽泳道或顶部 Stage 标记。

## 块类型 → 主题色

| 块类型 | palette role |
|---|---|
| Datapath | primary（蓝） |
| Control | secondary（紫） |
| Buffer / FIFO | success（绿） |
| Arbiter / Converter / MUX | warning（黄） |
| Synchronizer | danger（红） |
