"""SPICE/CDL 适配器（建设方案 §5 / §3.5 Engineering Mode 权威输入）。

提取 subckt、device、net、parameter → Circuit 模型。
只提取结构（连接关系），不做仿真或尺寸优化。
"""
from __future__ import annotations

import os
import re
from typing import Any

from .base import BaseAdapter, AdapterError, load_file_text


class SpiceAdapter(BaseAdapter):
    name = "spice"
    input_extensions = (".sp", ".spi", ".cdl", ".net", ".cir")

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        text = load_file_text(path)
        name = os.path.splitext(os.path.basename(path))[0]
        env = self._envelope(name, "transistor_schematic", name, path, "circuit")

        subckts = _parse_subckts(text)
        devices, nets = _parse_devices_and_nets(text)

        env["diagram"]["subtype"] = "schematic_engineering"
        env["circuit"] = {
            "mode": "engineering",
            "devices": devices,
            "nets": nets,
            "subcircuits": subckts,
        }
        return env


def _parse_subckts(text: str) -> list[dict[str, Any]]:
    subckts: list[dict[str, Any]] = []
    for m in re.finditer(r"\.subckt\s+(\S+)\s+([^\n]*)", text, re.I):
        name = m.group(1)
        ports = m.group(2).split()
        subckts.append({"id": _slug(name), "name": name, "ports": ports,
                        "trace": {"confidence": "extracted"}})
    return subckts


def _parse_devices_and_nets(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    devices: list[dict[str, Any]] = []
    nets: list[dict[str, Any]] = []
    net_set: set[str] = set()

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("*", ".", "$", "//", "#")):
            continue
        toks = s.split()
        if len(toks) < 2:
            continue
        dev = toks[0]
        m = re.match(r"^(M|MP|MN|R|C|L|D|Q|X)(\w+)", dev, re.I)
        if not m:
            continue
        kind = m.group(1).upper()
        did = m.group(2)
        terminals = toks[1:]
        if kind in ("M", "MP", "MN"):
            dtype = "pmos" if kind in ("MP",) else ("nmos" if kind in ("MN", "M") else "nmos")
            # M<name> d g s b [model]
            dtype = "pmos" if kind == "MP" else "nmos"
            terms = {}
            for role, val in zip(("d", "g", "s", "b"), terminals[:4]):
                terms[role] = val
            devices.append({
                "id": did, "type": dtype, "terminals": terms,
                "model": terminals[4] if len(terminals) > 4 else "",
                "trace": {"confidence": "extracted"},
            })
        elif kind in ("R", "C", "L", "D"):
            dtype = {"R": "resistor", "C": "capacitor", "L": "inductor", "D": "diode"}[kind]
            terms = dict(zip(("a", "b"), terminals[:2]))
            devices.append({
                "id": did, "type": dtype, "terminals": terms,
                "parameters": _param_dict(terminals[2:]),
                "trace": {"confidence": "extracted"},
            })
        elif kind == "X":
            sub_name = toks[-1]
            terms = dict(zip(("p" + str(i) for i in range(len(terminals) - 1)), terminals[:-1]))
            devices.append({
                "id": did, "type": "subckt_instance", "model": sub_name,
                "terminals": terms,
                "trace": {"confidence": "extracted"},
            })

        # 收集网络
        for t in terminals[:4]:
            if t and t not in ("0", "gnd!", "vss!", "vdd!"):
                if t not in net_set:
                    net_set.add(t)
                    nets.append({"id": _slug(t), "name": t,
                                 "trace": {"confidence": "extracted"}})

    return devices, nets


def _param_dict(tokens: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for t in tokens:
        if "=" in t:
            k, v = t.split("=", 1)
            params[k] = v
    return params


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_") or "obj"
