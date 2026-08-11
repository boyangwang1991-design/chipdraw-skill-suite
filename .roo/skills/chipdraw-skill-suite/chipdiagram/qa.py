"""结构校验与视觉 QA（建设方案 §10 Gate 3 / Gate 4 的结构部分）。

优先确定性结构检查（重叠、线穿块、标签裁切、页面溢出、图例、字号），
视觉 AI 仅作为补充（建设方案 §16：结构检查优先，视觉 AI 仅作补充）。

依赖上游封装脚本：
- `engines/shared/validate.py`：Draw.io 结构 lint（悬空边/重复 ID/重叠/线穿块）
- `engines/shared/repair_png.py`：修复 -e PNG 截断
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from .issues import Issue

SHARED_DIR = os.path.join(os.path.dirname(__file__), "engines", "shared")


def inspect_artifacts(artifacts: list[dict[str, str]], model: dict[str, Any]) -> list[Issue]:
    """对产物做结构 QA，返回问题列表。"""
    issues: list[Issue] = []
    drawio_files = [a for a in artifacts if a.get("format") == "drawio" and a.get("path")]
    png_files = [a for a in artifacts if a.get("format") == "png" and a.get("path")]

    # Draw.io 结构检查
    for art in drawio_files:
        issues.extend(_check_drawio_structure(art["path"]))

    # PNG 完整性（IEND 截断）
    for art in png_files:
        issues.extend(_check_png_integrity(art["path"]))

    # 对象数量一致性（Gate 4）：关键对象数量与模型一致
    issues.extend(_check_object_count(artifacts, model))
    return issues


def _run_shared_script(script: str, args: list[str]) -> tuple[int, str]:
    """运行 engines/shared 下的封装脚本，返回 (returncode, output)。"""
    script_path = os.path.join(SHARED_DIR, script)
    if not os.path.isfile(script_path):
        return -1, f"缺少共享脚本 {script}"
    try:
        proc = subprocess.run(
            [sys.executable, script_path, *args],
            capture_output=True, text=True, timeout=120,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc)


def _check_drawio_structure(path: str) -> list[Issue]:
    issues: list[Issue] = []
    code, out = _run_shared_script("validate.py", [path])
    if code != 0:
        # 上游 validate.py 非零退出表示存在 error 或（--strict 下）warning
        issues.append(Issue(
            code="QA_DRAWIO_STRUCTURE",
            severity="WARNING",
            message=f"Draw.io 结构检查发现疑似问题（exit={code}）：{out.strip()[:400]}",
            path=path,
            rule="qa.structure",
        ))
    return issues


def _check_png_integrity(path: str) -> list[Issue]:
    issues: list[Issue] = []
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        if data[-4:] == b"IEND" and len(data) >= 12:
            # 完整 PNG 以 8 字节 IEND type+CRC 结束；上游 bug 只留 4 字节长度
            if data[-8:-4] != b"IEND":
                issues.append(Issue(
                    code="QA_PNG_TRUNCATED",
                    severity="WARNING",
                    message=f"PNG 的 IEND chunk 截断（缺少 type+CRC），建议运行 repair_png.py：{path}",
                    path=path,
                    rule="qa.png",
                ))
    except OSError:
        pass
    return issues


def _check_object_count(artifacts: list[dict[str, str]], model: dict[str, Any]) -> list[Issue]:
    """Gate 4：渲染件关键对象数量与模型一致（用渲染日志或产物元数据核对）。

    由于 Draw.io 导出不直接暴露对象计数，这里通过产物 JSON 元数据（如果有）
    或基于模型做结构性提醒。完整核对依赖渲染器写入 stats。
    """
    issues: list[Issue] = []
    stats = artifacts and artifacts[0].get("stats")
    if not stats:
        return issues
    model_blocks = _model_block_count(model)
    if model_blocks is not None and stats.get("blocks") != model_blocks:
        issues.append(Issue(
            code="QA_OBJECT_COUNT_MISMATCH",
            severity="WARNING",
            message=f"渲染块数 {stats.get('blocks')} 与模型块数 {model_blocks} 不一致",
            rule="qa.object_count",
            data={"rendered": stats.get("blocks"), "model": model_blocks},
        ))
    return issues


def _model_block_count(model: dict[str, Any]) -> int | None:
    dtype = model["diagram"]["type"]
    node_key = {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }[dtype]
    node = model.get(node_key) or {}
    arrays = ("instances", "modules", "states", "devices")
    total = 0
    for a in arrays:
        if isinstance(node.get(a), list):
            total += len(node[a])
    return total if total > 0 else None
