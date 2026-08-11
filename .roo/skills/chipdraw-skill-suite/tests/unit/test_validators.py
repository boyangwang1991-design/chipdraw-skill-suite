"""单元测试：专业规则校验器（建设方案 §11.3 错误注入检出）。"""
from chipdiagram.model import normalize_model
from chipdiagram.validators.soc_validator import validate_soc
from chipdiagram.validators.ip_validator import validate_ip
from chipdiagram.validators.behavior_validator import validate_behavior
from chipdiagram.validators.circuit_validator import validate_circuit
from chipdiagram.issues import count_by_severity


def _wrap(node_type, node):
    return normalize_model({
        "schema_version": "1.0",
        "diagram": {"id": "t", "type": node_type, "title": "T"},
        "provenance": {"generator": "chip-design-diagram-suite"},
        **node,
    })


def test_soc_addr_overlap():
    m = _wrap("soc_architecture", {"soc": {
        "instances": [{"id": "a", "name": "A", "kind": "other"}],
        "address_spaces": [
            {"id": "s1", "name": "S1", "base": "0x1000", "size": "0x200"},
            {"id": "s2", "name": "S2", "base": "0x1100", "size": "0x200"},
        ],
    }})
    issues = validate_soc(m, "default")
    codes = [i.code for i in issues]
    assert "SOC_ADDR_OVERLAP" in codes


def test_soc_cdc_unhandled():
    m = _wrap("soc_architecture", {"soc": {
        "instances": [
            {"id": "a", "name": "A", "kind": "other", "clock_domain": "clk1"},
            {"id": "b", "name": "B", "kind": "other", "clock_domain": "clk2"},
        ],
        "connections": [{"id": "c1", "from": "a", "to": "b", "kind": "bus"}],
    }})
    issues = validate_soc(m, "default")
    assert any(i.code == "SOC_CDC_UNHANDLED" for i in issues)


def test_soc_irq_duplicate():
    m = _wrap("soc_architecture", {"soc": {
        "instances": [{"id": "a", "name": "A", "kind": "other"}],
        "interrupts": [
            {"id": "i1", "name": "I1", "source": "a", "target": "a", "number": 5},
            {"id": "i2", "name": "I2", "source": "a", "target": "a", "number": 5},
        ],
    }})
    issues = validate_soc(m, "default")
    assert any(i.code == "SOC_IRQ_NUMBER_DUPLICATE" for i in issues)


def test_ip_width_conversion_missing():
    m = _wrap("ip_architecture", {"ip": {
        "modules": [{"id": "c", "name": "C", "kind": "converter"}],
        "ports": [
            {"id": "p1", "name": "p1", "direction": "input", "width": 32},
            {"id": "p2", "name": "p2", "direction": "output", "width": 64},
        ],
        "datapaths": [{"id": "dp", "from": "p1", "to": "p2", "width": 32}],
    }})
    issues = validate_ip(m, "default")
    assert any(i.code == "IP_WIDTH_CONVERSION_MISSING" for i in issues)


def test_fsm_unreachable():
    m = _wrap("rtl_behavior", {"behavior": {
        "initial_state": "idle",
        "states": [
            {"id": "idle", "category": "normal"},
            {"id": "lost", "category": "normal"},
        ],
        "transitions": [],
    }})
    issues = validate_behavior(m, "default")
    assert any(i.code == "FSM_STATE_UNREACHABLE" for i in issues)


def test_timing_wave_data_mismatch():
    m = _wrap("rtl_behavior", {"behavior": {
        "clock": {"name": "clk"},
        "signals": [{"name": "s", "wave": "0.1...0", "data": ["A", "B"]}],
    }})
    # 强制 subtype=timing 以进入时序校验分支
    m["diagram"]["subtype"] = "timing"
    # 非 '.' 周期: 0,1,0 -> 3 个, data 2 个 -> 应报错
    issues = validate_behavior(m, "default")
    assert any(i.code == "TIMING_WAVE_DATA_MISMATCH" for i in issues)


def test_circuit_erc_gate_dangling():
    m = _wrap("transistor_schematic", {"circuit": {
        "mode": "engineering",
        "devices": [{"id": "m0", "type": "nmos", "terminals": {"g": "floating_gate", "d": "y", "s": "vss", "b": "vss"}}],
        "nets": [{"id": "n_y", "name": "y"}],
    }})
    issues = validate_circuit(m, "engineering")
    assert any(i.code == "CIRCUIT_GATE_DANGLING" for i in issues)


def test_circuit_erc_mos_terminals():
    m = _wrap("transistor_schematic", {"circuit": {
        "mode": "engineering",
        "devices": [{"id": "m0", "type": "pmos", "terminals": {"d": "y", "s": "vdd"}}],
        "nets": [],
    }})
    issues = validate_circuit(m, "engineering")
    assert any(i.code == "CIRCUIT_MOS_TERMINALS" for i in issues)
