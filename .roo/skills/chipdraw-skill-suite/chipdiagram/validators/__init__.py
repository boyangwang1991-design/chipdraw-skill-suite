"""专业规则校验子包。

- common_validator   公共：Schema、端点、方向、对象 ID 唯一、Mandatory Port、追踪
- soc_validator      SoC：协议/位宽/地址窗口/跨域/中断/依赖
- ip_validator       IP：数据通路位宽、流水线、FIFO、CDC/RDC、安全机制
- behavior_validator 行为：FSM 可达性、时序一致性、事务序列
- circuit_validator  电路：器件/网络/引脚唯一、四端完整、ERC
"""
