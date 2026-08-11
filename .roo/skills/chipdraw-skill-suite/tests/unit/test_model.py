"""单元测试：模型加载与归一化。"""
import pytest

from chipdiagram.model import (
    ModelError,
    load_model,
    normalize_model,
    compute_model_hash,
)


def _soc_model():
    return {
        "schema_version": "1.0",
        "diagram": {"id": "test-soc", "type": "soc_architecture", "title": "T"},
        "provenance": {"generator": "chip-design-diagram-suite"},
        "soc": {
            "instances": [{"id": "cpu", "name": "CPU", "kind": "cpu"}],
            "connections": [],
        },
    }


def test_normalize_adds_defaults():
    m = normalize_model(_soc_model(), source_path="a.yaml")
    assert m["diagram"]["status"] == "draft"
    assert m["style"]["theme"] == "aixsilicon-light"
    assert m["provenance"]["sources"][0]["path"] == "a.yaml"
    assert "_index" in m
    assert "_model_hash" in m


def test_normalize_requires_node():
    bad = _soc_model()
    del bad["soc"]
    with pytest.raises(ModelError):
        normalize_model(bad)


def test_hash_stable():
    m1 = normalize_model(_soc_model())
    m2 = normalize_model(_soc_model())
    assert m1["_model_hash"] == m2["_model_hash"]


def test_load_yaml_file(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text("schema_version: '1.0'\ndiagram:\n  id: x\n  type: ip_architecture\n  title: X\nip: {}\nprovenance: {generator: chip-design-diagram-suite}\n", encoding="utf-8")
    m = load_model(str(p))
    assert m["diagram"]["id"] == "x"
