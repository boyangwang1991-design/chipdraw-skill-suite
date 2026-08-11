"""集成测试：输入适配器 → 校验 → 渲染 → Manifest 端到端流水线。"""
import os

from chipdiagram import pipeline
from chipdiagram.adapters.registry import extract_input
from chipdiagram.model import normalize_model
from chipdiagram.issues import count_by_severity

# 示例位于 assets/examples（套件根下）
EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "examples")


def test_pipeline_from_yaml_ssot(tmp_path):
    """从 YAML SSOT 运行完整流水线。"""
    model_path = os.path.join(EXAMPLES, "pic-subsystem", "pic.yaml")
    assert os.path.isfile(model_path), f"模型文件不存在: {model_path} (EXAMPLES={EXAMPLES})"
    out = str(tmp_path / "out")
    result = pipeline.run_pipeline(
        [model_path], request={"view": "soc_overview"},
        formats=["drawio"], out_dir=out, allow_draft=True,
    )
    assert result.model["diagram"]["id"] == "pic-subsystem"
    errs = [(i.code, i.message) for i in result.issues if i.severity == "ERROR"]
    assert errs == [], f"PIC 不应有 ERROR: {errs}"
    assert any(a["format"] == "drawio" for a in result.artifacts)


def test_extract_then_build(tmp_path):
    """抽取（markdown）→ 归一化 → 校验 的链路。"""
    md = tmp_path / "spec.md"
    md.write_text(
        "# SoC Spec\n\n"
        "| Block | Type | Connect |\n"
        "|-------|------|---------|\n"
        "| CPU | cpu | Memory |\n"
        "| Memory | memory | |\n",
        encoding="utf-8",
    )
    model = extract_input(str(md), diagram_type="soc_architecture")
    normalized = normalize_model(model, source_path=str(md))
    issues = pipeline.validate(normalized, "default")
    # 推断对象应被记录为 INFO（COMMON_TRACE_INFERRED）
    assert any(i.code == "COMMON_TRACE_INFERRED" for i in issues)


def test_validate_blocks_bad_model(tmp_path):
    """含 ERROR 的模型应阻断（blocked=True）。"""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: '1.0'\n"
        "diagram: {id: bad, type: soc_architecture, title: Bad}\n"
        "provenance: {generator: chip-design-diagram-suite}\n"
        "soc:\n"
        "  instances: [{id: a, name: A, kind: cpu}]\n"
        "  connections: [{id: c, from: a, to: ghost, kind: bus}]\n",
        encoding="utf-8",
    )
    result = pipeline.run_pipeline(
        [str(bad)], formats=["drawio"], out_dir=str(tmp_path / "o"),
        allow_draft=False,
    )
    assert result.blocked
    assert any(i.code == "COMMON_ENDPOINT_MISSING" for i in result.issues)


def test_adapter_registry(tmp_path):
    """适配器注册表能识别各输入类型。"""
    from chipdiagram.adapters.registry import adapter_for
    assert adapter_for("x.md").name == "markdown"
    assert adapter_for("x.core").name == "fusesoc"
    assert adapter_for("x.sv").name == "systemverilog"
    assert adapter_for("x.rdl").name == "systemrdl"
    assert adapter_for("x.sp").name == "spice"
    # drawio 适配器需读文件内容判断
    d = tmp_path / "x.drawio"
    d.write_text(
        '<mxfile><diagram name="p"><mxGraphModel><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '</root></mxGraphModel></diagram></mxfile>',
        encoding="utf-8",
    )
    assert adapter_for(str(d)).name == "drawio"
