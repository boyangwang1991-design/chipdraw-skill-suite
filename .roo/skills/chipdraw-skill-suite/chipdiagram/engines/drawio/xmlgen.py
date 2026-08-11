# Draw.io XML generation basics (aligned with upstream xml-authoring.md).
#
# Rules:
# - id=0 and id=1 are required root cells; user shapes start at id=2
# - every vertex has vertex=1 parent=1 (or container id)
# - all text uses html=1
# - escape attributes; use &#xa; for newlines
# - every edge must contain mxGeometry relative=1 (self-closing invalid)
from __future__ import annotations

from xml.sax.saxutils import escape

RESERVED = "0", "1"

# common escape mapping (built via chr to avoid tool escaping)
_ESCAPE_MAP = {"<": "&lt;", ">": "&gt;", "\"": "&quot;", "\n": "&#xa;"}


class DrawioBuilder:
    def __init__(self, page_name="Page-1", host="drawio", version="26.0.0"):
        self.page_name = page_name
        self.host = host
        self.version = version
        self._cells = []
        self._next_id = 2
        self._used_set = set(RESERVED)

    def _alloc_id(self, hint=""):
        if hint and hint not in RESERVED and hint not in self._used_set:
            self._used_set.add(hint)
            return hint
        while str(self._next_id) in self._used_set:
            self._next_id += 1
        cid = str(self._next_id)
        self._next_id += 1
        self._used_set.add(cid)
        return cid

    def add_vertex(self, cell_id, value, x, y, width, height, style, parent="1"):
        cid = self._alloc_id(cell_id)
        value = escape(value, _ESCAPE_MAP)
        cell = ("<mxCell id=\"{}\" value=\"{}\" style=\"{}\" vertex=\"1\" parent=\"{}\">"
            + "<mxGeometry x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" as=\"geometry\" />"
            + "</mxCell>").format(cid, value, style, parent, x, y, width, height)
        self._cells.append(cell)

    def add_edge(self, cell_id, source, target, label, style, parent="1", exit_xy=None, entry_xy=None):
        cid = self._alloc_id(cell_id)
        label = escape(label, _ESCAPE_MAP)
        style_parts = [style]
        if exit_xy:
            style_parts.append("exitX={};exitY={};exitDx=0;exitDy=0;".format(*exit_xy))
        if entry_xy:
            style_parts.append("entryX={};entryY={};entryDx=0;entryDy=0;".format(*entry_xy))
        cell = ("<mxCell id=\"{}\" value=\"{}\" style=\"{}\" edge=\"1\" parent=\"{}\" source=\"{}\" target=\"{}\">"
            + "<mxGeometry relative=\"1\" as=\"geometry\" />"
            + "</mxCell>").format(cid, label, chr(59).join(style_parts), parent, source, target)
        self._cells.append(cell)

    def add_container(self, cell_id, value, x, y, width, height, style, parent="1"):
        cid = self._alloc_id(cell_id)
        value = escape(value, _ESCAPE_MAP)
        cell = ("<mxCell id=\"{}\" value=\"{}\" style=\"{}\" vertex=\"1\" parent=\"{}\">"
            + "<mxGeometry x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" as=\"geometry\" />"
            + "</mxCell>").format(cid, value, style, parent, x, y, width, height)
        self._cells.append(cell)
        return cid

    def to_xml(self, extra_diagram_attrs=""):
        cells = "\n  ".join(self._cells)
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            + "<mxfile host=\"{}\" version=\"{}\">\n"
            + "  <diagram name=\"{}\" id=\"{}\">\n"
            + "    <mxGraphModel>\n"
            + "      <root>\n"
            + "        <mxCell id=\"0\" />\n"
            + "        <mxCell id=\"1\" parent=\"0\" />\n"
            + "  {}\n"
            + "      </root>\n"
            + "    </mxGraphModel>\n"
            + "  </diagram>\n"
            + "</mxfile>\n"
        ).format(self.host, self.version, self.page_name, self.page_name, cells)

    def write(self, path):
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_xml())

# common style constants
STYLE_CONTAINER = "swimlane;startSize=30;html=1;"
STYLE_GROUP = "rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#999999;verticalAlign=top;fontStyle=2;dashed=1;"
STYLE_BLOCK = "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
STYLE_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
STYLE_EDGE_DATAPATH = STYLE_EDGE + "strokeColor=#1e77b4;strokeWidth=3;"
STYLE_EDGE_CONTROL = STYLE_EDGE + "strokeColor=#7b3fa0;strokeWidth=1;"
STYLE_EDGE_CLOCK = STYLE_EDGE + "strokeColor=#2e8b57;dashed=1;"
STYLE_EDGE_RESET = STYLE_EDGE + "strokeColor=#808080;dashed=1;"
STYLE_EDGE_INTERRUPT = STYLE_EDGE + "strokeColor=#e07b00;"
