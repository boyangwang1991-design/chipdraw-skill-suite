"""视觉/结构测试：Draw.io XML 结构校验（Gate 3/4 结构部分）。

验证生成的 .drawio XML 是 well-formed、含稳定 id、容器正确嵌套。
"""
import os
import xml.etree.ElementTree as ET

from chipdiagram.engines.drawio.xmlgen import DrawioBuilder

import pytest


def test_xml_well_formed():
    b = DrawioBuilder(page_name="test")
    b.add_vertex("v1", "CPU", 0, 0, 100, 50, "rounded=1;")
    b.add_edge("e1", "v1", "v2", "axi", "edgeStyle=orthogonalEdgeStyle;")
    xml_text = b.to_xml()
    # 必须可解析（well-formed）
    ET.fromstring(xml_text)


def test_root_cells_present():
    b = DrawioBuilder()
    xml_text = b.to_xml()
    assert '<mxCell id="0" />' in xml_text
    assert '<mxCell id="1" parent="0" />' in xml_text


def test_vertex_and_edge_structure():
    b = DrawioBuilder()
    b.add_vertex("v1", "A", 10, 20, 100, 50, "rounded=1;")
    b.add_edge("e1", "v1", "v2", "bus", "edgeStyle=orthogonalEdgeStyle;")
    xml_text = b.to_xml()
    # vertex 含 vertex=1 与几何
    assert 'vertex="1"' in xml_text
    assert '<mxGeometry x="10" y="20" width="100" height="50" as="geometry" />' in xml_text
    # edge 含 relative=1 geometry（自闭合 edge 无效，必须含该子元素）
    assert 'edge="1"' in xml_text
    assert '<mxGeometry relative="1" as="geometry" />' in xml_text


def test_container_nesting():
    b = DrawioBuilder()
    container_id = b.add_container("sub0", "Subsystem", 0, 0, 300, 200, "swimlane;")
    b.add_vertex("child0", "Child", 20, 40, 80, 40, "rounded=1;", parent=container_id)
    xml_text = b.to_xml()
    assert f'parent="{container_id}"' in xml_text


def test_id_stability():
    """同一对象 id 派生稳定 id，多次生成结构一致（建设方案 §15 兼容策略）。"""
    b1 = DrawioBuilder()
    b1.add_vertex("block_a", "A", 0, 0, 100, 50, "rounded=1;")
    b2 = DrawioBuilder()
    b2.add_vertex("block_a", "A", 0, 0, 100, 50, "rounded=1;")
    assert 'id="block_a"' in b1.to_xml()
    assert 'id="block_a"' in b2.to_xml()


def test_escape_special_chars():
    """标签含特殊字符应正确转义（建设方案 §3.4 中英文、特殊符号）。"""
    b = DrawioBuilder()
    b.add_vertex("v1", 'CPU "IRQ[0]" & <data>', 0, 0, 100, 50, "rounded=1;")
    xml_text = b.to_xml()
    # 转义实体（用 chr 构造避免工具转义）
    LT = chr(60)   # <
    GT = chr(62)   # >
    AMP = chr(38)  # &
    AMPQ = AMP + "quot;"
    assert AMPQ in xml_text
    assert (LT + "data" + GT) not in xml_text  # 未转义的 <data> 不应出现
    # 值应包含引号实体与尖括号实体的转义形式
    assert AMPQ in xml_text or (AMP + "#34;") in xml_text
    assert (AMP + "lt;data" + AMP + "gt;") in xml_text
