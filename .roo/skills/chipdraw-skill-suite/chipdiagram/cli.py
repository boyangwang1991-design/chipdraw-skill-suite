"""chipdiagram 命令行入口（建设方案 §8）。

用法：
    chipdiagram build integration/pic.yaml --view interrupt_network --format drawio,svg,png --out docs/diagrams/pic
    chipdiagram extract rtl/pic_top.sv --type ip --top pic_top --out build/diagram-model/pic.yaml
    chipdiagram build specs/dma_fsm.yaml --view fsm --out docs/diagrams/dma-fsm
    chipdiagram validate integration/soc.yaml --profile soc-signoff
    chipdiagram diff old/manifest.yaml new/manifest.yaml --out reports/diagram-diff
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Optional

from . import pipeline
from .adapters.registry import extract_input
from .issues import count_by_severity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chipdiagram",
        description="芯片研发智能绘图 Skill Suite 命令行工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="从结构化模型生成图形")
    p_build.add_argument("input", nargs="+", help="输入模型文件（YAML/JSON，可多个）")
    p_build.add_argument("--view", default=None, help="视图名（如 interrupt_network、fsm、timing）")
    p_build.add_argument("--subtype", default=None, help="视图 subtype")
    p_build.add_argument("--format", default="drawio,svg,png", help="输出格式，逗号分隔")
    p_build.add_argument("--out", default=".", help="输出目录")
    p_build.add_argument("--profile", default="default", help="校验 profile")
    p_build.add_argument("--allow-draft", action="store_true", default=True, help="允许带 WARNING 输出草稿")
    p_build.set_defaults(func=_cmd_build)

    p_extract = sub.add_parser("extract", help="从输入源抽取语义模型")
    p_extract.add_argument("input", help="输入文件（Markdown/FuseSoC/SystemVerilog/SystemRDL/IP-XACT/SPICE/Draw.io）")
    p_extract.add_argument("--type", default=None, help="模型类型（ip/rtl_behavior 等，供 SystemVerilog 使用）")
    p_extract.add_argument("--top", default=None, help="顶层模块名")
    p_extract.add_argument("--out", default="-", help="输出 YAML 路径（默认 stdout）")
    p_extract.set_defaults(func=_cmd_extract)

    p_validate = sub.add_parser("validate", help="校验但不生成")
    p_validate.add_argument("input", help="输入模型文件")
    p_validate.add_argument("--profile", default="default", help="校验 profile")
    p_validate.add_argument("--json", action="store_true", help="输出 JSON")
    p_validate.set_defaults(func=_cmd_validate)

    p_diff = sub.add_parser("diff", help="比较两个版本")
    p_diff.add_argument("old", help="旧版本（模型 YAML 或 manifest）")
    p_diff.add_argument("new", help="新版本")
    p_diff.add_argument("--out", default="reports/diagram-diff", help="输出目录")
    p_diff.set_defaults(func=_cmd_diff)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows 控制台默认 cp1252 无法输出中文，统一改为 UTF-8
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        print(f"错误: {exc}", file=sys.stderr)
        return 2


def _cmd_build(args: argparse.Namespace) -> int:
    request = None
    if args.view:
        request = {"view": args.view}
        if args.subtype:
            request["subtype"] = args.subtype

    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    result = pipeline.run_pipeline(
        list(args.input), request=request, formats=formats,
        out_dir=args.out, profile=args.profile, allow_draft=args.allow_draft,
    )

    counts = count_by_severity(result.issues)
    print(f"Diagram: {result.model['diagram']['id']}")
    print(f"视图数: {len(result.selections)}  产物数: {len(result.artifacts)}")
    print(f"质量: ERROR={counts['ERROR']} WARNING={counts['WARNING']} INFO={counts['INFO']}")
    for art in result.artifacts:
        print(f"  产物: {art.get('path')} ({art.get('format')})")
    if result.blocked:
        print("⛔ 存在 ERROR，正式发布被阻断（可用 --allow-draft 查看草稿）")
        return 1
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    kwargs: dict[str, Any] = {}
    if args.type:
        kwargs["type"] = args.type
    if args.top:
        kwargs["top"] = args.top
    model = extract_input(args.input, **kwargs)
    from .model import dump_yaml, normalize_model
    normalized = normalize_model(model, source_path=args.input)

    if args.out == "-":
        try:
            import yaml
            print(yaml.safe_dump(_strip_internal(normalized), allow_unicode=True, sort_keys=False))
        except ImportError:
            print(json.dumps(_strip_internal(normalized), ensure_ascii=False, indent=2))
    else:
        dump_yaml(normalized, args.out)
        print(f"已写入: {args.out}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    from .model import load_model
    model = load_model(args.input)
    issues = pipeline.validate(model, args.profile)
    counts = count_by_severity(issues)
    if args.json:
        print(json.dumps({
            "diagram_id": model["diagram"]["id"],
            "quality": counts,
            "issues": [i.to_dict() for i in issues],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"校验 {model['diagram']['id']}: ERROR={counts['ERROR']} WARNING={counts['WARNING']} INFO={counts['INFO']}")
        for i in issues:
            if i.severity in ("ERROR", "WARNING"):
                print(f"  [{i.severity}] {i.code} {i.message}")
    return 1 if counts["ERROR"] else 0


def _cmd_diff(args: argparse.Namespace) -> int:
    """比较两个模型/Manifest：调用上游 drawiodiff.py 或模型级 diff。"""
    if args.old.endswith(".drawio") and args.new.endswith(".drawio"):
        return _drawio_diff(args)
    return _model_diff(args)


def _drawio_diff(args: argparse.Namespace) -> int:
    """用上游 drawiodiff.py 比较两个 .drawio。"""
    script = os.path.join(os.path.dirname(__file__), "engines", "shared", "drawiodiff.py")
    if not os.path.isfile(script):
        print("缺少 drawiodiff.py 共享脚本", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    diff_json = os.path.join(args.out, "diff.json")
    try:
        proc = subprocess.run(
            [sys.executable, script, args.old, args.new, "-o", diff_json],
            capture_output=True, text=True, timeout=120)
    except Exception as exc:  # noqa: BLE001
        print(f"diff 失败: {exc}", file=sys.stderr)
        return 2
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    print(f"差异已写入: {diff_json}")
    return 0


def _model_diff(args: argparse.Namespace) -> int:
    """模型级差异比较（对象增删改）。"""
    from .model import load_model
    old = load_model(args.old)
    new = load_model(args.new)
    changes = _compare_models(old, new)
    os.makedirs(args.out, exist_ok=True)
    report = os.path.join(args.out, "diff.md")
    with open(report, "w", encoding="utf-8") as fh:
        fh.write(f"# 图形差异：{old['diagram']['id']} → {new['diagram']['id']}\n\n")
        for kind, msgs in changes.items():
            fh.write(f"## {kind} ({len(msgs)})\n\n")
            for m in msgs:
                fh.write(f"- {m}\n")
            fh.write("\n")
    print(f"差异报告已写入: {report}")
    for kind, msgs in changes.items():
        print(f"  {kind}: {len(msgs)}")
    return 0


def _compare_models(old: dict[str, Any], new: dict[str, Any]) -> dict[str, list[str]]:
    """比较两个模型的块/连接集合差异（按 id）。"""
    changes: dict[str, list[str]] = {"新增块": [], "移除块": [], "新增连接": [], "移除连接": []}
    old_blocks = _block_ids(old)
    new_blocks = _block_ids(new)
    changes["新增块"] = [f"`{b}`" for b in new_blocks - old_blocks]
    changes["移除块"] = [f"`{b}`" for b in old_blocks - new_blocks]
    old_conns = _conn_ids(old)
    new_conns = _conn_ids(new)
    changes["新增连接"] = [f"`{c}`" for c in new_conns - old_conns]
    changes["移除连接"] = [f"`{c}`" for c in old_conns - new_conns]
    return {k: v for k, v in changes.items() if v}


def _block_ids(model: dict[str, Any]) -> set[str]:
    node_key = _node_key(model)
    node = model.get(node_key) or {}
    ids: set[str] = set()
    for array_key in ("instances", "modules", "states", "devices"):
        for e in node.get(array_key, []) or []:
            if isinstance(e, dict) and e.get("id"):
                ids.add(str(e["id"]))
    return ids


def _conn_ids(model: dict[str, Any]) -> set[str]:
    node_key = _node_key(model)
    node = model.get(node_key) or {}
    ids: set[str] = set()
    for e in node.get("connections", []) or []:
        if isinstance(e, dict):
            ids.add(f"{e.get('from')}->{e.get('to')}")
    return ids


def _node_key(model: dict[str, Any]) -> str:
    return {
        "soc_architecture": "soc",
        "ip_architecture": "ip",
        "rtl_behavior": "behavior",
        "transistor_schematic": "circuit",
    }[model["diagram"]["type"]]


def _strip_internal(model: dict[str, Any]) -> dict[str, Any]:
    import copy
    out = copy.deepcopy(model)
    out.pop("_index", None)
    out.pop("_model_hash", None)
    return out


if __name__ == "__main__":
    sys.exit(main())
