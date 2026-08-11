"""主题加载与解析。

对齐上游 drawio-skill 的 preset 结构（styles/schema.json）：
    palette.primary/secondary/success/warning/accent/danger/neutral → {fillColor, strokeColor}
    roles.{role} → palette slot 名
    shapes.{role} → draw.io style 关键字
    font.{fontFamily,fontSize,...}
    edges.{style,arrow,dashedFor}
    extras.{sketch,globalStrokeWidth}

本仓内置 AIXSILICON 明暗主题位于 assets/libraries/themes/aixsilicon-{light,dark}.yaml，
同时兼容上游 chipdiagram/styles/built-in/*.json 作为降级基线。
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# 仓库根：chipdiagram/ 的上一级
# 仓库根：chipdiagram/ 的上一级
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 主题库位于 assets/libraries/themes（套件根下）
LIBRARY_THEMES = os.path.join(REPO_ROOT, "assets", "libraries", "themes")
BUILTIN_STYLES = os.path.join(os.path.dirname(__file__), "styles", "built-in")


class ThemeError(Exception):
    pass


def load_theme(name: str) -> dict[str, Any]:
    """按名称加载主题（YAML 或 JSON），失败时回退到默认主题并记录。"""
    for path in _candidate_paths(name):
        if os.path.isfile(path):
            return _load_file(path)
    raise ThemeError(f"未找到主题 {name!r}，可用内置主题：{list_theme_names()}")


def _candidate_paths(name: str) -> list[str]:
    lower = name.lower()
    return [
        os.path.join(LIBRARY_THEMES, f"{lower}.yaml"),
        os.path.join(LIBRARY_THEMES, f"{lower}.yml"),
        os.path.join(LIBRARY_THEMES, f"{lower}.json"),
        os.path.join(BUILTIN_STYLES, f"{lower}.json"),
    ]


def _load_file(path: str) -> dict[str, Any]:
    if path.endswith((".yaml", ".yml")):
        if yaml is None:
            raise ThemeError("缺少 PyYAML 依赖")
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def list_theme_names() -> list[str]:
    """列出可用主题名（libraries/themes + styles/built-in）。"""
    names: set[str] = set()
    for d in (LIBRARY_THEMES, BUILTIN_STYLES):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith((".yaml", ".yml", ".json")) and f != "schema.json":
                names.add(os.path.splitext(f)[0])
    return sorted(names)


def resolve_role_color(theme: dict[str, Any], role: str) -> dict[str, str]:
    """根据 role 解析 {fillColor, strokeColor}。找不到回退 neutral/primary。"""
    palette = theme.get("palette") or {}
    roles = theme.get("roles") or {}
    slot = roles.get(role) or (role if role in palette else "neutral")
    color = palette.get(slot) or palette.get("neutral") or {"fillColor": "#f5f5f5", "strokeColor": "#666666"}
    return {"fillColor": color.get("fillColor", "#f5f5f5"), "strokeColor": color.get("strokeColor", "#666666")}


def resolve_role_shape(theme: dict[str, Any], role: str) -> str:
    """根据 role 解析 draw.io style 关键字。"""
    shapes = theme.get("shapes") or {}
    return shapes.get(role, "rounded=1")


def edge_style(theme: dict[str, Any], kind: str = "default") -> str:
    """解析边样式。kind 可扩展芯片语义（datapath/control/clock/reset/interrupt/...）。"""
    edges = theme.get("edges") or {}
    base = edges.get("style", "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1")
    arrow = edges.get("arrow", "endArrow=classic;endFill=1")
    chip = (edges.get("chip") or {}).get(kind)
    if chip:
        return f"{base};{chip};{arrow}"
    return f"{base};{arrow}"


def font_style(theme: dict[str, Any]) -> str:
    font = theme.get("font") or {}
    parts = []
    if font.get("fontFamily"):
        parts.append(f"fontFamily={font['fontFamily']}")
    if font.get("fontSize"):
        parts.append(f"fontSize={font['fontSize']}")
    if font.get("titleBold"):
        parts.append("fontStyle=1")
    return ";".join(parts)
