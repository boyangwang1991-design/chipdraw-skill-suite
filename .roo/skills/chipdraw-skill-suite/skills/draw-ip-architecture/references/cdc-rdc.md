# CDC/RDC 结构（建设方案 §3.3）

## CDC 机制

| mechanism | 适用 |
|---|---|
| `2ff_sync` | 单 bit 电平信号 |
| `handshake` | 请求/应答式控制信号 |
| `async_fifo` | 多 bit 数据流跨时钟 |
| `pulse_sync` | 脉冲信号跨域（需保证不丢脉冲） |
| `gray_code` | 计数器（如 FIFO 指针） |

```yaml
cdc_paths:
  - id: cdc0
    from_domain: clk_a
    to_domain: clk_b
    mechanism: async_fifo
```

- mechanism 为 `none`/`tbd`/空 且无 waiver → **ERROR**；
- 脉冲跨域必须有 Pulse Synchronizer 或协议保证。

## RDC（复位域）

```yaml
rdc_paths:
  - id: rdc0
    from_domain: rst_a
    to_domain: rst_b
    mechanism: reset_sync
```

- 跨复位域无 Reset Deassert 同步且无 waiver → **ERROR**。

## 渲染约定

- CDC/RDC Block 使用黄色底色（`fillColor=#fff2cc`）；
- 异步 FIFO 标注读写时钟域；
- 每条 CDC/RDC 路径在边标签标注 mechanism。
