# WaveDrom 数字时序建模（建设方案 §3.4-B）

## 输入模型

```yaml
behavior:
  clock: {name: pclk, period: 10ns}
  signals:
    - {name: psel, wave: "0.1...0"}
    - {name: penable, wave: "0..1..0"}
    - {name: paddr, wave: "x.3...x", data: ["ADDR"]}
    - {name: pwdata, wave: "x.4...x", data: ["DATA"]}
    - {name: pready, wave: "1.....1"}
  markers:
    - {cycle: 2, text: setup}
    - {cycle: 3, text: access}
  origin: spec            # spec / simulation / inferred
  protocol_rules: APB setup/access 相位
```

## Wave 字符语义

- `0` 低电平、`1` 高电平、`x` 未知/高阻、`=` 同前值；
- `.` 分隔周期；
- data 数组每个元素对应一个非 `.` 周期；
- 数据数量与周期数不一致 → **ERROR**。

## 校验规则

- Wave 字符串长度和 Signal 数据数量一致；
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
