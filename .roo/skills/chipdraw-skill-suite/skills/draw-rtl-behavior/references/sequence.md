# 事务序列建模（建设方案 §3.4-C）

## 定位

事务序列图用于表达 Actor/Module 之间的消息次序，**不承担逐周期电平表达**
（后者交给 WaveDrom）。输出优先为可编辑 Draw.io 序列图，并可附 Mermaid 版本用于文档内嵌。

## 典型场景

- CPU → DMA → Interconnect → Memory；
- Interrupt Source → PIC → Safety Island/CLIC；
- Power Manager → CRG → Subsystem Reset；
- Bus Error → Monitor → Fault Manager → System Response；
- UVM Sequence → Driver → DUT → Monitor → Scoreboard。

## 输入模型

```yaml
behavior:
  participants:
    - {id: cpu, label: CPU}
    - {id: dma, label: DMA}
    - {id: mem, label: Memory}
  messages:
    - {from: cpu, to: dma, label: "cfg write"}
    - {from: dma, to: mem, label: "read req"}
    - {from: mem, to: dma, label: "read data", return: true}
    - {from: dma, to: cpu, label: "done irq", async: true}
```

## 消息类型

- 同步（solid, filled arrow）：默认；
- 异步（dashed, open arrow）：`async: true`；
- 返回（grey dashed）：`return: true`；
- 注释（note）：`{note: ..., over: participant}`。

## 校验规则

- 消息发送者/接收者必须存在于 participants；
- 注释归属（over）必须存在；
- 端点缺失 → ERROR。

## 禁止

- 不用 WaveDrom 代替事务序列图（两者定位不同，建设方案 §3.1 路由器禁止事项）。
