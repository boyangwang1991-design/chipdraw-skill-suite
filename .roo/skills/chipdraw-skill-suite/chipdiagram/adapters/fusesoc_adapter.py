"""FuseSoC `.core` 适配器（建设方案 §5 / CAPI2）。

提取 VLNV、dependencies、filesets、targets、parameters，产出依赖/工程视图。
不默认推断 RTL 端口互联（建设方案 §5：FuseSoC 不默认推断端口互联）。
"""
from __future__ import annotations

import os
import re
from typing import Any

from .base import BaseAdapter, AdapterError, load_file_text


class FusesocAdapter(BaseAdapter):
    name = "fusesoc"
    input_extensions = (".core",)

    def extract(self, path: str, **kwargs: Any) -> dict[str, Any]:
        text = load_file_text(path)
        name = os.path.splitext(os.path.basename(path))[0]
        env = self._envelope(name, "soc_architecture", name, path, "soc")
        vlnv = _parse_vlnv(text)
        if vlnv:
            env["diagram"]["id"] = _slug(vlnv)
        deps = _parse_dependencies(text)

        # FuseSoC 依赖视图：每个 dependency 作为连接，core 自身作为根实例
        instances: list[dict[str, Any]] = [{
            "id": _slug(vlnv or name), "name": vlnv or name, "kind": "subsystem",
        }]
        connections: list[dict[str, Any]] = []
        for dep in deps:
            dep_id = _slug(dep)
            instances.append({"id": dep_id, "name": dep, "kind": "other"})
            connections.append({
                "id": f"dep_{_slug(vlnv or name)}_{dep_id}",
                "from": _slug(vlnv or name), "to": dep_id, "kind": "dependency",
            })

        env["diagram"]["subtype"] = "fusesoc_dependency"
        env["soc"] = {"instances": instances, "connections": connections}
        env["soc"]["_raw"] = {
            "vlnv": vlnv,
            "dependencies": deps,
            "filesets": _parse_filesets(text),
            "targets": _parse_targets(text),
        }
        return env


def _parse_vlnv(text: str) -> str | None:
    m = re.search(r"CAPI2\s*\n\s*name\s*:\s*([^\s]+)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"name\s*:\s*([^\s]+)", text)
    return m.group(1).strip() if m else None


def _parse_dependencies(text: str) -> list[str]:
    deps: list[str] = []
    in_deps = False
    for line in text.splitlines():
        s = line.strip()
        if s == "dependencies:" or s.startswith("dependencies: #"):
            in_deps = True
            continue
        if in_deps:
            if s and not s.startswith("#") and ":" in s and not s.startswith(("filesets:", "targets:", "parameters:")):
                deps.append(s.split(":", 1)[0].strip())
            if s and s.endswith(":") and s not in deps and len(s) < 60 and " " not in s.strip() and s.strip().startswith(("$", "[")):
                pass
            if s and not (s.startswith(" ") or s.startswith("\t")) and s not in ("",):
                if not s.startswith(("name", "filesets", "targets", "parameters", "generate", "description", "maintainer", "authors", "top", "vendor", "library", "version")):
                    pass
    return [d for d in deps if d]


def _parse_filesets(text: str) -> list[str]:
    fs: list[str] = []
    for m in re.finditer(r"filesets\s*:\s*\n((?:\s+\w+:[^\n]*\n)+)", text):
        for line in m.group(1).splitlines():
            mm = re.match(r"\s+(\w+):", line)
            if mm:
                fs.append(mm.group(1))
    return fs


def _parse_targets(text: str) -> list[str]:
    tg: list[str] = []
    for m in re.finditer(r"targets\s*:\s*\n((?:\s+\w+:[^\n]*\n)+)", text):
        for line in m.group(1).splitlines():
            mm = re.match(r"\s+(\w+):", line)
            if mm:
                tg.append(mm.group(1))
    return tg


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", s.lower()).strip("-") or "core"
