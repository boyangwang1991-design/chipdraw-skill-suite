"""视图选择与复杂度控制（建设方案 §4.3 View Filter、§3.1 路由、§10 Gate）。

一份 SSOT 应能生成多张图。视图文件只定义选择和显示策略，不复制事实。
本模块实现：

- `select_views(model, request)`：根据用户请求/视图定义挑选视图
- `apply_view(model, view)`：对模型应用 View Filter，产出裁剪后的视图模型
- `complexity_check`：超过可见块/连接阈值时给出拆图建议
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .issues import Issue


@dataclass
class ViewSelection:
    """一次视图选择的产物。"""

    view_id: str
    subtype: str
    model: dict[str, Any]            # 裁剪后的视图模型
    issues: list[Issue] = field(default_factory=list)


# 各层级可用的视图目录（建设方案 §3.2/3.3/3.4）
SOC_VIEWS = {
    "soc_overview": "soc_architecture",
    "bus_interconnect": "soc_architecture",
    "address_map": "soc_architecture",
    "clock_reset": "soc_architecture",
    "power_domain": "soc_architecture",
    "interrupt_network": "soc_architecture",
    "safety_security": "soc_architecture",
    "fusesoc_dependency": "soc_architecture",
    "chiplet_topology": "soc_architecture",
}

IP_VIEWS = {
    "ip_overview": "ip_architecture",
    "datapath": "ip_architecture",
    "pipeline": "ip_architecture",
    "buffer_fifo": "ip_architecture",
    "interface_expanded": "ip_architecture",
    "register_interface": "ip_architecture",
    "cdc_rdc": "ip_architecture",
    "safety_mechanism": "ip_architecture",
    "rtl_hierarchy": "ip_architecture",
    "bitwidth_conversion": "ip_architecture",
}

BEHAVIOR_VIEWS = {
    "fsm": "rtl_behavior",
    "timing": "rtl_behavior",
    "sequence": "rtl_behavior",
}

TRANSISTOR_VIEWS = {
    "schematic_illustration": "transistor_schematic",
    "schematic_engineering": "transistor_schematic",
}

ALL_VIEWS: dict[str, str] = {}
ALL_VIEWS.update(SOC_VIEWS)
ALL_VIEWS.update(IP_VIEWS)
ALL_VIEWS.update(BEHAVIOR_VIEWS)
ALL_VIEWS.update(TRANSISTOR_VIEWS)


def resolve_view_subtype(view: str) -> Optional[str]:
    """根据视图名解析其 subtype（未知返回 None）。"""
    return ALL_VIEWS.get(view)


def select_views(model: dict[str, Any], request: Any = None) -> list[ViewSelection]:
    """根据用户请求（可含 view/subtype）或模型自带视图定义选择视图。

    - request 为字符串时视为视图名；
    - request 为字典时支持 {"view": "...", "subtype": "..."}；
    - 模型自带 view 定义（model["view"]）时使用之。
    """
    selections: list[ViewSelection] = []
    req_view = None
    req_subtype = None

    if isinstance(request, str):
        req_view = request
    elif isinstance(request, dict):
        req_view = request.get("view")
        req_subtype = request.get("subtype")

    if req_view:
        subtype = req_subtype or resolve_view_subtype(req_view)
        if subtype is None:
            subtype = "soc_architecture"  # 兜底
        selections.append(ViewSelection(view_id=req_view, subtype=subtype, model=model))
        return selections

    # 模型自带 view 定义
    view_def = model.get("view")
    if isinstance(view_def, dict) and view_def.get("id"):
        selections.append(ViewSelection(
            view_id=view_def["id"],
            subtype=resolve_view_subtype(view_def["id"]) or "soc_architecture",
            model=model,
        ))
        return selections

    # 默认视图：按 diagram.type 取首个
    dtype = model["diagram"]["type"]
    default_view = {
        "soc_architecture": "soc_overview",
        "ip_architecture": "ip_overview",
        "rtl_behavior": "fsm",
        "transistor_schematic": "schematic_illustration",
    }[dtype]
    selections.append(ViewSelection(view_id=default_view, subtype=default_view, model=model))
    return selections


def apply_view(model: dict[str, Any], view: ViewSelection) -> ViewSelection:
    """对模型应用 View Filter，产出裁剪后的视图模型。

    支持 include（连接类型/块白名单）、show（端口/位宽/域）、collapse（总线收敛）。
    未提供 include 时原样返回（视图只改变 subtype 标记）。
    """
    issues: list[Issue] = []
    if not isinstance(model.get("view"), dict):
        # 无显式 View Filter，直接以当前模型作为视图模型
        view.model = model
        view.subtype = view.subtype or resolve_view_subtype(view.view_id) or "soc_architecture"
        return view

    vf = model["view"]
    result = _deep_copy(model)

    included_blocks = vf.get("include", {}).get("blocks")
    if included_blocks:
        node_key = _node_key(model)
        for array_key in ("instances", "modules"):
            entries = result.get(node_key, {}).get(array_key)
            if not isinstance(entries, list):
                continue
            kept = [e for e in entries if str(e.get("id")) in included_blocks]
            removed = [e for e in entries if str(e.get("id")) not in included_blocks]
            result[node_key][array_key] = kept
            if removed:
                issues.append(Issue(
                    code="VIEW_BLOCK_FILTERED",
                    severity="INFO",
                    message=f"视图 {view.view_id} 过滤掉 {len(removed)} 个块",
                    rule="view.filter",
                ))

    # 连接裁剪
    conn_kinds = vf.get("include", {}).get("connection_kinds")
    if conn_kinds:
        node_key = _node_key(model)
        conns = result.get(node_key, {}).get("connections")
        if isinstance(conns, list):
            result[node_key]["connections"] = [c for c in conns if c.get("kind") in conn_kinds]

    # 收敛总线（collapse.axi_channels）
    if vf.get("collapse", {}).get("axi_channels", True):
        node_key = _node_key(model)
        conns = result.get(node_key, {}).get("connections")
        if isinstance(conns, list):
            seen: set[tuple[str, str]] = set()
            kept: list[dict[str, Any]] = []
            for c in conns:
                key = (str(c.get("from")), str(c.get("to")))
                if c.get("kind") == "bus" and key in seen:
                    continue  # 同一对端口的第二条总线连接收敛
                seen.add(key)
                kept.append(c)
            result[node_key]["connections"] = kept

    view.model = result
    view.issues = issues
    return view


def complexity_check(view: ViewSelection, max_blocks: int = 20, max_connections: int = 35) -> list[Issue]:
    """复杂度控制：超过阈值时给出自动拆图建议（建设方案 §3.2 布局规则）。"""
    issues: list[Issue] = []
    node_key = _node_key(view.model)
    node = view.model.get(node_key) or {}

    n_blocks = 0
    for array_key in ("instances", "modules", "states", "devices"):
        n_blocks += len(node.get(array_key, []) or [])
    n_conns = len(node.get("connections", []) or [])

    if n_blocks > max_blocks:
        issues.append(Issue(
            code="COMPLEXITY_BLOCKS",
            severity="WARNING",
            message=f"可见块 {n_blocks} 超过阈值 {max_blocks}，建议按子系统/域拆分并增加下钻链接",
            rule="layout.complexity",
            data={"blocks": n_blocks, "max": max_blocks},
        ))
    if n_conns > max_connections:
        issues.append(Issue(
            code="COMPLEXITY_CONNECTIONS",
            severity="WARNING",
            message=f"可见连接 {n_conns} 超过阈值 {max_connections}，建议聚合总线或分层显示",
            rule="layout.complexity",
            data={"connections": n_conns, "max": max_connections},
        ))
    return issues


def _node_key(model: dict[str, Any]) -> str:
    return {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }[model["diagram"]["type"]]


def _deep_copy(model: dict[str, Any]) -> dict[str, Any]:
    import json
    return json.loads(json.dumps(model))
