"""SystemVerilog 适配器（建设方案 §5）。

提取 module、port、instance、parameter、enum FSM。
复杂 generate/interface 需分阶段支持，无法解析的项保留原文并标为未解析。

输出两种模型之一（由 --type 决定）：
- ip：IP/微架构模型（module/ports/instances）
- rtl_behavior：行为模型（enum FSM）
"""
from __future__ import annotations

import os
import re
from typing import Any

from .base import BaseAdapter, AdapterError, load_file_text


class SystemVerilogAdapter(BaseAdapter):
    name = "systemverilog"
    input_extensions = (".sv", ".svh", ".v", ".vh")

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        text = load_file_text(path)
        kind = kwargs.get("type") or "ip"
        name = os.path.splitext(os.path.basename(path))[0]

        if kind == "rtl_behavior":
            return self._extract_behavior(path, text, name)
        return self._extract_ip(path, text, name)

    def _extract_ip(self, path: str, text: str, name: str) -> dict[str, Any]:
        env = self._envelope(name, "ip_architecture", name, path, "ip")
        modules, ports, instances = _parse_ip(text)
        if modules:
            env["diagram"]["id"] = _slug(modules[0])
        env["ip"] = {
            "modules": [{"id": _slug(m), "name": m, "kind": "other"} for m in modules],
            "ports": ports,
            "rtl_bindings": [{"id": f"rb_{_slug(m)}", "module": m, "rtl_path": path,
                              "top": i == 0} for i, m in enumerate(modules)],
        }
        if instances:
            env["ip"]["modules"].extend(
                {"id": _slug(inst), "name": inst, "kind": "other"} for inst in instances
                if _slug(inst) not in {m["id"] for m in env["ip"]["modules"]})
        return env

    def _extract_behavior(self, path: str, text: str, name: str) -> dict[str, Any]:
        env = self._envelope(name, "rtl_behavior", f"{name} FSM", path, "behavior")
        states, transitions = _parse_fsm(text)
        env["diagram"]["subtype"] = "fsm"
        env["behavior"] = {
            "initial_state": states[0] if states else "",
            "states": [{"id": _slug(s), "category": "normal"} for s in states],
            "transitions": transitions,
        }
        return env


def _parse_ip(text: str) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """提取模块、端口、实例。简化解析：处理无 generate 的常见形式。"""
    modules: list[str] = []
    ports: list[dict[str, Any]] = []
    instances: list[str] = []

    # module 声明（含参数）
    for m in re.finditer(r"\bmodule\s+(\w+)", text):
        modules.append(m.group(1))

    # 端口：module ( input logic [7:0] a, output wire y, ... )
    for m in re.finditer(
        r"\b(input|output|inout)\s+(?:wire|logic|reg|signed)?\s*(?:\[([0-9:]+)\])?\s*(\w+)",
        text):
        direction, width_expr, pname = m.group(1), m.group(2), m.group(3)
        width = _width_of(width_expr)
        ports.append({
            "id": _slug(pname), "name": pname, "direction": direction,
            "width": width, "kind": "data",
            "trace": {"source_refs": [{"file": "", "symbol": pname}], "confidence": "extracted"},
        })

    # 实例：modulename instname ( ... );
    for m in re.finditer(r"\b(\w+)\s+(\w+)\s*\([^;]*\)\s*;", text):
        mname, iname = m.group(1), m.group(2)
        if mname in modules or True:
            if not mname[0].isupper() and mname not in modules:
                continue
            instances.append(mname)

    # 去重
    seen_mod: set[str] = set()
    modules_u: list[str] = []
    for x in modules:
        if x not in seen_mod:
            seen_mod.add(x)
            modules_u.append(x)
    seen_p: set[str] = set()
    ports_u: list[dict[str, Any]] = []
    for p in ports:
        if p["name"] not in seen_p:
            seen_p.add(p["name"])
            ports_u.append(p)
    seen_i: set[str] = set()
    inst_u: list[str] = []
    for x in instances:
        if x not in seen_i and x not in modules_u:
            seen_i.add(x)
            inst_u.append(x)
    return modules_u, ports_u, inst_u


def _parse_fsm(text: str) -> tuple[list[str], list[dict[str, Any]]]:
    """提取 enum 状态与 case 分支（简化）。"""
    states: list[str] = []
    transitions: list[dict[str, Any]] = []

    for m in re.finditer(r"typedef\s+enum\s*\w*\s*\{([^}]+)\}", text):
        for s in m.group(1).split(","):
            s = s.split("=")[0].strip()
            if s and s.startswith("IDLE"):
                states.insert(0, s)
            elif s:
                states.append(s)
    # 保序去重
    seen: set[str] = set()
    states = [s for s in states if not (s in seen or seen.add(s))]

    # case 分支 → transition
    for m in re.finditer(r"case\s*\(\s*(\w+)\s*\)(.*?)endcase", text, re.S):
        body = m.group(2)
        for sm in re.finditer(r"(\w+)\s*:\s*begin(.*?)end", body, re.S):
            st = sm.group(1)
            action = " ".join(sm.group(2).split())[:80]
            transitions.append({
                "from": st, "to": st, "condition": f"state=={st}",
                "action": action, "source": "rtl",
            })
    return states, transitions


def _width_of(expr: str | None) -> int:
    if not expr:
        return 1
    m = re.match(r"(\d+)\s*:\s*(\d+)", expr)
    if m:
        return abs(int(m.group(1)) - int(m.group(2))) + 1
    return 1


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_") or "obj"
