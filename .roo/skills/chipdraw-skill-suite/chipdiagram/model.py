"""统一芯片图形语义模型：加载、归一化与基础访问工具。

所有图形优先由结构化事实（SSOT）生成。本模块负责：
- 从 YAML / JSON 文件加载语义模型（含公共 Envelope + 专业节点）
- 归一化：补齐默认字段、收集对象 ID、建立可追溯索引
- 提供模型访问辅助（按 id 查对象、按类型枚举等）

归一化后的模型结构遵循 schemas/common.schema.json。
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Iterable, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


class ModelError(Exception):
    """模型加载/归一化错误。"""


def _load_text(path: str) -> str:
    if not os.path.isfile(path):
        raise ModelError(f"输入文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def load_yaml_file(path: str) -> dict[str, Any]:
    """加载 YAML 或 JSON 文件为字典。"""
    if yaml is None:
        raise ModelError("缺少 PyYAML 依赖，请执行 pip install PyYAML")
    text = _load_text(path)
    try:
        data = yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001
        raise ModelError(f"解析 YAML 失败 {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ModelError(f"模型顶层必须是映射（object），实际为 {type(data).__name__}: {path}")
    return data


def load_model(path: str) -> dict[str, Any]:
    """加载并归一化一个模型文件（YAML 或 JSON）。"""
    data = load_yaml_file(path)
    return normalize_model(data, source_path=path)


def _collect_object_ids(model: dict[str, Any], key: str) -> dict[str, list[str]]:
    """从专业节点的对象列表中收集 id → 出现位置 映射。

    返回 {object_id: [array_key, ...]}，用于跨数组唯一性校验。
    """
    index: dict[str, list[str]] = {}
    for array_key, entries in (model.get(key) or {}).items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("id"):
                index.setdefault(str(entry["id"]), []).append(array_key)
    return index


def _collect_port_ids(model: dict[str, Any], key: str) -> set[str]:
    """收集实例内嵌端口 id，用于连接端点解析。"""
    ids: set[str] = set()
    for entry in (model.get(key) or {}).get("instances", []):
        for port in entry.get("ports", []):
            if port.get("id"):
                ids.add(str(port["id"]))
    return ids


def normalize_model(model: dict[str, Any], source_path: str = "") -> dict[str, Any]:
    """归一化模型：补齐默认字段，注入来源路径，建立索引。

    - 保证 diagram.type 对应的专业节点存在（缺失时报错）
    - 每个对象保持稳定（不改写业务字段），仅在顶层附加 _index 与 provenance
    """
    if "diagram" not in model:
        raise ModelError("模型缺少 diagram 节点（建设方案 §4.1 公共 Envelope）")
    diagram = model["diagram"]
    dtype = diagram.get("type")
    if dtype not in ("soc_architecture", "ip_architecture", "rtl_behavior", "transistor_schematic"):
        raise ModelError(f"未知 diagram.type: {dtype!r}")

    node_key = {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }[dtype]
    if node_key not in model:
        raise ModelError(f"diagram.type={dtype} 需要专业节点 {node_key}")

    model = json.loads(json.dumps(model))  # 深拷贝，避免污染调用方
    diagram = model["diagram"]  # 重新获取，指向拷贝后的对象

    # 补齐 envelope 默认值
    model.setdefault("schema_version", "1.0")
    diagram.setdefault("status", "draft")
    diagram.setdefault("language", "zh-CN")
    model.setdefault("style", {}).setdefault("theme", "aixsilicon-light")
    model.setdefault("style", {}).setdefault("page", "16:9")
    model.setdefault("style", {}).setdefault("colorblind_safe", True)
    model.setdefault("layout", {}).setdefault("direction", "left_to_right")
    model.setdefault("layout", {}).setdefault("max_visible_blocks", 20)
    model.setdefault("provenance", {}).setdefault("generator", "chip-design-diagram-suite")

    if source_path:
        model.setdefault("provenance", {}).setdefault("sources", [])
        if not any(s.get("path") == source_path for s in model["provenance"]["sources"]):
            model["provenance"]["sources"].insert(
                0, {"path": source_path, "role": "ssot"})

    # 建立对象 id 索引，便于校验器与渲染器快速解析端点
    index: dict[str, Any] = {
        "instances": _collect_object_ids(model, node_key),
        "modules": _collect_object_ids(model, node_key),
        "ports": _collect_port_ids(model, node_key),
        "devices": _collect_object_ids(model, node_key),
        "states": _collect_object_ids(model, node_key),
        "nets": _collect_object_ids(model, node_key),
    }
    model["_index"] = index

    # 模型哈希（结构稳定：剔除时间戳类字段后计算）
    model.setdefault("traceability", {}).setdefault("design_version", "0.0.0")
    model["_model_hash"] = compute_model_hash(model)
    return model


def compute_model_hash(model: dict[str, Any]) -> str:
    """计算稳定模型哈希（剔除 generated_at 与 _index 等非结构字段）。"""
    stable = json.loads(json.dumps(model, default=str))
    stable.pop("_index", None)
    stable.pop("_model_hash", None)
    if "provenance" in stable:
        stable["provenance"].pop("generated_at", None)
    text = json.dumps(stable, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_objects(model: dict[str, Any], object_id: str) -> list[tuple[str, dict[str, Any]]]:
    """按对象 id 查找所有匹配对象，返回 [(array_key, obj), ...]。"""
    results: list[tuple[str, dict[str, Any]]] = []
    node_key = _node_key(model)
    node = model.get(node_key) or {}
    for array_key, entries in node.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("id")) == str(object_id):
                results.append((array_key, entry))
    return results


def _node_key(model: dict[str, Any]) -> str:
    return {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }[model["diagram"]["type"]]


def dump_yaml(model: dict[str, Any], path: str) -> None:
    """将模型（剔除内部索引）写为 YAML 文件。"""
    if yaml is None:
        raise ModelError("缺少 PyYAML 依赖")
    out = json.loads(json.dumps(model, default=str))
    out.pop("_index", None)
    out.pop("_model_hash", None)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(out, fh, allow_unicode=True, sort_keys=False)


def iter_list(model: dict[str, Any], node_key: str, array_key: str) -> Iterable[dict[str, Any]]:
    """遍历专业节点的某个数组字段。"""
    node = model.get(node_key) or {}
    for entry in node.get(array_key, []) or []:
        if isinstance(entry, dict):
            yield entry
