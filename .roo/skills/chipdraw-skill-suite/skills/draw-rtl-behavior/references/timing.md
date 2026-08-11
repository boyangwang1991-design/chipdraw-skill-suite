# WaveDrom 数字时序建模（建设方案 §3.4-B，对齐 WaveDrom Tutorial）

## 输入模型

```yaml
behavior:
  clock:
    name: pclk
    period: 10ns            # 周期，自动成为时间标尺 tick
    # wave: "P......."      # 可选：显式时钟 wave；缺省按信号最大周期自动生成
    # polarity: positive    # positive / negative（负极性 N/n 开头）
    # edge_marker: true     # 工作沿画标记（P/N）还是纯电平（p/n）
    # display: true         # false 时时钟不进图，仅作 head.tick 标尺
    # phase: 0.5            # 可选相位偏移
  signals:
    - {name: psel, wave: "0.1...0"}
    - {name: penable, wave: "0..1..0"}
    - {name: paddr, wave: "x.3...x", data: ["ADDR"]}
    - {name: pwdata, wave: "x.4...x", data: ["DATA"]}
    - {name: pready, wave: "1.....1"}
  markers:
    - {cycle: 2, text: setup}
    - {cycle: 3, text: access}
  edges:                    # 可选：箭头（node 锚点）
    - "a~b t1"
    - "c->d 建立时间"
  config:                   # 可选：渲染配置
    hscale: 1
    # skin: narrow
  head:                     # 可选：图上方（标题/标尺）
    text: "APB Write Transaction"
    tick: 0
  foot:                     # 可选：图下方（说明）
    text: "Figure 100"
    tock: 9
  origin: spec            # spec / simulation / inferred
  protocol_rules: APB setup/access 相位
```

## Wave 字符语义（WaveDrom Tutorial）

- `0` 低电平、`1` 高电平、`x` 未知、`z` 高阻、`=` 同前值、`-` 无变化；
- `.` **延续前一状态一个周期**（不产生独立 data 位）；
- `|` Spacer/Gap 分隔符（不占时间周期，仅视觉分隔）；
- `+` 与下一周期同时刻（Sharp 线箭头同拍标记）。

## Wave 书写约定（渲染语义，建模必读）

WaveDrom 把每个字符边界都当作一次状态变化来渲染，因此：

- **连续同电平必须用 `.` 延续**：`"1."` 表示两拍高电平；写成 `"11"` 会在同值相邻处
  渲染出一条冗余跳变沿（glitch），波形看起来像信号抖动。`"00"` 同理。
- **首字符必须显式**：`.` 是"延续前一状态"，而首字符没有前态可延续，以 `.` 开头
  会被渲染为未知态（斜线填充）。首字符应写 `0`/`1`/`x`/`z` 或数据字符。
- **连续数字不是 glitch**：`2-9`/`=` 是连续 data 拍（如 `"xx45xxx"` 表示两拍数据），
  属合法写法，校验器与人工审查都不要误判。
- 自检方法：写完后扫描 wave，同值相邻仅允许出现在数字 data 拍中；电平段一律
  "显式初值 + `.` 延续"。校验器对 `11`/`00` 与首字符 `.` 报 WARNING（TIMING_WAVE_GLITCH /
  TIMING_WAVE_LEADING_DOT），命中即按上述规则改写。

## 周期对齐与 VALID 窗口覆盖（防 off-by-one）

wave 字符串的**字符索引就是周期号**（从 0 起，`|` 不占周期）。手写 wave 时最容易犯
的错误是 `.` 多数/少数一个，导致数据或地址整体错一拍（off-by-one）。推荐工作流：

1. **先列事件表**：把每个关键事件写成 (周期号, 事件) 列表，如
   `(1, AW 握手)`、`(2, W0)`、`(3, W1+WLAST)`、`(5, B 响应)`；
2. **按索引逐字符写 wave**：每个周期号对应一个字符位置，数据字符必须落在事件表
   指定的索引上；
3. **回对 VALID 窗口覆盖**：协议要求 VALID 不得先于同通道地址/控制/数据置起，且
   握手（含等待态）期间数据保持稳定。因此同通道（同前缀，如 `aw*`/`w*`/`b*`）带 data
   的信号，其有效字符（`.` 展开为前值后）必须覆盖整个 `*valid` 为高的窗口。
   例如 `awvalid: "1.0....1.0...."` 的高窗口为 cycle0-1 与 7-8，则 `awaddr` 应写
   `"2.x....3.x...."`（A0 覆盖 0-1、A1 覆盖 7-8），少写一个 `.` 就会 off-by-one。

校验器对未覆盖的 VALID 周期报 WARNING（TIMING_HANDSHAKE_DATA_UNCOVERED），命中即按
事件表核对字符索引并修正错位。

## 时钟字符

| 字符 | 含义 |
|---|---|
| `p` | 正极性时钟，无边沿标记 |
| `P` | 正极性时钟，带边沿标记 |
| `n` | 负极性时钟，无边沿标记 |
| `N` | 负极性时钟，带边沿标记 |
| `h`/`l`/`H`/`L` | 半拍电平（用于时钟门控混合） |

> 时钟字符每个代表一个**完整方波周期**；`p.......` = 8 周期正极性时钟。
> 可与普通电平混合制造 **Clock Gating** 效果，如 `phnlPHNL`。
> 引擎缺省会按信号最大周期数自动生成时钟 wave，无需手写。

## 分组

两种表达等价，WaveDrom 原生支持嵌套数组分组：

```yaml
# 内联嵌套数组（推荐，保留结构）
signals:
  - ["Master",
      ["ctrl",
        {name: write, wave: "01.0...."},
        {name: read,  wave: "0...1..0"}],
      {name: addr, wave: "x3.x4..x", data: ["A1", "A2"]}]
  - {}
  - ["Slave",
      {name: ack,   wave: "x01x0.1x"},
      {name: rdata, wave: "x.....4x", data: ["Q2"]}]

# 或顶层 groups 声明（平坦 signals + 分组）
groups:
  - {name: Master, signals: [write, read, addr]}
signals:
  - {name: write, wave: "01.0...."}
```

## 每信号 period/phase（DDR 示例）

```yaml
signals:
  - {name: CK,   wave: "P.......", period: 2}
  - {name: CMD,  wave: "x.3x=x4x=x=x=x=x", data: "RAS NOP CAS NOP NOP NOP NOP", phase: 0.5}
  - {name: DQS,  wave: "z.......0.1010z."}
  - {name: DQ,   wave: "z.........5555z.", data: "D0 D1 D2 D3"}
```

## node + edge 箭头

```yaml
signals:
  - {name: A, wave: "01........0....", node: ".a........j"}
  - {name: B, wave: "0.1.......0.1..", node: "..b.......i"}
edges:
  - "a~b t1"
  - "c-~>d time 3"
  - "g<->h 3 ms"
```

连接符：`~`(spline) `-`(直线) `|`(直角) `>`(箭头) `<`(反向) `+`(同拍)。

## 校验规则（行为校验器）

- **data 数量 = wave 中引用字符数**（数字 `2-9` 与 `=`；`x/z` 未知/高阻不引用，`.` 延续不引用，`|` 分隔不计）；
- `x2.....x` + `data:["ADDR"]` **合法**（数字 `2` 唯一引用），不要误判；
- **连续同电平即 glitch**：`11`/`00` 同值相邻会渲染冗余跳变沿，应写 `1.`/`0.`（WARNING: TIMING_WAVE_GLITCH）；
- **首字符不得为 `.`**：无前态可延续会渲染为未知态，首字符应为显式电平（WARNING: TIMING_WAVE_LEADING_DOT）；
- **VALID 窗口覆盖**：同通道带 data 信号的有效字符必须覆盖整个 `*valid` 为高窗口（VALID 不得先于数据置起、等待态期间数据须稳定，防 off-by-one，WARNING: TIMING_HANDSHAKE_DATA_UNCOVERED）；
- node 与 wave 长度一致（箭头锚点对齐）；
- 显式时钟 wave 只能含 `p/P/n/N/h/H/l/L/0/1/x/z/./|`；
- Clock 与时间标尺（period）存在；
- 必选信号缺失（`required: true`）；
- 协议规则：如 APB 的 Setup/Access 相位、AXI 的 VALID/READY；
- Ready/Valid 场景是否存在数据稳定性冲突；
- Reset 释放与 Clock 的关系是否合理；
- 图示例是"规范要求""RTL 仿真采样"还是"AI 推断"必须明确标注（`origin`）。

## 适用场景

AXI/APB/AHB 读写、Ready/Valid、Request/Acknowledge 握手、Reset Assertion/Deassertion、
Clock Gating 与切频、Interrupt 产生/锁存/清除、CDC 握手、Pipeline 周期关系、
Fault Injection/Detection/Response 时序。

## 参考资产

WaveDrom 官方能力清单与示例：`assets/libraries/wavedrom-examples/`（只读参考），
含时钟字符、分组、period/phase、config/head-foot、箭头、逻辑电路图等 WaveJSON 示例。
