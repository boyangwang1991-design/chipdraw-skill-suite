"""Golden 测试：5 个 Golden Case（建设方案 §11.2）的固定输入产出固定结构。

- 固定输入与归一化模型、DOT/WaveJSON/Draw.io 结构比较
- 验收：ERROR=0、关键产物存在、结构稳定
"""
import json
import os

from chipdiagram import pipeline
from chipdiagram.issues import count_by_severity

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "examples")

GOLDEN_CASES = [
    ("pic-subsystem/pic.yaml", {"view": "soc_overview"}, ["drawio"]),
    ("axi-width-converter/x2x.yaml", {"view": "datapath"}, ["drawio"]),
    ("dma-fsm/dma_fsm.yaml", {"view": "fsm"}, ["drawio"]),
    ("apb-timing/apb_timing.yaml", {"view": "timing"}, ["drawio"]),
    ("cmos-inverter/cmos_inverter.yaml", {"view": "schematic_engineering"}, ["drawio"]),
]


def _run_golden(tmp_path, rel, request, formats):
    model_path = os.path.join(EXAMPLES, rel)
    out = str(tmp_path / "out")
    result = pipeline.run_pipeline(
        [model_path], request=request, formats=formats,
        out_dir=out, allow_draft=True,
    )
    return result


def test_all_golden_cases_pass(tmp_path):
    """Golden Case 必须 ERROR=0 且产出关键文件。"""
    for rel, request, formats in GOLDEN_CASES:
        result = _run_golden(tmp_path, rel, request, formats)
        counts = count_by_severity(result.issues)
        assert counts["ERROR"] == 0, f"{rel} 不应有 ERROR: {counts}"
        assert len(result.artifacts) >= 1, f"{rel} 应产出至少 1 个文件"
        # 产物文件应存在
        for art in result.artifacts:
            assert os.path.isfile(art["path"]), f"{rel} 产物缺失: {art['path']}"


def test_golden_expected_artifacts(tmp_path):
    """各 Golden Case 应产出特定后端产物。"""
    expectations = {
        "dma-fsm/dma_fsm.yaml": ["diagram.dot", "diagram.drawio"],
        "apb-timing/apb_timing.yaml": ["diagram.wave.json"],
        "cmos-inverter/cmos_inverter.yaml": ["diagram.spice", "erc.md"],
    }
    for rel, request, formats in GOLDEN_CASES:
        if rel not in expectations:
            continue
        result = _run_golden(tmp_path, rel, request, formats)
        produced = {os.path.basename(a["path"]) for a in result.artifacts}
        for expected in expectations[rel]:
            assert expected in produced, f"{rel} 应产出 {expected}，实际 {produced}"


def test_manifest_and_validation_emitted(tmp_path):
    """每个视图应产出 manifest 与 validation 报告（建设方案 §9）。"""
    for rel, request, formats in GOLDEN_CASES:
        out = str(tmp_path / "out2")
        pipeline.run_pipeline(
            [os.path.join(EXAMPLES, rel)], request=request,
            formats=formats, out_dir=out, allow_draft=True,
        )
        assert os.path.isfile(os.path.join(out, "manifest.yaml")), f"{rel} 缺 manifest"
        assert os.path.isfile(os.path.join(out, "validation.json")), f"{rel} 缺 validation"
        # manifest 可解析
        import yaml
        with open(os.path.join(out, "manifest.yaml"), encoding="utf-8") as fh:
            manifest = yaml.safe_load(fh)
        assert manifest["diagram_id"]
