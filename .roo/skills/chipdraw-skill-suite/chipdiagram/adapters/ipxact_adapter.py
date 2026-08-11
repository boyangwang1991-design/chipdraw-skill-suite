"""IP-XACT 适配器（建设方案 §5）。

提取 component、busInterface、memoryMap、design → SoC/IP 模型。
IP-XACT 作为交换格式，不建议人工直接维护 XML。
"""
from __future__ import annotations

import os
import re
from typing import Any
from xml.etree import ElementTree as ET

from .base import BaseAdapter, AdapterError, load_file_text

NS = {
    "ipxact": "http://www.accellera.org/XMLSchema/IPXACT/1685-2022",
    "spirit": "http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009",
}


class IPXactAdapter(BaseAdapter):
    name = "ipxact"
    input_extensions = (".xml",)

    def accepts(self, path: str) -> bool:
        if not path.lower().endswith(self.input_extensions):
            return False
        # 只接受看起来像 IP-XACT 的文件（含 component/memoryMap 关键字）
        try:
            text = load_file_text(path)
        except AdapterError:
            return False
        return "busInterface" in text or "memoryMap" in text or "VLNV" in text

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        text = load_file_text(path)
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise AdapterError(f"IP-XACT XML 解析失败 {path}: {exc}") from exc

        name = _find_text(root, "name", "component") or os.path.splitext(os.path.basename(path))[0]
        env = self._envelope(_slug(name), "soc_architecture", name, path, "soc")

        instances, ports = _parse_component(root)
        env["diagram"]["subtype"] = "soc_overview"
        env["soc"] = {
            "instances": instances,
            "connections": _parse_design_connections(root),
        }
        if ports:
            env["soc"]["instances"][0]["ports"] = ports
        return env


def _parse_component(root: ET.Element) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    name = _find_text(root, "name", "component") or "component"
    instances = [{"id": _slug(name), "name": name, "kind": "other",
                  "trace": {"confidence": "extracted"}}]
    ports: list[dict[str, Any]] = []
    for bus in root.iter():
        if _tag(bus) != "busInterface":
            continue
        iname = _find_text(bus, "name") or ""
        role = "initiator" if _find_text(bus, "initiator") else "target"
        ports.append({
            "id": _slug(iname), "name": iname, "direction": "inout",
            "protocol": role, "kind": "interface",
            "trace": {"confidence": "extracted"},
        })
    return instances, ports


def _parse_design_connections(root: ET.Element) -> list[dict[str, Any]]:
    conns: list[dict[str, Any]] = []
    for comp in root.iter():
        if _tag(comp) != "componentInstance":
            continue
        cid = _find_text(comp, "instanceName") or _find_text(comp, "name") or ""
        for bus in comp.iter():
            if _tag(bus) != "busInterface":
                continue
            bname = _find_text(bus, "name") or ""
            conns.append({
                "id": f"c_{_slug(cid)}_{_slug(bname)}",
                "from": _slug(cid), "to": _slug(bname), "kind": "bus",
                "trace": {"confidence": "extracted"},
            })
    return conns


def _find_text(elem: ET.Element, tag: str, default: str = "") -> str:
    for child in elem.iter():
        if _tag(child) == tag and child.text and child.text.strip():
            return child.text.strip()
    return default


def _tag(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_") or "obj"
