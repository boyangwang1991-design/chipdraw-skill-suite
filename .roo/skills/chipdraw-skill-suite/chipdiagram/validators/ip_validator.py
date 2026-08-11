"""IP 微架构校验器（建设方案 §3.3 关键校验）。

- Module 与 RTL 实例绑定是否存在
- Port 名称、方向、位宽与 RTL 一致
- 数据通路位宽匹配；位宽转换需明确 Converter
- 流水级编号、Latency、Valid/Ready 关系
- FIFO 深度/数据宽度与接口一致
- 多源驱动是否经 MUX/Arbiter
- CDC 是否经 Synchronizer/Handshake/Async FIFO；脉冲跨域需 Pulse Sync
- Reset Deassert 是否同步
- 寄存器字段引用绑定 SystemRDL
- 安全机制检测对象/故障响应/上报路径完整
"""
from __future__ import annotations

from typing import Any

from ..issues import Issue


def validate_ip(model: dict[str, Any], profile: str = "default") -> list[Issue]:
    issues: list[Issue] = []
    ip = model.get("ip") or {}
    issues.extend(_check_datapath_widths(model, ip))
    issues.extend(_check_pipelines(model, ip))
    issues.extend(_check_fifo(model, ip))
    issues.extend(_check_cdc_rdc(model, ip))
    issues.extend(_check_safety(model, ip))
    issues.extend(_check_register_binding(model, ip))
    issues.extend(_check_rtl_binding(model, ip))
    issues.extend(_check_multi_driver(model, ip))
    return issues


def _collect_module_ids(ip: dict[str, Any]) -> set[str]:
    """收集 IP 模型中所有可引用对象 id（模块、端口、FIFO、仲裁器等）。"""
    ids: set[str] = set()
    for key in ("modules", "ports", "buffers", "arbiters", "interfaces",
                "register_interfaces", "safety_mechanisms", "pipelines"):
        for obj in ip.get(key, []) or []:
            if isinstance(obj, dict) and obj.get("id"):
                ids.add(str(obj["id"]))
    return ids


def _check_datapath_widths(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    """数据通路位宽匹配；位宽转换需明确 Converter。"""
    issues: list[Issue] = []
    ids = _collect_module_ids(ip)
    for path in list(ip.get("datapaths", []) or []) + list(ip.get("control_paths", []) or []):
        pid = str(path.get("id", ""))
        frm, to = str(path.get("from")), str(path.get("to"))
        if frm and frm not in ids:
            issues.append(Issue(
                code="IP_PATH_ENDPOINT_MISSING",
                severity="ERROR",
                message=f"通路 {pid} 的起点不存在: {frm!r}",
                object_id=pid,
                rule="ip.path_endpoint",
            ))
        if to and to not in ids:
            issues.append(Issue(
                code="IP_PATH_ENDPOINT_MISSING",
                severity="ERROR",
                message=f"通路 {pid} 的终点不存在: {to!r}",
                object_id=pid,
                rule="ip.path_endpoint",
            ))
    # 位宽转换：datapath 两端口宽度不同但无 Converter
    port_w = {str(p.get("id")): p.get("width") for p in ip.get("ports", []) or []}
    for path in ip.get("datapaths", []) or []:
        fw = port_w.get(str(path.get("from")))
        tw = port_w.get(str(path.get("to")))
        if fw and tw and fw != tw and not path.get("through_converter"):
            issues.append(Issue(
                code="IP_WIDTH_CONVERSION_MISSING",
                severity="ERROR",
                message=f"数据通路 {path.get('id','')} 位宽 {fw}→{tw} 不一致，缺明确 Converter",
                object_id=str(path.get("id", "")),
                rule="ip.bitwidth_converter",
                data={"from_width": fw, "to_width": tw},
            ))
    return issues


def _check_pipelines(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for pipe in ip.get("pipelines", []) or []:
        stages = pipe.get("stages", []) or []
        indexes = [s.get("index") for s in stages if s.get("index") is not None]
        if len(set(indexes)) != len(indexes):
            issues.append(Issue(
                code="IP_PIPELINE_STAGE_DUP",
                severity="ERROR",
                message=f"流水线 {pipe.get('id','')} 存在重复 stage 编号",
                object_id=str(pipe.get("id", "")),
                rule="ip.pipeline_stage_unique",
            ))
        for s in stages:
            idx = s.get("index")
            if idx is not None and (idx < 0 or idx >= len(stages)):
                issues.append(Issue(
                    code="IP_PIPELINE_STAGE_OUT_OF_RANGE",
                    severity="WARNING",
                    message=f"流水线 {pipe.get('id','')} stage {idx} 超出范围",
                    object_id=str(pipe.get("id", "")),
                    rule="ip.pipeline_stage",
                ))
    return issues


def _check_fifo(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for b in ip.get("buffers", []) or []:
        if b.get("kind") == "fifo":
            depth = b.get("depth")
            width = b.get("width")
            if depth is None or depth < 1:
                issues.append(Issue(
                    code="IP_FIFO_DEPTH_INVALID",
                    severity="WARNING",
                    message=f"FIFO {b.get('id','')} 深度无效: {depth!r}",
                    object_id=str(b.get("id", "")),
                    rule="ip.fifo_depth",
                ))
            if width is None or width < 1:
                issues.append(Issue(
                    code="IP_FIFO_WIDTH_INVALID",
                    severity="WARNING",
                    message=f"FIFO {b.get('id','')} 数据宽度无效: {width!r}",
                    object_id=str(b.get("id", "")),
                    rule="ip.fifo_width",
                ))
            if b.get("async") and (not b.get("read_clock_domain") or not b.get("write_clock_domain")):
                issues.append(Issue(
                    code="IP_FIFO_ASYNC_DOMAINS_MISSING",
                    severity="WARNING",
                    message=f"异步 FIFO {b.get('id','')} 缺少读写时钟域",
                    object_id=str(b.get("id", "")),
                    rule="ip.fifo_async",
                ))
    return issues


def _check_cdc_rdc(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for cdc in ip.get("cdc_paths", []) or []:
        mech = cdc.get("mechanism")
        if mech in (None, "", "none", "tbd"):
            if not cdc.get("waiver"):
                issues.append(Issue(
                    code="IP_CDC_NO_MECHANISM",
                    severity="ERROR",
                    message=f"CDC 路径 {cdc.get('id','')} 缺 Synchronizer/Handshake/Async FIFO 且无 waiver",
                    object_id=str(cdc.get("id", "")),
                    rule="ip.cdc_mechanism",
                ))
        if cdc.get("from_domain") == cdc.get("to_domain"):
            issues.append(Issue(
                code="IP_CDC_SAME_DOMAIN",
                severity="INFO",
                message=f"CDC 路径 {cdc.get('id','')} 源/目标时钟域相同",
                object_id=str(cdc.get("id", "")),
                rule="ip.cdc_same_domain",
            ))
    for rdc in ip.get("rdc_paths", []) or []:
        if not rdc.get("mechanism") and not rdc.get("waiver"):
            issues.append(Issue(
                code="IP_RDC_NO_SYNC",
                severity="ERROR",
                message=f"跨复位域 {rdc.get('id','')} 缺 Reset Deassert 同步",
                object_id=str(rdc.get("id", "")),
                rule="ip.rdc_sync",
            ))
    return issues


def _check_safety(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    ids = _collect_module_ids(ip)
    for sm in ip.get("safety_mechanisms", []) or []:
        for mon in sm.get("monitors", []) or []:
            if mon not in ids:
                issues.append(Issue(
                    code="IP_SAFETY_MONITOR_MISSING",
                    severity="WARNING",
                    message=f"安全机制 {sm.get('id','')} 的监测对象 {mon!r} 不存在",
                    object_id=str(sm.get("id", "")),
                    rule="ip.safety_monitor",
                ))
        if not sm.get("fault_response"):
            issues.append(Issue(
                code="IP_SAFETY_NO_RESPONSE",
                severity="WARNING",
                message=f"安全机制 {sm.get('id','')} 缺少故障响应定义",
                object_id=str(sm.get("id", "")),
                rule="ip.safety_response",
            ))
        if not sm.get("reporting_path"):
            issues.append(Issue(
                code="IP_SAFETY_NO_REPORTING",
                severity="WARNING",
                message=f"安全机制 {sm.get('id','')} 缺少上报路径",
                object_id=str(sm.get("id", "")),
                rule="ip.safety_reporting",
            ))
    return issues


def _check_register_binding(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for ri in ip.get("register_interfaces", []) or []:
        if ri.get("fields") and not ri.get("systemrdl_binding"):
            issues.append(Issue(
                code="IP_REG_NO_RDL_BINDING",
                severity="INFO",
                message=f"寄存器接口 {ri.get('id','')} 有字段但未绑定 SystemRDL",
                object_id=str(ri.get("id", "")),
                rule="ip.reg_binding",
            ))
    return issues


def _check_rtl_binding(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    mod_ids = {str(m.get("id")) for m in ip.get("modules", []) or []}
    bound = {str(b.get("module")) for b in ip.get("rtl_bindings", []) or []}
    for mid in mod_ids:
        if mid not in bound:
            issues.append(Issue(
                code="IP_MODULE_NO_RTL_BINDING",
                severity="WARNING",
                message=f"模块 {mid} 未绑定 RTL 实例",
                object_id=mid,
                rule="ip.rtl_binding",
            ))
    return issues


def _check_multi_driver(model: dict[str, Any], ip: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    # 多源驱动端口应经 MUX/Arbiter（简化：datapath 多个 to 同一目标）
    to_count: dict[str, list[str]] = {}
    for path in ip.get("datapaths", []) or []:
        t = str(path.get("to"))
        if t:
            to_count.setdefault(t, []).append(str(path.get("id")))
    arbiter_outputs = {str(a.get("output")) for a in ip.get("arbiters", []) or []}
    mux = {m.get("id") for m in ip.get("modules", []) or [] if m.get("kind") == "mux"}
    for t, owners in to_count.items():
        if len(owners) > 1 and t not in arbiter_outputs and t not in mux:
            issues.append(Issue(
                code="IP_MULTI_DRIVER_NO_ARBITER",
                severity="WARNING",
                message=f"目标 {t} 存在多源驱动 {owners}，但未经过 MUX/Arbiter",
                object_id=t,
                rule="ip.multi_driver",
                data={"drivers": owners},
            ))
    return issues
