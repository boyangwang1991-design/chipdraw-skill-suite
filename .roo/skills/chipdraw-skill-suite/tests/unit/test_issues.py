"""单元测试：Issue 模型与严重度逻辑。"""
from chipdiagram.issues import Issue, count_by_severity, block_error, sort_issues


def _i(code, severity):
    return Issue(code=code, severity=severity, message=code)


def test_issue_roundtrip():
    issue = Issue(code="TEST", severity="ERROR", message="测试", object_id="x", rule="r")
    d = issue.to_dict()
    assert d["code"] == "TEST"
    assert d["severity"] == "ERROR"
    restored = Issue.from_dict(d)
    assert restored.code == "TEST"
    assert restored.object_id == "x"


def test_count_by_severity():
    issues = [
        _i("A", "ERROR"),
        _i("B", "WARNING"),
        _i("C", "INFO"),
        _i("D", "ERROR"),
    ]
    counts = count_by_severity(issues)
    assert counts == {"ERROR": 2, "WARNING": 1, "INFO": 1}


def test_block_error():
    assert not block_error([_i("A", "WARNING")])
    assert block_error([_i("A", "ERROR")])


def test_sort_issues_order():
    issues = [
        _i("B", "INFO"),
        _i("A", "ERROR"),
        _i("C", "WARNING"),
    ]
    sorted_issues = sort_issues(issues)
    assert [i.severity for i in sorted_issues] == ["ERROR", "WARNING", "INFO"]
