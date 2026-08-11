"""单元测试：WaveDrom 时序引擎高级能力（对齐 WaveDrom Tutorial）。

覆盖：
- 自动时钟 lane 生成（p/P/n/N + 周期数）
- 分组（内联嵌套数组 + 顶层 groups 声明）
- 每信号 period/phase
- head/foot/config/marker/edge 映射
- data 匹配规则（x2...x 不误报）
- 时钟 wave 语法校验
"""
from chipdiagram.engines.wavedrom.timing import (
    _gen_clock_wave,
    _to_wavejson,
)
from chipdiagram.model import normalize_model
from chipdiagram.validators.common_validator import validate_schema_and_common
from chipdiagram.validators.behavior_validator import validate_behavior


def _behavior_model(behavior):
    return normalize_model({
        "schema_version": "1.0",
        "diagram": {"id": "t", "type": "rtl_behavior", "subtype": "timing", "title": "T"},
        "provenance": {"generator": "chip-design-diagram-suite"},
        "behavior": behavior,
    })


# ---- 时钟生成 ----

def test_gen_clock_wave_positive():
    # WaveDrom 时钟字符每个代表一个完整方波周期；. 延续
    assert _gen_clock_wave(8, "positive", True) == "P......."
    assert _gen_clock_wave(8, "positive", False) == "p......."
    assert _gen_clock_wave(8, "negative", True) == "N......."
    assert _gen_clock_wave(3, "positive", True) == "P.."


def test_clock_auto_lane():
    behavior = {
        "clock": {"name": "aclk", "period": "10ns"},
        "signals": [{"name": "s", "wave": "01..0"}],
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    # 时钟 lane 自动生成，周期数 = 5
    assert out["signal"][0] == {"name": "aclk", "wave": "P...."}
    assert out["head"]["tick"] == "10ns"


def test_clock_explicit_wave_and_display_false():
    behavior = {
        "clock": {"name": "clk", "wave": "p..p..", "display": False},
        "signals": [{"name": "s", "wave": "01.0.."}],
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    names = [s.get("name") for s in out["signal"] if isinstance(s, dict)]
    assert "clk" not in names  # display=False 不进图


# ---- 分组 ----

def test_group_nested_array():
    behavior = {
        "clock": {"name": "clk", "period": "10ns"},
        "signals": [
            ["Master",
                ["ctrl",
                    {"name": "write", "wave": "01.0...."},
                    {"name": "read", "wave": "0...1..0"}],
                {"name": "addr", "wave": "x3.x4..x", "data": "A1 A2"}],
            {},
            ["Slave", {"name": "ack", "wave": "x01x0.1x"}],
        ],
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    sig = out["signal"]
    # 时钟 + 嵌套组 + spacer + 组
    assert sig[0]["name"] == "clk"
    assert sig[1][0] == "Master"
    assert sig[1][1][0] == "ctrl"       # 嵌套子组
    assert sig[2] == {}                  # spacer
    assert sig[3][0] == "Slave"
    # 校验通过
    m = _behavior_model(behavior)
    errs = [i for i in validate_schema_and_common(m) if i.severity == "ERROR"]
    assert errs == []


def test_group_top_level_decl():
    behavior = {
        "clock": {"name": "clk"},
        "groups": [{"name": "Master", "signals": ["write", "read"]}],
        "signals": [
            {"name": "write", "wave": "01.0...."},
            {"name": "read", "wave": "0...1..0"},
            {"name": "free", "wave": "0..1..0"},
        ],
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    sig = out["signal"]
    # 时钟 + ['Master', write, read] + free
    assert sig[0]["name"] == "clk"
    assert sig[1][0] == "Master"
    assert sig[1][1]["name"] == "write"
    assert sig[1][2]["name"] == "read"
    assert sig[2]["name"] == "free"


# ---- period/phase ----

def test_signal_period_phase():
    """每信号 period/phase 透传到 lane；clock.period 进 head.tick 标尺。"""
    behavior = {
        "clock": {"name": "CK", "wave": "P.......", "period": "10ns"},
        "signals": [
            {"name": "CMD", "wave": "x.3x=x4x=x=x=x=x",
             "data": "RAS NOP CAS NOP NOP NOP NOP", "phase": 0.5},
            {"name": "DQ", "wave": "z.........5555z.",
             "data": "D0 D1 D2 D3", "period": 2},
        ],
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    lane_cmd = out["signal"][1]
    assert lane_cmd["phase"] == 0.5
    # 信号级 period 透传
    lane_dq = out["signal"][2]
    assert lane_dq["period"] == 2
    # clock.period 作为时间标尺（head.tick），不是 lane 属性
    assert out["head"]["tick"] == "10ns"
    assert "period" not in out["signal"][0]


# ---- head/foot/config/marker/edge ----

def test_head_foot_config_marker_edge():
    behavior = {
        "clock": {"name": "clk", "period": "10ns"},
        "signals": [
            {"name": "A", "wave": "01........0....", "node": ".a........j"},
            {"name": "B", "wave": "0.1.......0.1..", "node": "..b.......i"},
        ],
        "markers": [{"cycle": 2, "text": "握手"}],
        "edges": ["a~b t1", "c->d 建立时间"],
        "config": {"hscale": 2, "skin": "narrow"},
        "head": {"text": "标题", "tick": 0},
        "foot": {"text": "图注", "tock": 9},
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    assert out["marker"] == [{"cycle": 2, "text": "握手"}]
    assert out["edge"] == ["a~b t1", "c->d 建立时间"]
    assert out["config"] == {"hscale": 2, "skin": "narrow"}
    assert out["head"]["text"] == "标题"
    assert out["head"]["tick"] == 0
    assert out["foot"]["text"] == "图注"
    assert out["signal"][1]["node"] == ".a........j"


# ---- data 匹配与 node 长度 ----

def test_data_ref_count_not_false_positive():
    """x2.....x 的 data 引用字符只有数字 2，1 个 data 合法（不误报）。"""
    behavior = {
        "clock": {"name": "clk"},
        "signals": [
            {"name": "awaddr", "wave": "x2.....x", "data": ["ADDR"]},
            {"name": "wdata", "wave": "xxx45xxx", "data": ["BEAT0", "BEAT1"]},
        ],
        "origin": "spec",
    }
    m = _behavior_model(behavior)
    errs = [i for i in validate_behavior(m) if i.severity == "ERROR"]
    assert all(i.code != "TIMING_WAVE_DATA_MISMATCH" for i in errs)


def test_data_count_mismatch_error():
    """data 数量与引用字符数不一致应报错。"""
    behavior = {
        "clock": {"name": "clk"},
        "signals": [{"name": "s", "wave": "x3.45x", "data": ["A", "B"]}],  # 3 引用 vs 2 data
        "origin": "spec",
    }
    m = _behavior_model(behavior)
    codes = [i.code for i in validate_behavior(m)]
    assert "TIMING_WAVE_DATA_MISMATCH" in codes


def test_clock_wave_invalid_chars():
    behavior = {
        "clock": {"name": "clk", "wave": "P...X..."},
        "signals": [{"name": "s", "wave": "01..0"}],
        "origin": "spec",
    }
    m = _behavior_model(behavior)
    codes = [i.code for i in validate_behavior(m)]
    assert "TIMING_CLOCK_WAVE_INVALID" in codes


def test_node_length_mismatch():
    behavior = {
        "clock": {"name": "clk"},
        "signals": [{"name": "A", "wave": "01..0", "node": ".a"}],
        "origin": "spec",
    }
    m = _behavior_model(behavior)
    codes = [i.code for i in validate_behavior(m)]
    assert "TIMING_NODE_LEN_MISMATCH" in codes


# ---- gaps / over / under / pw path / data 字符串 ----

def test_gaps_passthrough():
    """顶层 gaps 表达式透传到 WaveJSON。"""
    behavior = {
        "clock": {"name": "clk", "wave": "p....."},
        "signals": [
            {"name": "valid", "wave": "0101.0"},
            {"name": "data", "wave": "x3x4.x", "data": "d0 d1"},
            {},
            {"name": "ready", "wave": "x1x01x"},
        ],
        "gaps": "(. |.. )",
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    assert out["gaps"] == "(. |.. )"


def test_over_under_passthrough():
    """lane 级 over/under（建立/保持窗口）透传。"""
    behavior = {
        "clock": {"name": "clk", "wave": "p.PpPpPP"},
        "signals": [
            {"name": "dat ->", "wave": "x.3.....", "data": "D",
             "over": "0...1..0", "under": "0.....1."},
            {},
            {"name": "FF", "wave": "x......3", "data": "D"},
        ],
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    lane = out["signal"][1]
    assert lane["over"] == "0...1..0"
    assert lane["under"] == "0.....1."


def test_pw_path_wave():
    """path 波形（['pw',{d:...}]）透传且不触发 data/node 校验。"""
    behavior = {
        "clock": {"name": "clk", "wave": "p......."},
        "signals": [
            {"name": "sawtooth", "wave": ["pw", {"d": ["m", 1, 0, "l", 2, 1, "v", -1]}]},
            {"name": "sin", "wave": ["pw", {"d": "m,0,.5 q,.25,1,.5,0 t,.5,0,.5,0"}]},
        ],
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    # 时钟 lane 不因 pw 波形崩溃
    assert out["signal"][0]["name"] == "clk"
    assert out["signal"][1]["wave"][0] == "pw"
    assert out["signal"][2]["wave"][1]["d"].startswith("m,0,.5")
    # 校验不报错（pw 跳过 data/node 检查）
    m = _behavior_model(behavior)
    errs = [i for i in validate_behavior(m) if i.severity == "ERROR"]
    assert errs == []


def test_data_string_split():
    """data 为空格分隔字符串时按 token 计数校验。"""
    behavior = {
        "clock": {"name": "clk"},
        "signals": [{"name": "data", "wave": "x3x4.x", "data": "d0 d1"}],
        "origin": "spec",
    }
    m = _behavior_model(behavior)
    errs = [i for i in validate_behavior(m) if i.severity == "ERROR"]
    assert all(i.code != "TIMING_WAVE_DATA_MISMATCH" for i in errs)


def test_config_arc_font_size():
    """config 额外键（arcFontSize 等）透传。"""
    behavior = {
        "clock": {"name": "clk"},
        "signals": [
            {"name": "enable", "wave": "0...1...0...", "node": "....a...b"},
            {"node": "....A...B"},
        ],
        "edges": ["a-A", "A<->B 100 ms delay", "B-b"],
        "config": {"arcFontSize": 18},
        "origin": "spec",
    }
    out = _to_wavejson(behavior)
    assert out["config"] == {"arcFontSize": 18}
    assert out["edge"] == ["a-A", "A<->B 100 ms delay", "B-b"]
