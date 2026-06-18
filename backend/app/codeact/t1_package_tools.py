"""T+1 front-machine data package validation CodeAct tool."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List


ALLOWED_DOMAINS = {"business", "legal", "financial", "industry", "news"}
REQUIRED_FIELDS = ["package_id", "subject_name", "data_domain", "as_of_date", "source_name", "source_type", "records"]


def validate_t1_data_package(payload: Dict[str, Any]) -> Dict[str, Any]:
    package = payload.get("package") if isinstance(payload.get("package"), dict) else payload
    if not isinstance(package, dict):
        raise ValueError("payload.package must be a data package object")

    issues: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    for field in REQUIRED_FIELDS:
        if package.get(field) in (None, "", []):
            issues.append(_issue("P0", "missing_field", f"缺少必填字段：{field}", "按前置机标准数据包 schema 补齐字段。", field=field))

    domain = str(package.get("data_domain") or "")
    if domain and domain not in ALLOWED_DOMAINS:
        issues.append(_issue("P0", "invalid_domain", f"data_domain 不在允许范围：{domain}", f"允许值：{', '.join(sorted(ALLOWED_DOMAINS))}。"))

    as_of = _parse_date(package.get("as_of_date"))
    if package.get("as_of_date") and as_of is None:
        issues.append(_issue("P0", "invalid_as_of_date", "as_of_date 日期格式无效", "建议使用 YYYY-MM-DD。"))
    elif as_of and as_of > date.today():
        warnings.append(_issue("P1", "future_as_of_date", "as_of_date 晚于当前日期", "核对前置机批次日期和时区配置。"))

    records = package.get("records")
    if records is not None and not isinstance(records, list):
        issues.append(_issue("P0", "invalid_records", "records 必须是数组", "每条记录应为标准化对象。"))
    elif isinstance(records, list):
        if not records:
            issues.append(_issue("P0", "empty_records", "records 为空", "前置机数据包至少应包含一条标准化记录。"))
        for index, record in enumerate(records[:20]):
            if not isinstance(record, dict):
                warnings.append(_issue("P1", "invalid_record", f"第{index + 1}条 record 不是对象", "检查数据标准化输出。", index=index))

    subject_keys = package.get("subject_keys")
    if subject_keys is not None and not isinstance(subject_keys, dict):
        warnings.append(_issue("P1", "invalid_subject_keys", "subject_keys 应为对象", "建议包含 credit_code、stock_code、aliases 等主体索引。"))
    elif isinstance(subject_keys, dict):
        if not any(subject_keys.get(key) for key in ["credit_code", "stock_code", "aliases"]):
            warnings.append(_issue("P2", "weak_subject_keys", "subject_keys 缺少主体识别键", "至少提供统一社会信用代码、股票代码或别名列表之一。"))

    if not package.get("checksum"):
        warnings.append(_issue("P1", "missing_checksum", "缺少 checksum", "建议前置机输出文件级 checksum，便于审计追溯和重复入库校验。"))
    if not package.get("raw_refs"):
        warnings.append(_issue("P2", "missing_raw_refs", "缺少 raw_refs", "建议保留原始供应商文件或接口响应引用。"))
    if not package.get("license_scope"):
        warnings.append(_issue("P2", "missing_license_scope", "缺少 license_scope", "建议标明数据授权使用范围。"))

    freshness_days = None
    if as_of:
        freshness_days = (date.today() - as_of).days
        max_age_days = int(payload.get("max_age_days") or 3)
        if freshness_days > max_age_days:
            warnings.append(_issue("P1", "stale_package", f"数据包距今 {freshness_days} 天，超过阈值 {max_age_days} 天", "确认是否仍可用于当前尽调，必要时要求补充最新批次。"))

    return {
        "passed": not any(item["severity"] == "P0" for item in issues),
        "issues": issues,
        "warnings": warnings,
        "metrics": {
            "record_count": len(records) if isinstance(records, list) else 0,
            "freshness_days": freshness_days,
            "has_checksum": bool(package.get("checksum")),
            "has_raw_refs": bool(package.get("raw_refs")),
        },
        "summary": _summary(issues, warnings),
    }


def _parse_date(value: Any):
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()[:10]
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _issue(severity: str, code: str, message: str, recommendation: str, **extra: Any) -> Dict[str, Any]:
    item = {"severity": severity, "code": code, "message": message, "recommendation": recommendation}
    item.update(extra)
    return item


def _summary(issues: List[Dict[str, Any]], warnings: List[Dict[str, Any]]) -> str:
    if issues:
        return f"T+1 数据包存在{len(issues)}项阻断性问题，不建议入库或用于报告证据。"
    if warnings:
        return f"T+1 数据包 schema 基本可用，但存在{len(warnings)}项需复核事项。"
    return "T+1 数据包通过基础 schema、追溯和新鲜度校验。"
