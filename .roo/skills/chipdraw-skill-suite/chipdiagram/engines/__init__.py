"""渲染引擎子包。

- shared/   封装上游 drawio-skill 的通用脚本（只读快照）
- drawio/   Draw.io XML 生成器（芯片语义 → 可编辑 .drawio）
- graphviz/ Graphviz 布局与 FSM/DOT 渲染
- wavedrom/ WaveDrom 数字时序（YAML → WaveJSON → SVG/PNG）
- xschem/   Xschem 工程原理图后端（.sch / SPICE / ERC）
"""
