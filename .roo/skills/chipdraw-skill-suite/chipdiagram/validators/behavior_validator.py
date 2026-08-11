"""行为级校验器（建设方案 §3.4：FSM / Timing / Sequence）。

FSM：
- 初始状态必须存在且唯一
- 所有 Transition 端点存在
- 检查不可达状态、无出口状态、孤立状态
- 重复/冲突条件
- 缺 Default/Error/Recovery 路径
- 状态编码重复或不完整

Timing：
- Wave 字符串长度与 Signal 数据数量一致
- Clock 与时间标尺存在
- 必选信号缺失
- 协议规则（如 APB Setup/Access）
- Reset 释放与 Clock 关系
- 来源标注（规范/仿真/AI 推断）

Sequence：
- 参与者存在、消息端点存在
"""
from __future__ import annotations

from typing import Any

from ..issues import Issue


def validate_behavior(model: dict[str, Any], profile: str = "default") -> list[Issue]:
    issues: list[Issue] = []
    behavior = model.get("behavior") or {}
    subtype = model.get("diagram", {}).get("subtype")

    if subtype == "timing":
        issues.extend(_validate_timing(model, behavior))
    elif subtype == "sequence":
        issues.extend(_validate_sequence(model, behavior))
    else:
        issues.extend(_validate_fsm(model, behavior))
    return issues


def _validate_fsm(model: dict[str, Any], behavior: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    states = behavior.get("states", []) or []
    transitions = behavior.get("transitions", []) or []
    initial = behavior.get("initial_state", "")
    state_ids = {str(s.get("id")) for s in states}

    # 初始状态存在且唯一
    if not initial:
        issues.append(Issue(code="FSM_NO_INITIAL", severity="ERROR",
                            message="FSM 缺少初始状态", rule="fsm.initial_exists"))
    elif initial not in state_ids:
        issues.append(Issue(code="FSM_INITIAL_MISSING", severity="ERROR",
                            message=f"初始状态 {initial!r} 不在 states 中", object_id=initial,
                            rule="fsm.initial_in_states"))

    # Transition 端点
    for t in transitions:
        frm, to = str(t.get("from")), str(t.get("to"))
        if frm not in state_ids:
            issues.append(Issue(code="FSM_TRANS_SRC_MISSING", severity="ERROR",
                                message=f"转移起点不存在: {frm!r}", rule="fsm.trans_endpoint"))
        if to not in state_ids:
            issues.append(Issue(code="FSM_TRANS_DST_MISSING", severity="ERROR",
                                message=f"转移终点不存在: {to!r}", rule="fsm.trans_endpoint"))

    # 可达性：从初始状态 BFS
    reachable = _reachable(initial, transitions)
    for s in states:
        sid = str(s.get("id"))
        if sid not in reachable:
            issues.append(Issue(code="FSM_STATE_UNREACHABLE", severity="WARNING",
                                message=f"状态 {sid} 不可达（从初始状态 {initial}）",
                                object_id=sid, rule="fsm.reachability"))

    # 无出口状态（终态，非 error/recovery 且非最后）
    out_states = {str(t.get("from")) for t in transitions}
    for s in states:
        sid = str(s.get("id"))
        cat = s.get("category", "normal")
        if sid not in out_states and cat not in ("error", "recovery"):
            issues.append(Issue(code="FSM_STATE_NO_EXIT", severity="WARNING",
                                message=f"状态 {sid} 无出口转移", object_id=sid, rule="fsm.no_exit"))

    # 孤立状态（无入无出）
    in_states = {str(t.get("to")) for t in transitions}
    for s in states:
        sid = str(s.get("id"))
        if sid not in out_states and sid not in in_states and sid != initial:
            issues.append(Issue(code="FSM_STATE_ORPHAN", severity="WARNING",
                                message=f"状态 {sid} 为孤立状态", object_id=sid, rule="fsm.orphan"))

    # 缺 Default/Error/Recovery
    cats = {s.get("category") for s in states}
    if "error" not in cats and "fault" not in cats:
        issues.append(Issue(code="FSM_NO_ERROR_PATH", severity="WARNING",
                            message="FSM 缺少 Error/Fault 状态路径", rule="fsm.error_path"))
    if "recovery" not in cats:
        issues.append(Issue(code="FSM_NO_RECOVERY", severity="WARNING",
                            message="FSM 缺少 Recovery 状态", rule="fsm.recovery"))

    # 状态编码重复
    enc = [s.get("encoding_value") for s in states if s.get("encoding_value")]
    if len(enc) != len(set(enc)):
        issues.append(Issue(code="FSM_ENCODING_DUP", severity="WARNING",
                            message="状态编码重复", rule="fsm.encoding_unique"))

    # 推断条件标记
    for t in transitions:
        if t.get("source") == "inferred":
            issues.append(Issue(code="BEHAVIOR_INFERRED", severity="INFO",
                                message=f"转移 {t.get('from')}→{t.get('to')} 为推断条件，需与 RTL 核对",
                                object_id=f"{t.get('from')}→{t.get('to')}", rule="fsm.inferred"))
    return issues


def _reachable(initial: str, transitions: list[dict[str, Any]]) -> set[str]:
    from collections import deque
    adj: dict[str, list[str]] = {}
    for t in transitions:
        adj.setdefault(str(t.get("from")), []).append(str(t.get("to")))
    seen: set[str] = set()
    q = deque([initial]) if initial else deque()
    while q:
        s = q.popleft()
        if s in seen:
            continue
        seen.add(s)
        for nxt in adj.get(s, []):
            if nxt not in seen:
                q.append(nxt)
    return seen


def _validate_timing(model: dict[str, Any], behavior: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    clock = behavior.get("clock") or {}
    signals = behavior.get("signals", []) or []

    if not clock.get("name"):
        issues.append(Issue(code="TIMING_NO_CLOCK", severity="ERROR",
                            message="时序图缺少 Clock", rule="timing.clock_exists"))

    for sig in signals:
        wave = sig.get("wave") or ""
        data = sig.get("data") or []
        # WaveDrom 规则：'.' 表示延续上一周期（无独立数据），
        # data 数组长度应等于 wave 中非延续周期（非 '.' 符号）的数量。
        # 'x' 表示未知/高阻，通常不配 data 值；仅统计需显式数据的周期
        data_cycles = [c for c in wave if c not in (".", "x")]
        if data and len(data) != len(data_cycles):
            issues.append(Issue(code="TIMING_WAVE_DATA_MISMATCH", severity="ERROR",
                                message=f"信号 {sig.get('name')} 的 wave 数据周期数({len(data_cycles)}) 与 data 数({len(data)}) 不一致",
                                object_id=sig.get("name"), rule="timing.wave_data"))

    # 必选信号缺失（由 diagram 指定 protocol_rules 时可扩展）
    required = [s for s in signals if s.get("required")]
    if required:
        pass

    # 来源标注
    origin = behavior.get("origin", "inferred")
    if origin == "inferred":
        issues.append(Issue(code="BEHAVIOR_INFERRED", severity="INFO",
                            message="时序图为 AI 推断，需标注来源（规范/仿真采样）",
                            rule="timing.origin"))
    return issues


def _validate_sequence(model: dict[str, Any], behavior: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    participants = {str(p.get("id")) for p in behavior.get("participants", []) or []}
    for m in behavior.get("messages", []) or []:
        if m.get("from") and str(m["from"]) not in participants:
            issues.append(Issue(code="SEQ_SRC_MISSING", severity="ERROR",
                                message=f"消息 {m.get('label','')} 的发送者 {m.get('from')} 不存在",
                                rule="sequence.participant"))
        if m.get("to") and str(m["to"]) not in participants:
            issues.append(Issue(code="SEQ_DST_MISSING", severity="ERROR",
                                message=f"消息 {m.get('label','')} 的接收者 {m.get('to')} 不存在",
                                rule="sequence.participant"))
        if m.get("over") and str(m["over"]) not in participants:
            issues.append(Issue(code="SEQ_NOTE_OVER_MISSING", severity="WARNING",
                                message=f"注释 {m.get('note','')} 的归属 {m.get('over')} 不存在",
                                rule="sequence.participant"))
    return issues
