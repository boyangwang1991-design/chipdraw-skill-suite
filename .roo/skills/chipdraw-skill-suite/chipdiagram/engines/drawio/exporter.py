"""Draw.io CLI 导出与降级（参考上游 SKILL.md 导出章节）。

关键点：
- Preview PNG 用 `--width 2000` 且不加 `-e`（否则 vision API 400）
- Final PNG 用 `-e -s 2`，随后运行 repair_png.py 修复 IEND 截断
- CLI 缺失时降级：返回 .drawio XML 即可（浏览器可打开），或用 encode_drawio_url.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Optional

SHARED_DIR = os.path.join(os.path.dirname(__file__), "..", "shared")


def find_drawio_binary() -> Optional[str]:
    """解析 draw.io CLI 二进制（平台相关）。返回可执行路径或 None。"""
    for name in ("drawio", "draw.io"):
        p = shutil.which(name)
        if p:
            return p
    if sys.platform == "darwin":
        cand = "/Applications/draw.io.app/Contents/MacOS/draw.io"
        if os.path.isfile(cand):
            return cand
    if os.name == "nt":
        cand = r"C:\Program Files\draw.io\draw.io.exe"
        if os.path.isfile(cand):
            return cand
    return None


def export_drawio(drawio_path: str, out_stem: str, formats: list[str],
                  final: bool = True) -> list[str]:
    """导出 .drawio 到 PNG/SVG/PDF。

    返回成功导出的文件路径列表。CLI 缺失时返回空（由调用方降级）。
    """
    binary = find_drawio_binary()
    if binary is None:
        return []

    os.makedirs(os.path.dirname(os.path.abspath(out_stem)), exist_ok=True)
    exported: list[str] = []
    for fmt in formats:
        out = f"{out_stem}.{fmt}"
        args = [binary, "-x", "-f", fmt, "-o", out, drawio_path]
        if fmt == "png":
            if final:
                args.extend(["-e", "-s", "2"])
            else:
                args.extend(["--width", "2000"])
        elif fmt in ("svg", "pdf") and final:
            args.append("-e")
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=180)
        except Exception:  # noqa: BLE001
            continue
        if proc.returncode != 0 or not os.path.isfile(out):
            continue
        if fmt == "png" and final:
            _repair_png(out)
        exported.append(out)
    return exported


def _repair_png(path: str) -> None:
    """运行上游 repair_png.py 修复 -e PNG 截断的 IEND chunk。"""
    script = os.path.join(SHARED_DIR, "repair_png.py")
    if not os.path.isfile(script):
        return
    try:
        subprocess.run([sys.executable, script, path], capture_output=True, timeout=60)
    except Exception:  # noqa: BLE001
        pass


def browser_url(drawio_path: str) -> Optional[str]:
    """CLI 缺失时生成 diagrams.net 查看/编辑 URL（降级方案）。"""
    script = os.path.join(SHARED_DIR, "encode_drawio_url.py")
    if not os.path.isfile(script):
        return None
    try:
        proc = subprocess.run(
            [sys.executable, script, drawio_path], capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return None
