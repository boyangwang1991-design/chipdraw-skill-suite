# 跨域规则（建设方案 §3.2）

## 时钟域（CDC）

- 跨时钟域连接必须显式经过 Synchronizer/Handshake/Async FIFO（连接 `through` 字段）或声明 `cdc_handled`；
- 未处理且无 waiver → **ERROR**。

## 复位域（RDC）

- 跨复位域连接必须有 Reset Deassert 同步（`rdc_handled`）或 Reset Sync 对象；
- 未处理 → **ERROR**。

## 电源域

- 跨电源域连接需要 Isolation / Retention / Level Shifter（`through` 字段）；
- 缺失 → WARNING（是否阻断由项目 profile 决定）。

## 安全/保密域

- 跨 Safety Domain 连接需经允许的 Bridge/Firewall；
- 跨 Security Domain 连接需经 Bridge/Firewall；
- 缺失 → WARNING。

## 校验触发条件

校验器在两端实例的域字段存在且不同时触发。实例可声明：
`clock_domain` / `reset_domain` / `power_domain` / `safety_domain` / `security_domain`。

## 渲染

跨域对象建议使用淡色容器区分；CDC/RDC Block 用黄色底色；Safety Mechanism 用红色边框。
