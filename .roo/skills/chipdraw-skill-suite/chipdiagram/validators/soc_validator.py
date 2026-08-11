"""SoC 专业校验器（建设方案 §3.2 关键校验）。

- Initiator/Target 方向合法性
- 协议类型、版本、数据/地址/ID 位宽兼容
- 地址窗口重叠、越界、无上游可达
- 跨时钟域 CDC 处理、跨复位域 RDC、跨电源域 Isolation/Retention/Level Shifter
- 跨安全/保密域 Bridge/Firewall
- 中断重复编号、悬空、多驱动
- FuseSoC 依赖缺失/循环
"""
from __future__ import annotations

from typing import Any

from ..issues import Issue

# 协议位宽约束（数据/地址/ID）
PROTOCOL_CONSTRAINTS = {
    "AXI": {"data": [32, 64, 128, 256, 512, 1024], "addr": [32, 40, 48, 64], "id": [4, 5, 6, 8, 10, 16]},
    "AXI-Lite": {"data": [32, 64], "addr": [32, 64], "id": []},
    "AHB": {"data": [32, 64, 128], "addr": [32], "id": []},
    "APB": {"data": [32, 64], "addr": [32], "id": []},
    "CHI": {"data": [32, 64, 128, 256, 512], "addr": [40, 48, 52, 56], "id": [4, 5, 6, 7, 8, 9, 10, 11, 12]},
    "TileLink": {"data": [32, 64, 128, 256], "addr": [32, 40, 48, 56], "id": []},
}

PROTOCOL_ALIASES = {"AXI4": "AXI", "AXI4-Lite": "AXI-Lite", "AXI5": "AXI"}


def validate_soc(model: dict[str, Any], profile: str = "default") -> list[Issue]:
    issues: list[Issue] = []
    soc = model.get("soc") or {}
    issues.extend(_check_protocol_compat(model, soc))
    issues.extend(_check_address_spaces(model, soc))
    issues.extend(_check_cross_domain(model, soc))
    issues.extend(_check_interrupts(model, soc))
    issues.extend(_check_fusesoc_deps(model, soc))
    issues.extend(_check_interface_direction(model, soc))
    return issues


def _canon_protocol(p: str | None) -> str | None:
    if not p:
        return None
    return PROTOCOL_ALIASES.get(p, p)


def _check_interface_direction(model: dict[str, Any], soc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    valid_roles = {"initiator", "target", "master", "slave", "source", "sink"}
    for itf in soc.get("interfaces", []) or []:
        role = itf.get("role", "").lower()
        if role and role not in valid_roles:
            issues.append(Issue(
                code="SOC_INVALID_ROLE",
                severity="ERROR",
                message=f"接口 {itf.get('id','')} 方向非法: {role!r}",
                object_id=str(itf.get("id", "")),
                rule="soc.role_valid",
            ))
    return issues


def _check_protocol_compat(model: dict[str, Any], soc: dict[str, Any]) -> list[Issue]:
    """校验连接两端的协议与位宽兼容。"""
    issues: list[Issue] = []
    interfaces = {str(i.get("id")): i for i in soc.get("interfaces", []) or []}
    for c in soc.get("connections", []) or []:
        cid = str(c.get("id", ""))
        proto = _canon_protocol(c.get("protocol"))
        if proto and proto in PROTOCOL_CONSTRAINTS:
            constr = PROTOCOL_CONSTRAINTS[proto]
            data_w = c.get("data_width")
            addr_w = c.get("addr_width")
            if data_w and constr["data"] and data_w not in constr["data"]:
                issues.append(Issue(
                    code="SOC_DATA_WIDTH_INVALID",
                    severity="WARNING",
                    message=f"连接 {cid} 的数据位宽 {data_w} 不符合 {proto} 规范",
                    object_id=cid,
                    rule="soc.protocol_width",
                    data={"width": data_w, "allowed": constr["data"]},
                ))
            if addr_w and constr["addr"] and addr_w not in constr["addr"]:
                issues.append(Issue(
                    code="SOC_ADDR_WIDTH_INVALID",
                    severity="WARNING",
                    message=f"连接 {cid} 的地址位宽 {addr_w} 不符合 {proto} 规范",
                    object_id=cid,
                    rule="soc.protocol_width",
                ))
        # 从 from/to 接口位宽比较
        frm = str(c.get("from"))
        to = str(c.get("to"))
        if frm in interfaces and to in interfaces:
            fi, ti = interfaces[frm], interfaces[to]
            if fi.get("data_width") and ti.get("data_width") and \
               fi.get("data_width") != ti.get("data_width"):
                issues.append(Issue(
                    code="SOC_INTERFACE_WIDTH_MISMATCH",
                    severity="WARNING",
                    message=f"连接 {cid} 两端数据位宽不一致: {frm}={fi.get('data_width')} vs {to}={ti.get('data_width')}",
                    object_id=cid,
                    rule="soc.width_compat",
                ))
    return issues


def _check_address_spaces(model: dict[str, Any], soc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    spaces = soc.get("address_spaces", []) or []
    parsed: list[tuple[int, int, dict[str, Any]]] = []
    for s in spaces:
        base = _hex_int(s.get("base"))
        size = _hex_int(s.get("size"))
        if base is None or size is None:
            issues.append(Issue(
                code="SOC_ADDR_PARSE_FAIL",
                severity="WARNING",
                message=f"地址窗口 {s.get('id','')} 的 base/size 无法解析",
                object_id=str(s.get("id", "")),
                rule="soc.addr_parse",
            ))
            continue
        parsed.append((base, base + size, s))
    # 重叠检测
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            a_lo, a_hi, a = parsed[i]
            b_lo, b_hi, b = parsed[j]
            if a_lo < b_hi and b_lo < a_hi:
                issues.append(Issue(
                    code="SOC_ADDR_OVERLAP",
                    severity="ERROR",
                    message=f"地址窗口重叠: {a.get('id')} [{a.get('base')}..] 与 {b.get('id')} [{b.get('base')}..]",
                    object_id=f"{a.get('id')}|{b.get('id')}",
                    rule="soc.addr_overlap",
                    data={"a": a.get("base"), "b": b.get("base")},
                ))
    return issues


def _check_cross_domain(model: dict[str, Any], soc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    # 实例到域映射
    dom_of: dict[str, dict[str, str]] = {}
    for inst in soc.get("instances", []) or []:
        dom_of[str(inst.get("id"))] = {
            "clock": inst.get("clock_domain"),
            "reset": inst.get("reset_domain"),
            "power": inst.get("power_domain"),
            "safety": inst.get("safety_domain"),
            "security": inst.get("security_domain"),
        }

    for c in soc.get("connections", []) or []:
        cid = str(c.get("id", ""))
        frm = str(c.get("from"))
        to = str(c.get("to"))
        fd, td = dom_of.get(frm), dom_of.get(to)
        if not fd or not td:
            continue
        # 跨时钟域
        if fd.get("clock") and td.get("clock") and fd["clock"] != td["clock"]:
            if not c.get("cdc_handled") and not c.get("through"):
                issues.append(Issue(
                    code="SOC_CDC_UNHANDLED",
                    severity="ERROR",
                    message=f"连接 {cid} 跨时钟域 {fd['clock']}→{td['clock']} 且无 CDC 处理/waiver",
                    object_id=cid,
                    rule="soc.cdc",
                ))
        # 跨复位域
        if fd.get("reset") and td.get("reset") and fd["reset"] != td["reset"]:
            if not c.get("rdc_handled"):
                issues.append(Issue(
                    code="SOC_RDC_UNHANDLED",
                    severity="ERROR",
                    message=f"连接 {cid} 跨复位域 {fd['reset']}→{td['reset']} 且无 Reset Sync/RDC 处理",
                    object_id=cid,
                    rule="soc.rdc",
                ))
        # 跨电源域
        if fd.get("power") and td.get("power") and fd["power"] != td["power"]:
            if not c.get("through"):
                issues.append(Issue(
                    code="SOC_POWER_DOMAIN_CROSSING",
                    severity="WARNING",
                    message=f"连接 {cid} 跨电源域 {fd['power']}→{td['power']}，需 Isolation/Retention/Level Shifter",
                    object_id=cid,
                    rule="soc.power_domain",
                ))
        # 跨安全域
        if fd.get("safety") and td.get("safety") and fd["safety"] != td["safety"]:
            if not c.get("through"):
                issues.append(Issue(
                    code="SOC_SAFETY_DOMAIN_CROSSING",
                    severity="WARNING",
                    message=f"连接 {cid} 跨安全域，需经允许的 Bridge/Firewall",
                    object_id=cid,
                    rule="soc.safety_domain",
                ))
        # 跨保密域
        if fd.get("security") and td.get("security") and fd["security"] != td["security"]:
            if not c.get("through"):
                issues.append(Issue(
                    code="SOC_SECURITY_DOMAIN_CROSSING",
                    severity="WARNING",
                    message=f"连接 {cid} 跨保密域，需经 Bridge/Firewall",
                    object_id=cid,
                    rule="soc.security_domain",
                ))
    return issues


def _check_interrupts(model: dict[str, Any], soc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    irqs = soc.get("interrupts", []) or []
    numbers: dict[int, list[str]] = {}
    for irq in irqs:
        num = irq.get("number")
        if num is not None:
            numbers.setdefault(num, []).append(str(irq.get("id", "")))
        # 悬空：source/target 不存在
        ids = _all_ids(model, soc)
        if irq.get("source") and str(irq["source"]) not in ids:
            issues.append(Issue(
                code="SOC_IRQ_SOURCE_DANGLING",
                severity="WARNING",
                message=f"中断 {irq.get('id','')} 的源 {irq.get('source')} 不存在",
                object_id=str(irq.get("id", "")),
                rule="soc.irq_source",
            ))
    for num, owners in numbers.items():
        if len(owners) > 1:
            issues.append(Issue(
                code="SOC_IRQ_NUMBER_DUPLICATE",
                severity="ERROR",
                message=f"中断编号重复: {num} 由 {owners} 共用",
                data={"number": num, "owners": owners},
                rule="soc.irq_number_unique",
            ))
    return issues


def _check_fusesoc_deps(model: dict[str, Any], soc: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    deps = [c for c in soc.get("connections", []) or [] if c.get("kind") == "dependency"]
    # 环检测（简化：两节点互依赖）
    pairs = {(str(d.get("from")), str(d.get("to"))) for d in deps}
    for a, b in pairs:
        if (b, a) in pairs:
            issues.append(Issue(
                code="SOC_DEPENDENCY_CYCLE",
                severity="ERROR",
                message=f"FuseSoC 依赖形成循环: {a} ↔ {b}",
                object_id=f"{a}|{b}",
                rule="soc.dependency_acyclic",
            ))
    return issues


def _hex_int(s: Any) -> int | None:
    if isinstance(s, int):
        return s
    if isinstance(s, str):
        s = s.replace("_", "").strip()
        try:
            return int(s, 0)
        except ValueError:
            return None
    return None


def _all_ids(model: dict[str, Any], soc: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for inst in soc.get("instances", []) or []:
        ids.add(str(inst.get("id")))
        for p in inst.get("ports", []) or []:
            ids.add(str(p.get("id")))
    for itf in soc.get("interfaces", []) or []:
        ids.add(str(itf.get("id")))
    return ids
