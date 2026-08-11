"""WaveDrom 时序渲染（建设方案 §3.4-B）。

输入：behavior 节点（timing 模型：clock + signals + markers）
输出：
- diagram.wave.json  （WaveJSON，权威中间格式）
- diagram.svg        （优先 wavedrom-cli；缺失时尝试本地 SVG 兜底）
- diagram.png        （wavedrom-cli 支持时）
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from ...views import ViewSelection


def render_timing(selection: ViewSelection, formats: list[str] | None,
                  out_dir: str, theme: dict[str, Any]) -> list[dict[str, str]]:
    """生成数字时序图。"""
    behavior = selection.model.get("behavior") or {}
    if not behavior.get("signals"):
        return []

    wavejson = _to_wavejson(behavior)
    os.makedirs(out_dir, exist_ok=True)
    wave_path = os.path.join(out_dir, "diagram.wave.json")
    with open(wave_path, "w", encoding="utf-8") as fh:
        json.dump(wavejson, fh, ensure_ascii=False, indent=2)

    artifacts: list[dict[str, str]] = [{"path": wave_path, "format": "wavejson", "kind": "editable"}]

    # 渲染 SVG/PNG（wavedrom-cli）
    svg_path, png_path = _render_with_cli(wave_path, out_dir)
    if svg_path:
        artifacts.append({"path": svg_path, "format": "svg", "kind": "rendered"})
    if png_path:
        artifacts.append({"path": png_path, "format": "png", "kind": "rendered"})
    return artifacts


def _to_wavejson(behavior: dict[str, Any]) -> dict[str, Any]:
    clock = behavior.get("clock") or {}
    head = {"tick": clock.get("period") or "", "phase": clock.get("phase") or ""}
    signals: list[Any] = []
    for s in behavior.get("signals", []):
        entry: dict[str, Any] = {"name": s.get("name"), "wave": s.get("wave")}
        if s.get("data"):
            entry["data"] = s["data"]
        if s.get("node"):
            entry["node"] = s["node"]
        signals.append(entry)

    wavejson: dict[str, Any] = {}
    if head.get("tick") or head.get("phase"):
        wavejson["head"] = {k: v for k, v in head.items() if v}
    wavejson["signal"] = signals
    markers = behavior.get("markers")
    if markers:
        wavejson["marker"] = markers
    return wavejson


def _render_with_cli(wave_path: str, out_dir: str) -> tuple[str | None, str | None]:
    """用 wavedrom-cli 渲染 SVG/PNG；返回 (svg, png) 路径。"""
    cli = shutil.which("wavedrom-cli")
    if cli is None:
        return None, None

    svg_path = os.path.join(out_dir, "diagram.svg")
    try:
        proc = subprocess.run(
            [cli, "--input", wave_path, "--svg", svg_path],
            capture_output=True, text=True, timeout=120)
        if proc.returncode != 0 or not os.path.isfile(svg_path):
            return None, None
    except Exception:  # noqa: BLE001
        return None, None

    png_path = None
    png_candidate = os.path.join(out_dir, "diagram.png")
    try:
        proc = subprocess.run(
            [cli, "--input", wave_path, "--png", png_candidate],
            capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and os.path.isfile(png_candidate):
            png_path = png_candidate
    except Exception:  # noqa: BLE001
        pass
    return svg_path, png_path
