# 路由决策细节

本文件在需要详细路由决策或边界情况时读取（建设方案 §3.1 路由规则补充）。

## 输入类型识别

| 输入特征 | 判定来源 | 归一化结果 | 备注 |
|---|---|---|---|
| 自然语言/Markdown（`.md/.txt`） | 无结构化语法 | `inferred` YAML | 关键连接需确认 |
| YAML（含 `diagram.type`） | `diagram:` 节点 | 按 type 归一化 | 推荐权威来源 |
| FuseSoC `.core` | `CAPI2` / `name:` | 依赖/工程视图 | 不推断 RTL 端口互联 |
| SystemVerilog `.sv/.v` | `module` / `enum` | IP/行为模型 | generate/interface 分阶段支持 |
| SystemRDL `.rdl` | `reg` / `field` | IP 寄存器视图 | 复用 PeakRDL |
| IP-XACT `.xml` | `busInterface`/`memoryMap` | SoC/IP 模型 | 交换格式 |
| WaveJSON `.json` | `signal` / `wave` | Behavior Timing | 保留原始周期表达 |
| SPICE/CDL `.sp/.cdl` | `.subckt` / `M/R/C/X` | Circuit 模型 | Engineering 权威输入 |
| `.drawio` | `<mxfile` | Graph 模型 | 不自动视为 SSOT |

## 优先级（建设方案 §5 输入优先级）

```
项目指定 SSOT
  > 已评审的结构化设计文件
  > RTL / SPICE 等实现事实
  > 已评审规格
  > 未评审文档
  > 现有图形
  > 自然语言和图片推断
```

项目可在 `diagram-policy.yaml` 中覆盖该顺序。

## 组合请求

- **SoC 框图 + 中断时序**：先 SoC，再 RTL behavior 生成关联子图。
- **IP 框图 + 接口展开**：先 IP overview，再 interface_expanded 子图。
- **SoC 上下文 + PIC 内部**：router 建立 `diagram-set.yaml`，一个 SSOT 多视图。

## 边界情况

- **无法判断 illustration/engineering** → 询问用户。
- **未知端口/网络** → 不臆造，输出 `TBD`，阻断或带告警。
- **需求冲突** → 遵循输入优先级，冲突记录进 Manifest assumptions。

## 视图目录（供路由参考）

- SoC：`soc_overview`、`bus_interconnect`、`address_map`、`clock_reset`、`power_domain`、`interrupt_network`、`safety_security`、`fusesoc_dependency`、`chiplet_topology`
- IP：`ip_overview`、`datapath`、`pipeline`、`buffer_fifo`、`interface_expanded`、`register_interface`、`cdc_rdc`、`safety_mechanism`、`rtl_hierarchy`、`bitwidth_conversion`
- Behavior：`fsm`、`timing`、`sequence`
- Transistor：`schematic_illustration`、`schematic_engineering`
