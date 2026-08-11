# 流水线与数据通路建模（建设方案 §3.3）

## Pipeline

```yaml
pipelines:
  - id: pipe0
    name: main_pipeline
    stages:
      - {index: 0, name: fetch, latency: 1}
      - {index: 1, name: decode, latency: 1}
      - {index: 2, name: execute, latency: 3}
    valid_ready: true
```

- Stage 编号必须唯一且连续（重复 → ERROR）；
- latency 表示该级周期数；
- valid_ready 表示流水级间握手。

## 数据通路与位宽转换

```yaml
datapaths:
  - id: dp0
    from: aw_fifo
    to: width_converter
    width: 1024
  - id: dp1
    from: width_converter
    to: write_channel
    width: 32
```

- 通路两端端口位宽不同时，必须经明确 `through_converter`（Converter 块）；
- 缺失 Converter → **ERROR**（`IP_WIDTH_CONVERSION_MISSING`）；
- 例：32→1024 bit 参数化位宽转换应建模为 `width_converter` 块。

## 多源驱动

- 多个通路写同一目标时，目标必须是 Arbiter/MUX 输出；
- 否则 → WARNING（`IP_MULTI_DRIVER_NO_ARBITER`）。

## 渲染

- Pipeline 用等宽泳道（Stage 列）或顶部 Stage 标记；
- 边标签标注位宽、协议、Latency。
