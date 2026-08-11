"""单元测试：行为级校验器 Timing wave 书写约定检查。

覆盖运行中暴露的两类问题：
- 连续同电平字符（"11"/"00"）在 WaveDrom 中渲染出冗余跳变沿（glitch）；
- wave 以 `.` 开头（无前态可延续）被渲染为未知态。
"""
from chipdiagram.validators.behavior_validator import validate_behavior


def _timing_model(signals):
    return {
        "diagram": {"id": "t", "type": "rtl_behavior", "subtype": "timing"},
        "behavior": {
            "clock": {"name": "clk", "period": "10ns"},
            "signals": signals,
            "origin": "spec",
        },
    }


def _codes(model):
    return [i.code for i in validate_behavior(model)]


def test_glitch_consecutive_same_level_warns():
    """连续同电平（11/00）应报 TIMING_WAVE_GLITCH。"""
    model = _timing_model([{"name": "awvalid", "wave": "11....11......"}])
    assert "TIMING_WAVE_GLITCH" in _codes(model)


def test_leading_dot_warns():
    """wave 以 `.` 开头应报 TIMING_WAVE_LEADING_DOT。"""
    model = _timing_model([{"name": "wvalid", "wave": "..11..."}])
    assert "TIMING_WAVE_LEADING_DOT" in _codes(model)


def test_clean_wave_no_wave_style_warning():
    """正确写法（`1.` 延续、连续数字 data 拍）不应误报。"""
    model = _timing_model([
        {"name": "awvalid", "wave": "1.0....1.0...."},
        {"name": "wdata", "wave": "xx45xxx", "data": ["B0", "B1"]},
        {"name": "wlast", "wave": "0..10......10."},
    ])
    codes = _codes(model)
    assert "TIMING_WAVE_GLITCH" not in codes
    assert "TIMING_WAVE_LEADING_DOT" not in codes


def test_axi_example_clean():
    """自带 AXI 写示例应无 wave 写法告警。"""
    import os
    import yaml
    path = os.path.join(os.path.dirname(__file__), "..", "..",
                        "assets", "examples", "axi-write-timing", "axi_write_timing.yaml")
    with open(path, encoding="utf-8") as fh:
        model = yaml.safe_load(fh)
    codes = _codes(model)
    assert "TIMING_WAVE_GLITCH" not in codes
    assert "TIMING_WAVE_LEADING_DOT" not in codes
    assert "TIMING_HANDSHAKE_DATA_UNCOVERED" not in codes


def test_handshake_coverage_warns_when_uncovered():
    """地址比握手晚一拍就绪（off-by-one）应报 TIMING_HANDSHAKE_DATA_UNCOVERED。"""
    model = _timing_model([
        {"name": "awvalid", "wave": "1.0....1.0...."},
        {"name": "awready", "wave": "010.....10...."},
        # 握手周期为 1 与 8；A1 落在 cycle8-9，cycle8 握手沿上未就绪
        {"name": "awaddr", "wave": "2.x.....3x....", "data": ["A0", "A1"]},
    ])
    assert "TIMING_HANDSHAKE_DATA_UNCOVERED" in _codes(model)


def test_handshake_coverage_clean_when_covered():
    """地址覆盖握手周期（含 `.` 延续展开）不应误报。"""
    model = _timing_model([
        {"name": "awvalid", "wave": "1.0....1.0...."},
        {"name": "awready", "wave": "010.....10...."},
        {"name": "awaddr", "wave": "2.x....3.x....", "data": ["A0", "A1"]},
    ])
    assert "TIMING_HANDSHAKE_DATA_UNCOVERED" not in _codes(model)
