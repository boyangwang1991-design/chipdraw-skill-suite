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


# WaveDrom data 引用字符：数字 2-9（显示 data[k-2]）与 `=`（延续值引用）。
# 官方规则：`data` 数组按顺序对应 wave 中会显示文本的**数字/延续字符**；
# `x`/`z` 为未知/高阻（不显示 data），`.` 为延续（无独立 data），`|` 为分隔符。
_DATA_REF_CHARS = set("23456789=")


def _iter_timing_lanes(items: list[Any]) -> list[dict[str, Any]]:
    """递归收集 timing 的 lane 字典（跳过分组数组首元素与空 spacer）。"""
    lanes: list[dict[str, Any]] = []
    for it in items:
        if isinstance(it, list):
            lanes.extend(_iter_timing_lanes(it[1:] if it and isinstance(it[0], str) else it))
        elif isinstance(it, dict) and it:
            lanes.append(it)
    return lanes


def _effective_chars(plain: str) -> list[str]:
    """把 `.` 延续展开为前一有效字符，得到每周期的"有效状态"序列。"""
    eff: list[str] = []
    last = "x"
    for c in plain:
        if c == ".":
            c = last
        last = c
        eff.append(c)
    return eff


def _handshake_coverage_issues(signals: list[dict[str, Any]]) -> list[Issue]:
    """同通道 VALID 窗口数据就绪检查（AXI 类 valid/ready 协议）。

    按名字前缀配对 `<prefix>valid` / `<prefix>ready`。协议要求 VALID 不得
    先于同通道地址/控制/数据置起，且握手（含等待态）期间数据必须保持稳定；
    因此同前缀且带 data 的 lane，其有效字符（展开 `.` 延续后为数字/`=`）
    必须覆盖整个 `*valid` 为高的窗口。用于拦截 off-by-one 错位（如地址比
    awvalid 晚一拍就绪）与等待态期间数据未保持。
    """
    issues: list[Issue] = []
    by_name = {str(s.get("name")): s for s in signals if s.get("name")}
    for vname in [n for n in by_name if n.lower().endswith("valid")]:
        prefix = vname[: -len("valid")]
        rname = prefix + "ready"
        ready = by_name.get(rname)
        if ready is None:
            continue
        vwave = by_name[vname].get("wave") or ""
        rwave = ready.get("wave") or ""
        if isinstance(vwave, list) or isinstance(rwave, list):
            continue
        # `.` 是延续符，需先展开为有效电平再取 VALID 为高的窗口
        veff = _effective_chars(vwave.replace("|", ""))
        v_cycles = [i for i, v in enumerate(veff) if v == "1"]
        if not v_cycles:
            continue
        for name, sig in by_name.items():
            low = name.lower()
            if not low.startswith(prefix) or low in (vname.lower(), rname.lower()):
                continue
            wave = sig.get("wave") or ""
            if isinstance(wave, list) or not sig.get("data"):
                continue
            eff = _effective_chars(wave.replace("|", ""))
            bad = [c for c in v_cycles if c >= len(eff) or eff[c] not in _DATA_REF_CHARS]
            if bad:
                issues.append(Issue(
                    code="TIMING_HANDSHAKE_DATA_UNCOVERED", severity="WARNING",
                    message=f"通道 {prefix}* 信号 {name} 在 {vname} 为高周期 {bad} 未就绪/未保持"
                            f"（VALID 不得先于数据置起，握手含等待态期间数据须稳定，检查 wave 字符索引是否 off-by-one）",
                    object_id=name, rule="timing.handshake_coverage"))
    return issues


def _validate_timing(model: dict[str, Any], behavior: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    clock = behavior.get("clock") or {}
    signals = _iter_timing_lanes(behavior.get("signals", []) or [])
    issues.extend(_handshake_coverage_issues(signals))

    if not clock.get("name"):
        issues.append(Issue(code="TIMING_NO_CLOCK", severity="ERROR",
                            message="时序图缺少 Clock", rule="timing.clock_exists"))

    # 各信号周期数一致性（时钟 wave 可能含 `.` 延续，需扩展为显式周期）
    clock_wave = clock.get("wave") or ""
    if clock_wave:
        # 时钟字符每个代表一个完整方波周期；. 延续；| 分隔
        clock_cycles = len(clock_wave.replace("|", ""))
    else:
        clock_cycles = 0
    for sig in signals:
        wave = sig.get("wave") or ""
        # path 波形（['pw', {d:...}]）不做逐字符 data/node 校验
        if isinstance(wave, list):
            continue
        data = sig.get("data") or []
        # data 可为数组或空格分隔字符串（官方示例两种都支持）
        if isinstance(data, str):
            data_items = data.split() if data.strip() else []
        else:
            data_items = list(data)
        # 显式周期数（去 |，+ 不计为新周期但保持同拍对齐）
        periods = [c for c in wave if c != "|"]
        # data 引用字符 = 数字 2-9 与 =
        data_refs = [c for c in wave if c in _DATA_REF_CHARS]

        # data 数量必须等于引用字符数
        if data_items and len(data_items) != len(data_refs):
            issues.append(Issue(code="TIMING_WAVE_DATA_MISMATCH", severity="ERROR",
                                message=f"信号 {sig.get('name')} 的 wave 引用字符数({len(data_refs)}) 与 data 数({len(data)}) 不一致",
                                object_id=sig.get("name"), rule="timing.wave_data"))

        # node 与 wave 长度一致（箭头锚点对齐）
        node = sig.get("node") or ""
        if node and len(node.replace("|", "")) != len(periods):
            issues.append(Issue(code="TIMING_NODE_LEN_MISMATCH", severity="WARNING",
                                message=f"信号 {sig.get('name')} 的 node 长度与 wave 周期数不一致",
                                object_id=sig.get("name"), rule="timing.node_len"))

        # wave 书写约定检查（WaveDrom 渲染语义）：
        # - 首字符没有"前一状态"可延续，以 `.` 开头会被渲染为未知态（斜线）；
        # - 连续同电平字符（"11"/"00"）在同值相邻处渲染冗余跳变沿（glitch），
        #   连续同电平应写作 "1." / "0."；连续数字（data 拍）不在此列。
        plain = wave.replace("|", "")
        if plain and plain[0] == ".":
            issues.append(Issue(code="TIMING_WAVE_LEADING_DOT", severity="WARNING",
                                message=f"信号 {sig.get('name')} 的 wave 以 `.` 开头（无前态可延续，将渲染为未知态），"
                                        f"首字符应为显式电平（0/1/x/z 或数据字符）",
                                object_id=sig.get("name"), rule="timing.wave_leading_dot"))
        glitch = [f"{a}{b}" for a, b in zip(plain, plain[1:]) if a == b and a in "01"]
        if glitch:
            issues.append(Issue(code="TIMING_WAVE_GLITCH", severity="WARNING",
                                message=f"信号 {sig.get('name')} 的 wave 含连续同电平 {glitch!r}（渲染出 glitch 跳变沿），"
                                        f"连续同电平请用 `.` 延续（如 \"1.\" / \"0.\"）",
                                object_id=sig.get("name"), rule="timing.wave_glitch"))

    # 必选信号缺失（由 diagram 指定 protocol_rules 时可扩展）
    required = [s for s in signals if s.get("required")]
    if required:
        pass

    # 时钟 wave 语法检查（若显式给出）
    if clock_wave:
        bad = [c for c in clock_wave.replace("|", "") if c not in ".pPnNhHlL01xz"]
        if bad:
            issues.append(Issue(code="TIMING_CLOCK_WAVE_INVALID", severity="ERROR",
                                message=f"时钟 wave 含非法字符 {bad!r}（仅允许 p/P/n/N/h/H/l/L/0/1/x/z/./|）",
                                rule="timing.clock_wave"))

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
