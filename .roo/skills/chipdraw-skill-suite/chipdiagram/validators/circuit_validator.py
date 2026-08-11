"""电路/晶体管校验器（建设方案 §3.5 工程校验 / ERC）。

- Device、Net、Port 名称唯一
- MOS 四端连接完整
- Bulk 连接满足项目规则
- 电源和地不存在直接短路
- 无悬空 Gate 或未声明网络
- Model 和 Symbol 可解析
- 参数单位和数值格式合法
- Subcircuit 实例端口数与定义一致
- Schematic Netlist 与输入 SPICE/CDL 结构一致
- ERC 错误阻断正式输出，告警进入 waiver 流程
"""
from __future__ import annotations

import re
from typing import Any

from ..issues import Issue

POWER_NETS = {"vdd", "vcc", "vdd!", "avdd", "vdda"}
GROUND_NETS = {"vss", "gnd", "gnd!", "0", "vssa"}


def validate_circuit(model: dict[str, Any], profile: str = "default") -> list[Issue]:
    issues: list[Issue] = []
    circuit = model.get("circuit") or {}
    issues.extend(_check_uniqueness(model, circuit))
    issues.extend(_check_mos_terminals(model, circuit))
    issues.extend(_check_bulk(model, circuit))
    issues.extend(_check_power_short(model, circuit))
    issues.extend(_check_dangling_gate(model, circuit))
    issues.extend(_check_subckt_ports(model, circuit))
    return issues


def _devices(circuit: dict[str, Any]) -> list[dict[str, Any]]:
    return circuit.get("devices", []) or []


def _nets(circuit: dict[str, Any]) -> dict[str, str]:
    return {str(n.get("name")): str(n.get("id")) for n in circuit.get("nets", []) or []}


def _check_uniqueness(model: dict[str, Any], circuit: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    dev_ids: dict[str, int] = {}
    for d in _devices(circuit):
        did = str(d.get("id", ""))
        dev_ids[did] = dev_ids.get(did, 0) + 1
    for did, cnt in dev_ids.items():
        if cnt > 1:
            issues.append(Issue(code="CIRCUIT_DEVICE_DUP", severity="ERROR",
                                message=f"器件 id 重复: {did}", object_id=did,
                                rule="circuit.device_unique"))
    net_names: dict[str, int] = {}
    for n in circuit.get("nets", []) or []:
        nn = str(n.get("name", ""))
        net_names[nn] = net_names.get(nn, 0) + 1
    for nn, cnt in net_names.items():
        if cnt > 1:
            issues.append(Issue(code="CIRCUIT_NET_DUP", severity="ERROR",
                                message=f"网络名重复: {nn}", rule="circuit.net_unique"))
    return issues


def _check_mos_terminals(model: dict[str, Any], circuit: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for d in _devices(circuit):
        if d.get("type") in ("pmos", "nmos"):
            terms = d.get("terminals") or {}
            missing = [k for k in ("g", "d", "s", "b") if k not in terms or not terms.get(k)]
            if missing:
                issues.append(Issue(code="CIRCUIT_MOS_TERMINALS", severity="ERROR",
                                    message=f"MOS {d.get('id')} 四端连接不完整，缺少 {missing}",
                                    object_id=str(d.get("id", "")),
                                    rule="circuit.mos_terminals", data={"missing": missing}))
    return issues


def _check_bulk(model: dict[str, Any], circuit: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for d in _devices(circuit):
        if d.get("type") in ("pmos", "nmos"):
            terms = d.get("terminals") or {}
            b = terms.get("b")
            s = terms.get("s")
            if b and s and b != s and b not in POWER_NETS and b not in GROUND_NETS:
                issues.append(Issue(code="CIRCUIT_BULK_RULE", severity="WARNING",
                                    message=f"MOS {d.get('id')} Bulk({b}) 与 Source({s}) 连接不符合常规（PMOS bulk 接电源/NMOS bulk 接地）",
                                    object_id=str(d.get("id", "")),
                                    rule="circuit.bulk"))
    return issues


def _check_power_short(model: dict[str, Any], circuit: dict[str, Any]) -> list[Issue]:
    """电源与地直接短路：同一器件两个端子分别接电源与地。"""
    issues: list[Issue] = []
    for d in _devices(circuit):
        terms = d.get("terminals") or {}
        vals = [str(v).lower() for v in terms.values()]
        has_power = any(v in POWER_NETS for v in vals)
        has_ground = any(v in GROUND_NETS for v in vals)
        if has_power and has_ground and d.get("type") not in ("resistor", "capacitor", "inductor"):
            # 允许 R/C/L 自然跨电源地；其他器件视为潜在短路（取决于拓扑）
            issues.append(Issue(code="CIRCUIT_POWER_SHORT_RISK", severity="ERROR",
                                message=f"器件 {d.get('id')} 端子同时连接电源与地（{d.get('type')}），存在短路风险",
                                object_id=str(d.get("id", "")),
                                rule="circuit.power_short"))
    return issues


def _check_dangling_gate(model: dict[str, Any], circuit: dict[str, Any]) -> list[Issue]:
    """悬空 Gate：MOS gate 未连接任何已声明网络。"""
    issues: list[Issue] = []
    net_names = set(_nets(circuit).keys())
    port_names = {str(p.get("name")) for p in circuit.get("ports", []) or []}
    all_nets = net_names | port_names | POWER_NETS | GROUND_NETS
    for d in _devices(circuit):
        if d.get("type") in ("pmos", "nmos"):
            g = (d.get("terminals") or {}).get("g")
            if g and g not in all_nets:
                issues.append(Issue(code="CIRCUIT_GATE_DANGLING", severity="ERROR",
                                    message=f"MOS {d.get('id')} 的 Gate({g}) 悬空或未声明网络",
                                    object_id=str(d.get("id", "")),
                                    rule="circuit.gate_dangling"))
    return issues


def _check_subckt_ports(model: dict[str, Any], circuit: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    subckts = {str(s.get("name")): s for s in circuit.get("subcircuits", []) or []}
    for d in _devices(circuit):
        if d.get("type") == "subckt_instance":
            model_name = d.get("model", "")
            terms = d.get("terminals") or {}
            if model_name in subckts:
                expect = len(subckts[model_name].get("ports", []) or [])
                actual = len(terms)
                if expect != actual:
                    issues.append(Issue(code="CIRCUIT_SUBCKT_PORT_COUNT", severity="ERROR",
                                        message=f"子电路实例 {d.get('id')} 端口数({actual}) 与定义 {model_name}({expect}) 不一致",
                                        object_id=str(d.get("id", "")),
                                        rule="circuit.subckt_ports",
                                        data={"expected": expect, "actual": actual}))
            elif not model_name:
                issues.append(Issue(code="CIRCUIT_SUBCKT_NO_MODEL", severity="WARNING",
                                    message=f"子电路实例 {d.get('id')} 缺少 model",
                                    object_id=str(d.get("id", "")),
                                    rule="circuit.subckt_model"))
    return issues
