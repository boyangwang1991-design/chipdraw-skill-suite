"""校验问题（Issue）模型与严重度定义。

严重度（建设方案 §10）：
- ERROR   会导致错误事实、非法连接或不可用输出 → 阻断正式生成
- WARNING 信息不完整或存在设计风险 → 允许草稿，正式发布需处理/waiver
- INFO    建议优化布局或表达 → 不阻断
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Issue:
    """一条校验/QA 发现。

    code   机器可读的问题码（如 SOC_PORT_ENDPOINT_MISSING）
    severity  ERROR / WARNING / INFO
    message 人可读的中文描述
    path    问题所在对象路径（如 soc.instances[0].ports[1]）
    object_id 相关对象 id（如模块/端口/连接 id）
    rule    触发规则名（如 soc.endpoint_exists）
    data    附加结构数据（供测试与报告使用）
    """

    code: str
    severity: str
    message: str
    path: str = ""
    object_id: str = ""
    rule: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "object_id": self.object_id,
            "rule": self.rule,
            "data": self.data,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Issue":
        return Issue(
            code=d.get("code", ""),
            severity=d.get("severity", "INFO"),
            message=d.get("message", ""),
            path=d.get("path", ""),
            object_id=d.get("object_id", ""),
            rule=d.get("rule", ""),
            data=d.get("data", {}),
        )


SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def sort_issues(issues: list[Issue]) -> list[Issue]:
    """ERROR 在前，其次 WARNING、INFO，保持相对稳定顺序。"""
    return sorted(issues, key=lambda i: (SEVERITY_ORDER.get(i.severity, 9), i.code, i.path))


def count_by_severity(issues: list[Issue]) -> dict[str, int]:
    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for i in issues:
        if i.severity in counts:
            counts[i.severity] += 1
    return counts


def block_error(issues: list[Issue]) -> bool:
    """是否存在需要阻断正式生成的 ERROR。"""
    return any(i.severity == "ERROR" for i in issues)
