"""公共校验器（建设方案 §10 Gate 1 / Gate 2 公共部分）。

- Schema 校验（jsonschema，按 diagram.type 加载对应 Schema）
- 对象 ID 唯一性
- Mandatory Port 悬空
- 端点存在性（连接 from/to 必须能解析到块/端口）
- 推断来源记录（trace.confidence=inferred → INFO）
"""
from __future__ import annotations

import json
import os
from typing import Any

from ..issues import Issue

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "schemas")

# 各 diagram.type 对应的专业 Schema
TYPE_SCHEMA = {
    "soc_architecture": "common.schema.json",
    "ip_architecture": "common.schema.json",
    "rtl_behavior": "common.schema.json",
    "transistor_schematic": "common.schema.json",
}


def validate_schema_and_common(model: dict[str, Any], profile: str = "default") -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(_validate_schema(model))
    issues.extend(_validate_common_rules(model))
    return issues


def _validate_schema(model: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    dtype = model.get("diagram", {}).get("type")
    if dtype not in TYPE_SCHEMA:
        issues.append(Issue(
            code="COMMON_SCHEMA_UNKNOWN_TYPE",
            severity="ERROR",
            message=f"未知 diagram.type: {dtype!r}",
            rule="schema.type",
        ))
        return issues

    try:
        import jsonschema
    except ImportError:
        # 无 jsonschema 依赖时降级为轻量检查
        return _lightweight_schema_check(model)

    schema = _load_schema("common.schema.json")
    try:
        # 注册本地 schema 目录作为相对 $ref 的解析基础（soc/ip/fsm/circuit 等）
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7

        def _resource_for(name):
            return Resource.from_contents(_load_schema(name), default_specification=DRAFT7)

        registry = Registry().with_resources([
            ("soc.schema.json", _resource_for("soc.schema.json")),
            ("ip.schema.json", _resource_for("ip.schema.json")),
            ("fsm.schema.json", _resource_for("fsm.schema.json")),
            ("circuit.schema.json", _resource_for("circuit.schema.json")),
            ("view.schema.json", _resource_for("view.schema.json")),
            ("timing.schema.json", _resource_for("timing.schema.json")),
            ("sequence.schema.json", _resource_for("sequence.schema.json")),
        ])
        validator = jsonschema.Draft7Validator(schema, registry=registry)
        for err in sorted(validator.iter_errors(model), key=lambda e: list(e.path)):
            issues.append(Issue(
                code="COMMON_SCHEMA_VIOLATION",
                severity="ERROR",
                message=f"Schema 校验失败: {err.message}",
                path="/".join(str(p) for p in err.path),
                rule="schema.validation",
                data={"path": list(err.path)},
            ))
    except jsonschema.SchemaError as exc:
        issues.append(Issue(
            code="COMMON_SCHEMA_INVALID",
            severity="ERROR",
            message=f"Schema 文件无效: {exc}",
            rule="schema.definition",
        ))
    return issues


def _load_schema(name: str) -> dict[str, Any]:
    path = os.path.join(SCHEMAS_DIR, name)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _lightweight_schema_check(model: dict[str, Any]) -> list[Issue]:
    """无 jsonschema 依赖时的最小检查。"""
    issues: list[Issue] = []
    dtype = model.get("diagram", {}).get("type")
    node_key = {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }.get(dtype)
    if node_key and node_key not in model:
        issues.append(Issue(
            code="COMMON_SCHEMA_VIOLATION",
            severity="ERROR",
            message=f"diagram.type={dtype} 缺少专业节点 {node_key}",
            rule="schema.envelope",
        ))
    return issues


def _validate_common_rules(model: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    dtype = model.get("diagram", {}).get("type")
    node_key = {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }.get(dtype)
    node = model.get(node_key) or {}

    # 对象 ID 唯一性
    issues.extend(_check_id_uniqueness(model, node, node_key))
    # 端点存在性
    issues.extend(_check_endpoints(model, node, node_key))
    # Mandatory Port
    issues.extend(_check_mandatory_ports(model, node, node_key))
    # 推断来源记录
    issues.extend(_check_inferred(model, node, node_key))
    return issues


def _collect_ids(model: dict[str, Any], node: dict[str, Any], node_key: str) -> set[str]:
    ids: set[str] = set()
    for array_key, entries in node.items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if isinstance(e, dict) and e.get("id"):
                ids.add(str(e["id"]))
    # 内嵌端口 id
    for inst in node.get("instances", []) or []:
        for p in inst.get("ports", []) or []:
            if p.get("id"):
                ids.add(str(p["id"]))
    # 信号名/状态 id
    for array_key in ("states", "signals", "devices", "nets"):
        for e in node.get(array_key, []) or []:
            if isinstance(e, dict) and e.get("id"):
                ids.add(str(e["id"]))
            elif isinstance(e, dict) and e.get("name"):
                ids.add(str(e["name"]))
    return ids


def _check_id_uniqueness(model: dict[str, Any], node: dict[str, Any], node_key: str) -> list[Issue]:
    issues: list[Issue] = []
    seen: dict[str, list[str]] = {}
    for array_key, entries in node.items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if isinstance(e, dict) and e.get("id"):
                i = str(e["id"])
                seen.setdefault(i, []).append(array_key)
    for i, locs in seen.items():
        if len(set(locs)) > 1 or len(locs) > 1:
            issues.append(Issue(
                code="COMMON_ID_NOT_UNIQUE",
                severity="ERROR",
                message=f"对象 ID 不唯一: {i!r} 出现于 {locs}",
                object_id=i,
                path=f"{node_key}.{locs[0]}",
                rule="common.id_unique",
            ))
    return issues


def _check_endpoints(model: dict[str, Any], node: dict[str, Any], node_key: str) -> list[Issue]:
    """连接的 from/to 必须能解析到块/端口 id。"""
    issues: list[Issue] = []
    ids = _collect_ids(model, node, node_key)
    for c in node.get("connections", []) or []:
        frm = str(c.get("from", ""))
        to = str(c.get("to", ""))
        if frm and frm not in ids:
            issues.append(Issue(
                code="COMMON_ENDPOINT_MISSING",
                severity="ERROR",
                message=f"连接 {c.get('id','')} 的起点不存在: {frm!r}",
                object_id=str(c.get("id", "")),
                path=f"{node_key}.connections",
                rule="common.endpoint_exists",
                data={"from": frm},
            ))
        if to and to not in ids:
            issues.append(Issue(
                code="COMMON_ENDPOINT_MISSING",
                severity="ERROR",
                message=f"连接 {c.get('id','')} 的终点不存在: {to!r}",
                object_id=str(c.get("id", "")),
                path=f"{node_key}.connections",
                rule="common.endpoint_exists",
                data={"to": to},
            ))
    return issues


def _check_mandatory_ports(model: dict[str, Any], node: dict[str, Any], node_key: str) -> list[Issue]:
    issues: list[Issue] = []
    connected = set()
    for c in node.get("connections", []) or []:
        connected.add(str(c.get("from")))
        connected.add(str(c.get("to")))
    for inst in node.get("instances", []) or []:
        for p in inst.get("ports", []) or []:
            if p.get("mandatory") and p.get("id") not in connected and inst.get("id") not in connected:
                issues.append(Issue(
                    code="COMMON_MANDATORY_PORT_DANGLING",
                    severity="WARNING",
                    message=f"Mandatory 端口悬空: {inst.get('id')}.{p.get('name')}",
                    object_id=str(p.get("id", "")),
                    rule="common.mandatory_port",
                ))
    return issues


def _check_inferred(model: dict[str, Any], node: dict[str, Any], node_key: str) -> list[Issue]:
    """所有推断对象应记录来源与置信度。"""
    issues: list[Issue] = []
    for array_key, entries in node.items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            trace = e.get("trace") or {}
            conf = trace.get("confidence")
            if conf == "inferred":
                issues.append(Issue(
                    code="COMMON_TRACE_INFERRED",
                    severity="INFO",
                    message=f"对象 {e.get('id','')} 为推断结果，需人工复核",
                    object_id=str(e.get("id", "")),
                    path=f"{node_key}.{array_key}",
                    rule="common.inferred",
                ))
            elif conf == "tbd":
                issues.append(Issue(
                    code="COMMON_TBD",
                    severity="WARNING",
                    message=f"对象 {e.get('id','')} 存在 TBD/待确认项",
                    object_id=str(e.get("id", "")),
                    path=f"{node_key}.{array_key}",
                    rule="common.tbd",
                ))
    return issues
