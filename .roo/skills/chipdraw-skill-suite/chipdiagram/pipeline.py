"""统一执行流水线（建设方案 §2.3）。

```
输入资产 → 任务识别与路由 → 抽取并归一化语义模型 → Schema与专业规则校验
        → 视图选择与复杂度控制 → 自动布局与专业后端渲染 → 结构校验与视觉QA
        → 发布图形、报告与Manifest
```

失败处理原则（建设方案 §2.3）：
- 事实不完整 → 显式 TBD 与待确认项，不静默补全关键连接；
- ERROR（Schema 错误、端点不存在、电气短路）→ 阻断正式生成；
- WARNING（轻微布局、非关键悬空）→ 允许草稿；
- 所有自动推断记录来源和置信度；
- 输入、归一化模型、最终输出之间可追踪。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from . import model as model_mod
from .issues import Issue, block_error, count_by_severity, sort_issues
from . import views as views_mod


@dataclass
class PipelineResult:
    """一次完整流水线运行的结果。"""

    model: dict[str, Any]
    normalized: dict[str, Any]
    issues: list[Issue]
    selections: list[views_mod.ViewSelection]
    artifacts: list[dict[str, str]] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    blocked: bool = False

    @property
    def error_count(self) -> int:
        return count_by_severity(self.issues)["ERROR"]

    @property
    def warning_count(self) -> int:
        return count_by_severity(self.issues)["WARNING"]


def load_and_normalize(inputs: list[str], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """加载并归一化输入模型（支持 YAML/JSON 文件列表）。"""
    if not inputs:
        raise model_mod.ModelError("未提供任何输入文件")
    merged: dict[str, Any] = {}
    for path in inputs:
        data = model_mod.load_yaml_file(path)
        merged = _merge_envelope(merged, data, path)
    return model_mod.normalize_model(merged, source_path=inputs[0] if inputs else "")


def _merge_envelope(acc: dict[str, Any], data: dict[str, Any], path: str) -> dict[str, Any]:
    """合并多个输入：专业节点取后加载者覆盖，来源累加。"""
    import copy
    result = copy.deepcopy(acc) if acc else {}
    for k, v in data.items():
        if k == "provenance":
            result.setdefault("provenance", {}).setdefault("sources", [])
            for s in v.get("sources", []):
                if not any(x.get("path") == s.get("path") for x in result["provenance"]["sources"]):
                    result["provenance"]["sources"].append(s)
        elif k in ("soc", "ip", "behavior", "circuit", "diagram", "style", "layout", "outputs", "traceability", "view"):
            result[k] = v
        else:
            result[k] = v
    return result


def validate(model: dict[str, Any], profile: str = "default") -> list[Issue]:
    """Schema 与专业规则校验（Gate 1 + Gate 2）。"""
    from .validators.common_validator import validate_schema_and_common
    from .validators.soc_validator import validate_soc
    from .validators.ip_validator import validate_ip
    from .validators.behavior_validator import validate_behavior
    from .validators.circuit_validator import validate_circuit

    issues: list[Issue] = []
    issues.extend(validate_schema_and_common(model, profile))
    dtype = model["diagram"]["type"]
    if dtype == "soc_architecture":
        issues.extend(validate_soc(model, profile))
    elif dtype == "ip_architecture":
        issues.extend(validate_ip(model, profile))
    elif dtype == "rtl_behavior":
        issues.extend(validate_behavior(model, profile))
    elif dtype == "transistor_schematic":
        issues.extend(validate_circuit(model, profile))
    return sort_issues(issues)


def select_views(model: dict[str, Any], request: Any = None) -> list[views_mod.ViewSelection]:
    """视图选择与复杂度控制。"""
    selections = views_mod.select_views(model, request)
    applied: list[views_mod.ViewSelection] = []
    for sel in selections:
        applied.append(views_mod.apply_view(model, sel))
    return applied


def compute_layout(selection: views_mod.ViewSelection, theme: dict[str, Any] | None = None) -> views_mod.ViewSelection:
    """计算布局（由引擎填充几何信息）。本步骤由各引擎完成，此处保留接口。"""
    from .engines.layout import compute_view_layout
    return compute_view_layout(selection, theme or {})


def render(selection: views_mod.ViewSelection, formats: list[str] | None = None,
           out_dir: str = ".", theme: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """调用专业后端渲染，返回产物列表 [{path, format, kind}]。"""
    from .engines.renderer import render_view
    return render_view(selection, formats=formats, out_dir=out_dir, theme=theme or {})


def inspect_artifacts(artifacts: list[dict[str, str]], model: dict[str, Any]) -> list[Issue]:
    """结构校验与视觉 QA（Gate 3 + Gate 4 的结构部分）。"""
    from .qa import inspect_artifacts as _inspect
    return _inspect(artifacts, model)


def publish(model: dict[str, Any], issues: list[Issue], artifacts: list[dict[str, str]],
            qa_issues: list[Issue], out_dir: str = ".") -> dict[str, Any]:
    """生成 validation 报告与 Manifest（建设方案 §9）。"""
    from .publish import publish as _publish
    return _publish(model, issues, artifacts, qa_issues, out_dir=out_dir)


def run_pipeline(inputs: list[str], request: Any = None, formats: list[str] | None = None,
                 out_dir: str = ".", profile: str = "default",
                 policy: dict[str, Any] | None = None,
                 allow_draft: bool = True) -> PipelineResult:
    """一次性运行完整流水线。

    - blocked=True 表示存在 ERROR（默认阻断正式发布，除非 allow_draft）
    - 返回 PipelineResult，含 issues、selections、artifacts、manifest
    """
    normalized = load_and_normalize(inputs, policy)
    issues = validate(normalized, profile)
    selections = select_views(normalized, request)

    blocked = block_error(issues)
    artifacts: list[dict[str, str]] = []
    qa_issues: list[Issue] = []

    if blocked and not allow_draft:
        return PipelineResult(
            model=normalized, normalized=normalized, issues=issues,
            selections=selections, blocked=True,
        )

    all_artifacts: list[dict[str, str]] = []
    all_qa: list[Issue] = []
    for sel in selections:
        sel = compute_layout(sel)
        arts = render(sel, formats=formats, out_dir=out_dir)
        all_artifacts.extend(arts)
        all_qa.extend(inspect_artifacts(arts, sel.model))

    manifest = publish(normalized, issues, all_artifacts, all_qa, out_dir=out_dir)
    return PipelineResult(
        model=normalized, normalized=normalized, issues=issues,
        selections=selections, artifacts=all_artifacts, manifest=manifest,
        blocked=blocked,
    )
