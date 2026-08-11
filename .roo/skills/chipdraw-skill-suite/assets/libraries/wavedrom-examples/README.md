# WaveDrom 官方能力清单与示例（WaveJSON 参考）

> 来源：WaveDrom 官方 "Hitchhiker's Guide to the WaveDrom"（observablehq.com/@drom/wavedrom，v286）与
> WaveDrom Tutorial（wavedrom.com）。本目录为 **只读参考**，供芯片时序建模时对齐 WaveJSON 语法。
> 原 notebook 源码存档：`SOURCE_wavedrom_observable_notebook.js`（本目录，只读追溯）。

WaveJSON 是描述数字时序图的 JSON 格式。核心元素 `signal` 是 **WaveLane** 数组；
每个 WaveLane 必填 `name` 与 `wave`。每个 `wave` 字符代表一个时间周期。

## 目录

### 基础（Hitchhiker's Guide 教程）

| 文件 | 内容 |
|---|---|
| [`examples/wave-basics.json`](examples/wave-basics.json) | 基础波形 + 时钟字符 + 组合 |
| [`examples/groups-gaps.json`](examples/groups-gaps.json) | Spacer/Gap（`\|`）+ 分组 |
| [`examples/groups-nested.json`](examples/groups-nested.json) | 嵌套分组（Master/Slave） |
| [`examples/period-phase.json`](examples/period-phase.json) | 每信号 period/phase（DDR 读事务） |
| [`examples/config-head-foot.json`](examples/config-head-foot.json) | config(hscale/skin) + head/foot |
| [`examples/head-foot-jsonml.json`](examples/head-foot-jsonml.json) | head/foot JsonML 富文本 |
| [`examples/arrows-splines.json`](examples/arrows-splines.json) | Spline 箭头（edge/node） |
| [`examples/arrows-sharp.json`](examples/arrows-sharp.json) | 直角箭头（edge/node） |
| [`examples/gray-counter.json`](examples/gray-counter.json) | Gray 码计数器 |
| [`examples/logic-assign.json`](examples/logic-assign.json) | 逻辑电路图 `assign`（tut2） |

### 总线协议（AXI4 / AHB / 流式）

| 文件 | 内容 |
|---|---|
| [`examples/axi4-aw-handshake.json`](examples/axi4-aw-handshake.json) | AXI4 AW 通道握手（gaps） |
| [`examples/ahb-reads.json`](examples/ahb-reads.json) | AHB 读突发（gaps） |
| [`examples/ahb-wait-states.json`](examples/ahb-wait-states.json) | AHB 读含等待态（head/foot/gaps） |
| [`examples/ahb-writes.json`](examples/ahb-writes.json) | AHB 写突发（head/foot/gaps） |
| [`examples/streaming-valid-ready.json`](examples/streaming-valid-ready.json) | 流式 valid/ready |
| [`examples/streaming-backpressure.json`](examples/streaming-backpressure.json) | 流式背压（cpu data） |

### DDR / LVDS / 时序窗口

| 文件 | 内容 |
|---|---|
| [`examples/ddr-lvds-sampling.json`](examples/ddr-lvds-sampling.json) | DDR/LVDS 双沿采样（period/phase） |
| [`examples/ddr-phase-shift.json`](examples/ddr-phase-shift.json) | DDR 相位对齐 |
| [`examples/lvds-state-machine.json`](examples/lvds-state-machine.json) | LVDS 接收状态机 |
| [`examples/setup-hold-window.json`](examples/setup-hold-window.json) | 建立/保持时间窗（over/under） |
| [`examples/setup-hold-multi.json`](examples/setup-hold-multi.json) | 多周期建立/保持窗 |

### 模拟波形（pw path）与位域

| 文件 | 内容 |
|---|---|
| [`examples/analog-pw-simple.json`](examples/analog-pw-simple.json) | path 波形（pw）入门 |
| [`examples/analog-pw-shapes.json`](examples/analog-pw-shapes.json) | 锯齿/三角/RC 波形 |
| [`examples/analog-pw-sine.json`](examples/analog-pw-sine.json) | 正弦波形 |
| [`examples/pll-lockup.json`](examples/pll-lockup.json) | PLL 锁定过程（使能→锁定标志） |
| [`examples/edge-delay-arrows.json`](examples/edge-delay-arrows.json) | 延时箭头 + arcFontSize |
| [`examples/reg-bitfield.json`](examples/reg-bitfield.json) | 寄存器位域图（reg） |
| [`examples/reg-bitfield-attrs.json`](examples/reg-bitfield-attrs.json) | 位域带 attr/type |
| [`examples/riscv-i-type.json`](examples/riscv-i-type.json) | RISC-V I-type 指令位域 |

### 速查

| 文件 | 内容 |
|---|---|
| [`wave-symbols.md`](wave-symbols.md) | wave 字符、时钟、data、node/edge、gaps、over/under、pw、reg 速查表 |

## 关键能力（对应实现差距）

1. **wave 字符语义**：`0/1/x/z/=/-/h/l/H/L/p/n/P/N/u/d/2-9` + `.`（延续） + `|`（Spacer/Gap 分隔） + `+`（同拍标记，Sharp 线箭头用）。
2. **时钟 lane**：`p/P`（正极性带/不带边沿标记）、`n/N`（负极性带/不带标记）；可与其他电平混合做 **时钟门控**。
3. **分组**：`['组名', {...}, ...]` 可嵌套，用于总线/主从分组。
4. **每信号 period/phase**：`period` 乘数、`phase` 相位偏移（DDR、相移时钟）。
5. **config**：`hscale`（水平缩放）、`skin`（'default'/'narrow'）、`arcFontSize`（箭头字号）。
6. **head/foot**：`tick`（对齐标尺）、`tock`（标尺间）、`text`（JsonML 支持 h1-h6/error/warning/info/success/muted + 任意 tspan 属性）。
7. **node + edge 箭头**：`node` 字符串标记周期点，`edge` 数组用 `~`(spline)/`-`(line)/`|`(sharp)/`>`(箭头)/`<`(反向) 组合连接，可带标签。
8. **gaps**：顶层 Gap 表达式（`. s`=Spacer 尺寸、`1`-`9`=Gap 位置），用于总线空闲/延迟插入。
9. **over/under**：lane 级建立/保持时间窗口注释。
10. **pw path 波形**：`wave: ['pw', {d:'SVG path'}]` 绘制模拟/自定义波形（正弦/锯齿/三角/RC/PLL）。
11. **reg 位域图**：`reg` 数组 + `config`（hspace/vspace/lanes/compact/hflip/vflip）渲染寄存器图。
12. **`assign`（逻辑电路图，tut2）**：`["out", [运算符树]]`，运算符 `& | ^ ~ ~& ~^` 与 IEC 门 `AND OR XOR NAND NOR XNOR INV BUF`。
