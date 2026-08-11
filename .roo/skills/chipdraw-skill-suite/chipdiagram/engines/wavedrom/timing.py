"""WaveDrom 时序渲染（建设方案 §3.4-B，对齐 WaveDrom Tutorial）。

输入：behavior 节点（timing 模型：clock + signals + markers + edges + config + head/foot + gaps）
输出：
- diagram.wave.json  （WaveJSON，权威中间格式）
- diagram.svg        （优先 wavedrom-cli；缺失时尝试本地 SVG 兜底）
- diagram.png        （wavedrom-cli 支持时）

对齐 WaveDrom 官方 Tutorial 的能力：
- 时钟 lane：`p/P/n/N`（正/负极性，带/不带边沿标记），支持时钟门控混合；
  缺省按信号最大周期数自动生成时钟 wave，或显式 `clock.wave`。
- 分组：`['组名', {...}, ...]` 可嵌套；或顶层 `groups` 显式声明。
- 每信号 `period`/`phase`（DDR、相移时钟）。
- 顶层 `edges`（node 锚点 + edge 箭头字符串）与 `gaps`（Gap 表达式）。
- 每 lane `over`/`under`（建立/保持时间窗口）。
- wave 支持 `['pw', {d: [...]}]`（SVG path 波形，模拟/自定义形状）。
- 渲染配置 `config`（hscale/skin/arcFontSize 等）与 `head`/`foot`（tick/tock/text）。
- markers → WaveDrom `marker` 数组。
"""
from __future__ import annotations

import json
import os
import re
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


# ---- 周期计数与时钟生成 -------------------------------------------------

# WaveDrom 时钟字符：正/负极性 × 带/不带边沿标记
_CLOCK_CHARS = set("pPnNhHlL")
# 需对应 data 值的数据字符（数字 2-9、= 延续值、x/z 总线）
_DATA_CHARS = set("23456789=")


def _wave_len(wave: Any) -> int:
    """wave 周期长度：字符串去 `|` 后取长；数组（pw path）按数字段周期估算。"""
    if isinstance(wave, str):
        return len(wave.replace("|", ""))
    if isinstance(wave, list) and wave and wave[0] == "pw":
        # path 波形：从 d 字符串估算周期数（每 'q'/'l' 段约 1 周期）
        d = ""
        if len(wave) > 1 and isinstance(wave[1], dict):
            d = wave[1].get("d", "")
        if isinstance(d, list):
            return max(len(d) // 4, 1)
        return max(len(str(d)) // 8, 1)
    return 0


def _max_cycles(items: list[Any]) -> int:
    """所有信号的 wave 最大周期数（递归处理分组；去掉 `|` 分隔符）。"""
    maxc = 0
    for it in items:
        if isinstance(it, list):
            maxc = max(maxc, _max_cycles(it))
        elif isinstance(it, dict):
            maxc = max(maxc, _wave_len(it.get("wave")))
    return maxc


def _gen_clock_wave(cycles: int, polarity: str = "positive",
                    edge_marker: bool = True) -> str:
    """按周期数生成时钟 wave。

    WaveDrom 中时钟字符 p/P/n/N 每个代表一个**完整方波周期**（内部
    高半拍+低半拍），`.` 会延续该方波。因此 N 周期时钟 =
    `P` + `.`×(N-1)（正极性带沿标记）/ `p....`（无标记）。
    负极性用 `N`/`n` 开头。
    """
    if cycles <= 0:
        return ""
    first = "P" if edge_marker else "p"
    if polarity == "negative":
        first = "N" if edge_marker else "n"
    return first + "." * (cycles - 1)


def _apply_groups_decl(raw: list[Any], groups_decl: list[dict[str, Any]]) -> list[Any]:
    """把顶层 `groups` 声明聚合到内联嵌套数组结构（官方语法）。

    仅当 signals 为纯 lane 字典且声明了 groups 时生效；否则原样返回。
    """
    if not groups_decl:
        return raw
    # 仅处理"全为 lane dict"的平坦列表
    if any(not isinstance(it, dict) for it in raw):
        return raw
    name_to_sig: dict[str, dict[str, Any]] = {}
    for s in raw:
        nm = s.get("name")
        if nm:
            name_to_sig[str(nm)] = s
    result: list[Any] = []
    used: set[str] = set()
    for g in groups_decl:
        gname = g.get("name")
        group_items: list[dict[str, Any]] = []
        for sname in g.get("signals", []) or []:
            if sname in name_to_sig:
                group_items.append(name_to_sig[sname])
                used.add(sname)
        if group_items:
            result.append([gname] + group_items)
    # 未分组的信号保持原序追加
    for s in raw:
        if s.get("name") and str(s["name"]) not in used:
            result.append(s)
    return result


def _transform_lane(entry: dict[str, Any]) -> dict[str, Any]:
    """把模型 lane 转换为 WaveJSON lane。

    透传：name/wave（含 ['pw',{d:...}] path）/data/node/period/phase/over/under。
    """
    lane: dict[str, Any] = {"name": entry.get("name"), "wave": entry.get("wave")}
    for key in ("data", "node", "over", "under"):
        if entry.get(key) is not None:
            lane[key] = entry[key]
    if entry.get("period"):
        lane["period"] = entry["period"]
    if entry.get("phase") is not None:
        lane["phase"] = entry["phase"]
    return lane


def _transform_items(items: list[Any]) -> list[Any]:
    """递归转换信号列表，保留 WaveDrom 嵌套分组数组结构。"""
    out: list[Any] = []
    for it in items:
        if isinstance(it, list):
            # 分组数组：['组名', ...]；首元素为组名
            head = it[0] if it and isinstance(it[0], str) else None
            children = _transform_items(it[1:] if head is not None else it)
            if head is not None:
                out.append([head] + children)
            else:
                out.extend(children)
        elif isinstance(it, dict):
            if it:
                out.append(_transform_lane(it))
            else:
                # 空 lane（spacer/分隔）
                out.append({})
        else:
            out.append(it)
    return out


def _to_wavejson(behavior: dict[str, Any]) -> dict[str, Any]:
    clock = behavior.get("clock") or {}
    period = clock.get("period") or ""
    phase = clock.get("phase") or ""
    clock_display = clock.get("display", True)
    head: dict[str, Any] = {}
    if period:
        head["tick"] = period
    if phase:
        head["phase"] = phase

    raw_signals = behavior.get("signals", []) or []
    # 顶层 groups 声明聚合（若使用）
    signals = _apply_groups_decl(raw_signals, behavior.get("groups", []) or [])
    max_cycles = _max_cycles(signals)

    # 时钟 lane：显式 clock.wave 或自动生成；display=False 时只进 head
    clock_lane: dict[str, Any] | None = None
    if clock.get("name") and clock_display:
        cwave = clock.get("wave")
        if not cwave and max_cycles > 0:
            cwave = _gen_clock_wave(
                max_cycles,
                polarity=clock.get("polarity", "positive"),
                edge_marker=clock.get("edge_marker", True),
            )
        if cwave:
            clock_lane = {"name": clock.get("name"), "wave": cwave}
            if clock.get("phase") is not None:
                clock_lane["phase"] = clock["phase"]

    signals_out: list[Any] = []
    if clock_lane is not None:
        signals_out.append(clock_lane)
    signals_out.extend(_transform_items(signals))

    wavejson: dict[str, Any] = {}
    if head:
        wavejson["head"] = head
    wavejson["signal"] = signals_out

    # 用户自定义 head/foot（覆盖自动 head 的 tick/phase）
    for key in ("head", "foot"):
        custom = behavior.get(key)
        if custom:
            merged = dict(wavejson.get(key, {}))
            # 自动 tick/phase 保留，除非用户显式覆盖
            for k, v in custom.items():
                if k == "text":
                    merged["text"] = v
                else:
                    merged[k] = v
            wavejson[key] = merged

    # config
    config = behavior.get("config") or {}
    if config:
        wavejson["config"] = {k: v for k, v in config.items() if v is not None}

    # markers
    markers = behavior.get("markers")
    if markers:
        wavejson["marker"] = markers

    # edges（箭头）
    edges = behavior.get("edges")
    if edges:
        wavejson["edge"] = edges

    # gaps（Gap 表达式，如 '1.1s.1'、'(. |.. )'）
    gaps = behavior.get("gaps")
    if gaps:
        wavejson["gaps"] = gaps

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
