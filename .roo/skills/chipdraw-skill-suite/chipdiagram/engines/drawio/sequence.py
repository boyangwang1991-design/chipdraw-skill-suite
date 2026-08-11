"""事务序列图引擎（封装上游 seqlayout.py 确定性几何）。

事务序列图表达 Actor/Module 之间的消息次序，不承担逐周期电平表达
（建设方案 §3.4-C）。典型场景：CPU→DMA→Interconnect→Memory；
Interrupt Source→PIC→CLIC；UVM Sequence→Driver→DUT→Monitor→Scoreboard。

输出优先为可编辑 Draw.io 序列图，并可附 Mermaid 版本用于文档内嵌。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from ...views import ViewSelection
from ..shared import seqlayout as seqlayout_mod  # noqa: F401

SHARED_DIR = os.path.join(os.path.dirname(__file__), "..", "shared")


def render_sequence(selection: ViewSelection, formats: list[str] | None,
                    out_dir: str, theme: dict[str, Any]) -> list[dict[str, str]]:
    """生成事务序列图的 .drawio（并可选 Mermaid）。"""
    model = selection.model
    behavior = model.get("behavior") or {}
    if not behavior.get("participants") and not behavior.get("messages"):
        return []

    seq_json = _to_seq_json(model, behavior)
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "diagram.seq.json")
    drawio_path = os.path.join(out_dir, "diagram.drawio")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(seq_json, fh, ensure_ascii=False, indent=2)

    artifacts: list[dict[str, str]] = []
    script = os.path.join(SHARED_DIR, "seqlayout.py")
    if os.path.isfile(script):
        try:
            proc = subprocess.run(
                [sys.executable, script, json_path, "-o", drawio_path],
                capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and os.path.isfile(drawio_path):
                artifacts.append({"path": drawio_path, "format": "drawio", "kind": "editable"})
        except Exception:  # noqa: BLE001
            pass
    if not artifacts:
        # 降级：直接调用共享模块函数生成
        try:
            seqlayout_mod.main([json_path, "-o", drawio_path])
            if os.path.isfile(drawio_path):
                artifacts.append({"path": drawio_path, "format": "drawio", "kind": "editable"})
        except Exception:  # noqa: BLE001
            pass

    # Mermaid 附本（文档内嵌）
    mmd = _to_mermaid(seq_json)
    if mmd:
        mmd_path = os.path.join(out_dir, "diagram.mmd")
        with open(mmd_path, "w", encoding="utf-8") as fh:
            fh.write(mmd)
        artifacts.append({"path": mmd_path, "format": "mermaid", "kind": "document"})

    # 导出 PNG/SVG
    if artifacts and any(a["format"] == "drawio" for a in artifacts):
        from .exporter import export_drawio
        fmt = [f for f in (formats or ["drawio", "svg", "png"]) if f in ("svg", "png", "pdf")]
        if fmt:
            exported = export_drawio(drawio_path, os.path.join(out_dir, "diagram"), fmt, final=True)
            for p in exported:
                artifacts.append({"path": p, "format": p.rsplit(".", 1)[-1], "kind": "rendered"})
    return artifacts


def _to_seq_json(model: dict[str, Any], behavior: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": model.get("diagram", {}).get("title", model.get("diagram", {}).get("id", "sequence")),
        "participants": behavior.get("participants", []),
        "messages": behavior.get("messages", []),
    }


def _to_mermaid(seq_json: dict[str, Any]) -> str:
    """生成 Mermaid sequenceDiagram 文本（文档内嵌版）。"""
    lines = ["sequenceDiagram"]
    for p in seq_json.get("participants", []):
        lines.append(f"    participant {p.get('id')} as {p.get('label', p.get('id'))}")
    for m in seq_json.get("messages", []):
        frm = m.get("from")
        to = m.get("to")
        label = m.get("label", "")
        if m.get("note"):
            lines.append(f"    Note over {m.get('over', frm)}: {m.get('note')}")
            continue
        if m.get("return"):
            lines.append(f"    {to}-->>{frm}: {label}")
        elif m.get("async"):
            lines.append(f"    {frm}-->{to}: {label}")
        else:
            lines.append(f"    {frm}->>{to}: {label}")
    return "\n".join(lines)
