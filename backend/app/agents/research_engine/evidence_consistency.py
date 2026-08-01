"""跨源证据一致性校验与冲突消解。

在 claim 装配前检测同一事实字段在不同证据源间的取值冲突：
- 检测冲突（distinct normalized values across sources）；
- 对 claim 降置信度、标记人工复核；
- 生成 evidence_consistency 缺口，喂给 approve_gap 中断。

借鉴 gpt-researcher 的"多源聚合"思想，但金融场景不盲信频率选择——
高可信源与低可信源冲突时优先采信高可信源（低严重度），同级冲突升级为
中等严重度并触发人工复核。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from .state import ResearchGap, stable_id

_MAX_CONFLICT_GAPS = 3
_PENALTY_MEDIUM = 0.72
_PENALTY_LOW = 0.85


def _is_comparable(value: Any) -> bool:
    """是否为可跨源比较的标量字段值（排除长文本/列表/噪声）。"""
    if value is None:
        return False
    text = str(value).strip()
    if not text or len(text) > 80:
        return False
    # 含句级标点的多为原始网页文本，不可比
    if any(ch in text for ch in ["。", "；", "，"]):
        return False
    return True


def _normalize(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("：", ":")


def _extract_comparable_fields(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从证据元数据抽取可跨源比较的 (field, value, source, trust_level, evidence_id) 记录。"""
    records: List[Dict[str, Any]] = []
    for item in evidence:
        metadata = item.get("metadata") or {}
        extracted = metadata.get("extracted_fields") or {}
        source = item.get("source") or item.get("source_name") or item.get("source_type") or "未知来源"
        trust = item.get("trust_level") or item.get("reliability") or "unknown"
        eid = item.get("id", "")

        # 工商登记结构化字段（企业名称/证券代码/法定代表人/注册资本等）
        biz_fields = extracted.get("business_fields") or {}
        if isinstance(biz_fields, dict):
            for field, value in biz_fields.items():
                if _is_comparable(value):
                    records.append({"field": str(field), "value": str(value).strip(),
                                    "source": source, "trust_level": trust, "evidence_id": eid})

        # 司法信号类型集合（按排序后字符串比较，识别"涉诉 vs 无诉讼"类冲突）
        legal = extracted.get("legal_signals") or {}
        signal_types = legal.get("signal_types") or []
        if isinstance(signal_types, list) and signal_types:
            records.append({"field": "司法信号类型",
                            "value": "、".join(sorted(str(s) for s in signal_types)),
                            "source": source, "trust_level": trust, "evidence_id": eid})
    return records


def detect_field_conflicts(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """检测同一字段在不同源间的取值冲突。

    返回冲突列表，每项含 field / values / severity / has_high_trust。
    无冲突或多源取值一致时返回空列表。
    """
    records = _extract_comparable_fields(evidence)
    by_field: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_field[rec["field"]].append(rec)

    conflicts: List[Dict[str, Any]] = []
    for field, entries in by_field.items():
        # 同一来源的重复不算冲突，按 (source, normalized value) 去重
        seen = {}
        distinct_values: List[Dict[str, Any]] = []
        for entry in entries:
            key = (entry["source"], _normalize(entry["value"]))
            if key in seen:
                continue
            seen[key] = True
            distinct_values.append(entry)
        if len(distinct_values) < 2:
            continue
        # 归一化后取值数量
        norm_values = {_normalize(e["value"]) for e in distinct_values}
        if len(norm_values) < 2:
            continue  # 表面不同但归一化后一致（如大小写/空格）

        has_high = any(e["trust_level"] == "high" for e in distinct_values)
        # 高可信源能"裁定"冲突 → 低严重度；同级冲突 → 中等严重度
        severity = "low" if has_high else "medium"
        conflicts.append({
            "field": field,
            "values": [{"value": e["value"], "source": e["source"], "trust_level": e["trust_level"]}
                       for e in distinct_values],
            "severity": severity,
            "has_high_trust": has_high,
        })
    # 中等严重度优先，限制数量避免缺口爆炸
    conflicts.sort(key=lambda c: 0 if c["severity"] == "medium" else 1)
    return conflicts[:_MAX_CONFLICT_GAPS]


def apply_conflicts_to_claim(claim: Dict[str, Any], conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """对 claim 施加冲突惩罚：降置信度、标记人工复核、追加冲突提示。"""
    if not conflicts:
        return claim
    has_medium = any(c["severity"] == "medium" for c in conflicts)
    penalty = _PENALTY_MEDIUM if has_medium else _PENALTY_LOW
    try:
        original = float(claim.get("confidence", 0.5))
    except (TypeError, ValueError):
        original = 0.5
    claim["confidence"] = round(original * penalty, 2)
    claim["requires_manual_review"] = True
    fields = "、".join(sorted({c["field"] for c in conflicts}))[:120]
    claim["text"] = (str(claim.get("text", "")) + f"（注意：{fields}存在跨源取值冲突，已降置信度并标记人工复核）").strip()
    claim["consistency_conflicts"] = len(conflicts)
    return claim


def conflicts_to_gaps(task_id: str, conflicts: List[Dict[str, Any]]) -> List[ResearchGap]:
    """将跨源冲突转化为 evidence_consistency 缺口，喂给 approve_gap 中断。"""
    gaps: List[ResearchGap] = []
    for conflict in conflicts:
        values_str = " vs ".join(f"{v['value']}({v['source']})" for v in conflict["values"][:4])
        gaps.append({
            "id": stable_id("gap_conflict", task_id, conflict["field"]),
            "task_id": task_id,
            "description": f"跨源证据冲突：{conflict['field']}存在{len(conflict['values'])}个不一致取值（{values_str[:160]}）",
            "why_it_matters": "同一字段跨源不一致，可能影响结论可靠性；需人工复核并采信权威源。",
            "suggested_next_actions": ["以权威/高可信源为准", "人工核验冲突字段", "必要时补充官方材料"],
            "severity": conflict["severity"],
            "source": "evidence_consistency",
        })
    return gaps
