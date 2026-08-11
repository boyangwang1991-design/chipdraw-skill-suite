# SoC 符号库

SoC 系统级绘图使用的块类型与默认样式。实际颜色由主题 roles 解析
（见 `../themes/aixsilicon-*.yaml`），此处只维护形状关键字。

| 块类型 | draw.io style |
|---|---|
| CPU / DSP / NPU | `rounded=1`（primary 蓝） |
| Memory / SRAM / DRAM | `shape=cylinder3`（success 绿） |
| Peripheral | `rounded=1`（accent 橙） |
| Subsystem | `swimlane;startSize=30`（secondary 紫） |
| Interconnect / NoC | `rounded=1`（warning 黄） |
| Bridge / Controller | `rounded=1`（warning 黄） |
| PHY / 外部接口 | `rounded=1;dashed=1`（neutral 灰） |
| Power/Safety/Security Domain | `rounded=0;dashed=1` 淡色容器 |

## 符号检索

需要具体 draw.io 官方图标（如 CPU/网络符号）时，运行共享脚本：

```bash
uv run python chipdiagram/engines/shared/shapesearch.py "cpu"
```
