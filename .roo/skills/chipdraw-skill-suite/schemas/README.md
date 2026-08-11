# Schema 目录

芯片图形语义模型的 JSON Schema 集合（建设方案 §4）。

| 文件 | 用途 |
| --- | --- |
| [`common.schema.json`](common.schema.json) | 公共 Envelope：`diagram` / `provenance` / `style` / `layout` / `outputs` / `traceability`，并按 `diagram.type` 仅允许一个专用节点 |
| [`view.schema.json`](view.schema.json) | View Filter：一份 SSOT 生成多张图的选择/显示策略，不复制事实 |
| [`soc.schema.json`](soc.schema.json) | L1 SoC：实例、接口、连接、地址空间、时钟/复位/电源/安全/保密域、中断、层级 |
| [`ip.schema.json`](ip.schema.json) | L2 IP：模块、端口、接口、数据通路、控制通路、流水线、FIFO、仲裁、寄存器接口、CDC/RDC、安全机制、RTL 绑定 |
| [`fsm.schema.json`](fsm.schema.json) | L3 行为：FSM / Timing / Sequence 三小类（oneOf），由 subtype 区分 |
| [`timing.schema.json`](timing.schema.json) | 薄包装，引用 `fsm.schema.json#/definitions/timing` |
| [`sequence.schema.json`](sequence.schema.json) | 薄包装，引用 `fsm.schema.json#/definitions/sequence` |
| [`circuit.schema.json`](circuit.schema.json) | L4 晶体管：mode（illustration/engineering）、端口、器件、网络、子电路、PDK |

## 设计原则（建设方案 §4.1 / §16）

- 公共 Envelope + 四类专用 Schema，禁止形成单个超级 Schema（避免字段膨胀与校验困难）。
- 对象级 `trace`（`source_refs` / `confidence` / `owner` / `review_status`）支持逐对象追踪。
- `confidence` 取值：`confirmed` / `extracted` / `inferred` / `tbd`，渲染时对低置信度做区分显示。
- Schema 使用 `major.minor` 版本；Major 变更需迁移脚本，Minor 只允许向后兼容地增加字段（建设方案 §15）。

## 校验

`chipdiagram.validators.common_validator` 负责 Schema 校验（Gate 1），使用 `jsonschema` 库按 `diagram.type` 加载对应 Schema 并校验整个 Envelope。
