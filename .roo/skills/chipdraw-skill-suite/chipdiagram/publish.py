"""发布环节：Manifest 与 validation 报告（建设方案 §9）。

标准输出件（每个视图至少）：
    <view-name>/
    ├── source.yaml          # 用户输入或 View 定义
    ├── model.normalized.yaml
    ├── diagram.drawio / .svg / .png / .pdf
    ├── validation.json      # 机器可读
    ├── validation.md        # 人可读
    └── manifest.yaml

Manifest 固化全部版本与 Hash（建设方案 §15 兼容策略）。
"""
from __future__ import annotations

import datetime
import json
import os
from typing import Any

from .issues import Issue, count_by_severity, sort_issues
from .model import compute_model_hash


def publish(model: dict[str, Any], issues: list[Issue],
            artifacts: list[dict[str, str]], qa_issues: list[Issue],
            out_dir: str = ".") -> dict[str, Any]:
    """生成 validation.json、validation.md 与 manifest.yaml。

    返回 manifest 字典，同时把文件写入 out_dir。
    """
    os.makedirs(out_dir, exist_ok=True)
    all_issues = sort_issues(issues + qa_issues)
    counts = count_by_severity(all_issues)

    # --- validation.json / md ---
    validation = {
        "diagram_id": model["diagram"]["id"],
        "schema_version": model.get("schema_version", "1.0"),
        "generator": "chip-design-diagram-suite",
        "generated_at": _now(),
        "quality": counts,
        "issues": [i.to_dict() for i in all_issues],
        "blocked": counts["ERROR"] > 0,
    }
    _write_json(os.path.join(out_dir, "validation.json"), validation)
    _write_md(os.path.join(out_dir, "validation.md"), validation)

    # --- manifest.yaml ---
    manifest = {
        "manifest_version": "1.0",
        "diagram_id": model["diagram"]["id"],
        "design_version": model.get("traceability", {}).get("design_version", "0.0.0"),
        "model_hash": model.get("_model_hash") or compute_model_hash(model),
        "source_files": _source_files(model),
        "artifacts": [_strip_stats(a) for a in artifacts],
        "statistics": _statistics(model, artifacts),
        "quality": counts,
        "assumptions": _assumptions(model, all_issues),
        "versions": {
            "generator": "1.0.0",
            "schema": model.get("schema_version", "1.0"),
        },
    }
    _write_yaml(os.path.join(out_dir, "manifest.yaml"), manifest)
    return manifest


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _source_files(model: dict[str, Any]) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for s in model.get("provenance", {}).get("sources", []) or []:
        entry = {"path": s.get("path", "")}
        if s.get("role"):
            entry["role"] = s["role"]
        files.append(entry)
    return files


def _strip_stats(artifact: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in artifact.items() if k != "stats"}


def _statistics(model: dict[str, Any], artifacts: list[dict[str, str]]) -> dict[str, Any]:
    node_key = {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }[model["diagram"]["type"]]
    node = model.get(node_key) or {}
    stats: dict[str, Any] = {}
    for array_key in ("instances", "modules", "ports", "states", "devices", "connections", "transitions", "signals", "nets"):
        if isinstance(node.get(array_key), list):
            stats[array_key] = len(node[array_key])
    stats["artifacts"] = len(artifacts)
    return stats


def _assumptions(model: dict[str, Any], issues: list[Issue]) -> list[dict[str, Any]]:
    """收集推断/TBD 记录（建设方案 §2.3：所有自动推断必须在 Manifest 记录来源和置信度）。"""
    assumptions: list[dict[str, Any]] = []
    idx = 1
    for issue in issues:
        if issue.code in ("COMMON_TRACE_INFERRED", "BEHAVIOR_INFERRED", "CIRCUIT_INFERRED",
                          "SOC_INFERRED", "IP_INFERRED", "COMMON_TBD", "VIEW_BLOCK_FILTERED"):
            assumptions.append({
                "id": f"ASM-{idx:03d}",
                "text": issue.message,
                "status": "pending_confirmation",
                "object_id": issue.object_id,
            })
            idx += 1
    return assumptions


def _write_json(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _write_md(path: str, validation: dict[str, Any]) -> None:
    lines = [
        f"# 校验报告：{validation['diagram_id']}",
        "",
        f"- 生成器：{validation['generator']}",
        f"- 生成时间：{validation['generated_at']}",
        f"- Schema 版本：{validation['schema_version']}",
        "",
        "## 质量汇总",
        "",
        f"- ERROR：{validation['quality']['ERROR']}",
        f"- WARNING：{validation['quality']['WARNING']}",
        f"- INFO：{validation['quality']['INFO']}",
        "",
        "## 问题清单",
        "",
    ]
    if validation["issues"]:
        for i in validation["issues"]:
            lines.append(f"- **[{i['severity']}]** `{i['code']}` {i['message']}")
            if i.get("path"):
                lines.append(f"  - 位置：`{i['path']}`")
    else:
        lines.append("无问题。")
    lines.append("")
    if validation["blocked"]:
        lines.append("> ⛔ 存在 ERROR，正式发布被阻断。")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _write_yaml(path: str, data: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError:  # pragma: no cover
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
