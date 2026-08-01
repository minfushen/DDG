"""Report quality evaluator for DDG DeepResearch due-diligence reports.

The evaluator is intentionally deterministic and explainable. It does not try
to judge whether a credit decision is ultimately correct; it checks whether a
generated report has the minimum structure, evidence binding, financial depth,
industry depth, language quality, and credit-policy coherence expected from a
bank customer-manager review draft.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REQUIRED_CHAPTERS = [
    "overview",
    "business",
    "financial",
    "industry",
    "legal",
    "risks",
    "credit",
    "evidence",
]

CHAPTER_NAMES = {
    "overview": "报告摘要与授信建议",
    "business": "企业主体与治理结构",
    "financial": "财务状况与偿债能力",
    "industry": "行业与经营环境",
    "legal": "司法与合规风险",
    "risks": "交叉验证与重大风险",
    "credit": "信贷方案建议",
    "evidence": "证据链与待补充材料",
}

DIMENSION_WEIGHTS = {
    "subject_identity": 10,
    "report_structure": 10,
    "evidence_depth": 15,
    "inline_citations": 15,
    "financial_depth": 15,
    "industry_depth": 15,
    "legal_business_coverage": 8,
    "credit_coherence": 7,
    "language_quality": 5,
}

BAD_LANGUAGE_PATTERNS = [
    "暂不可用",
    "暂不可计算",
    "报告专项待补充",
    "专项报告待补充",
    "模拟数据",
    "mock",
    "兜底模拟",
    "牛奶准入",
    "建议可口",
    "边界边界",
    "状况与偿债能力",
    "回周期",
    # OCR / 识别错误词与低质量口语表达
    "鱼子",
    "鱼籽",
    "显着",
    "显箸",
    "什么玩意儿",
    "啥玩意儿",
]

# 合法超集短语：某些 bad pattern 是合法章节标题的子串（如"状况与偿债能力"是
# "财务状况与偿债能力"的子串），匹配时需减去合法超集出现次数，避免对正文标题误报。
LEGITIMATE_SUPERSETS = {
    "状况与偿债能力": "财务状况与偿债能力",
}

FINANCIAL_KEYWORDS = [
    "近三年",
    "营业收入",
    "净利润",
    "毛利率",
    "经营现金流",
    "资产负债率",
    "流动比率",
    "应收账款",
]

INDUSTRY_KEYWORDS = [
    "行业定位",
    "周期",
    "竞争格局",
    "政策",
    "上下游",
    "议价能力",
    "授信关注",
    "同业",
]

LEGAL_BUSINESS_KEYWORDS = [
    "统一社会信用代码",
    "法定代表人",
    "注册资本",
    "经营范围",
    "股权",
    "行政处罚",
    "裁判",
    "被执行",
    "失信",
]


@dataclass
class QualityIssue:
    severity: str
    dimension: str
    message: str
    recommendation: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "dimension": self.dimension,
            "message": self.message,
            "recommendation": self.recommendation,
        }


def evaluate_report_quality(report: Dict[str, Any], sample: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate one due-diligence report JSON and return a scored result."""
    sample = sample or {}
    evidence = _evidence_items(report)
    chapters = _chapter_map(report)
    evidence_ids = {str(item.get("id")) for item in evidence if item.get("id")}
    corpus = _report_text(report)
    issues: List[QualityIssue] = []

    dimension_scores = {
        "subject_identity": _score_subject_identity(report, sample, corpus, issues),
        "report_structure": _score_report_structure(chapters, issues),
        "evidence_depth": _score_evidence_depth(evidence, issues),
        "inline_citations": _score_inline_citations(chapters, evidence_ids, issues),
        "financial_depth": _score_financial_depth(chapters.get("financial", {}), corpus, issues),
        "industry_depth": _score_industry_depth(chapters.get("industry", {}), corpus, sample, issues),
        "legal_business_coverage": _score_legal_business(chapters, corpus, issues),
        "credit_coherence": _score_credit_coherence(report, chapters, issues),
        "language_quality": _score_language_quality(corpus, issues),
    }
    weighted_score = round(sum(dimension_scores[key] * DIMENSION_WEIGHTS[key] for key in DIMENSION_WEIGHTS) / 100)
    blockers = [issue for issue in issues if issue.severity == "P0"]
    high = [issue for issue in issues if issue.severity == "P1"]
    result = {
        "overall_score": weighted_score,
        "grade": _grade(weighted_score),
        "passed": weighted_score >= 75 and not blockers and len(high) <= 3,
        "dimension_scores": dimension_scores,
        "issues": [issue.to_dict() for issue in issues],
        "metrics": {
            "chapter_count": len(chapters),
            "evidence_count": len(evidence),
            "high_trust_evidence_count": len([item for item in evidence if item.get("trust_level") == "high" or item.get("reliability") == "high"]),
            "evidence_with_source_url_count": len([item for item in evidence if item.get("source_url")]),
            "inline_citation_count": _inline_citation_count(chapters),
            "unresolved_placeholder_count": _count_bad_phrases(corpus),
        },
        "recommendations": _top_recommendations(issues),
    }
    return result


def evaluate_report_file(report_path: str | Path, sample_path: str | Path | None = None) -> Dict[str, Any]:
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    sample = json.loads(Path(sample_path).read_text(encoding="utf-8")) if sample_path else None
    return evaluate_report_quality(report, sample=sample)


def _score_subject_identity(report: Dict[str, Any], sample: Dict[str, Any], corpus: str, issues: List[QualityIssue]) -> int:
    enterprise_name = str(report.get("enterprise_name") or "").strip()
    if not enterprise_name:
        issues.append(_issue("P0", "subject_identity", "报告缺少企业主体名称。", "确保任务创建和报告合成层都写入 enterprise_name。"))
        return 0
    polluted_words = ["分析一下", "这家上市公司", "这个上市公司", "进行全方位尽调"]
    if any(word in enterprise_name for word in polluted_words):
        issues.append(_issue("P0", "subject_identity", f"企业主体疑似被用户指令污染：{enterprise_name}", "主体识别应只保留公司名称或证券简称，不应带入任务话术。"))
        return 25

    expected_aliases = [str(item) for item in sample.get("expected_aliases", []) if item]
    if expected_aliases and not any(alias in enterprise_name or alias in corpus for alias in expected_aliases):
        issues.append(_issue("P1", "subject_identity", "报告未命中回归样例中的主体别名。", "检查证券简称、公司全称、股票代码映射是否正确。"))
        return 65
    return 100


def _score_report_structure(chapters: Dict[str, Dict[str, Any]], issues: List[QualityIssue]) -> int:
    missing = [chapter for chapter in REQUIRED_CHAPTERS if chapter not in chapters]
    if missing:
        issues.append(_issue("P1", "report_structure", f"缺少报告章节：{', '.join(CHAPTER_NAMES[item] for item in missing)}。", "报告合成层应稳定输出 8 章贷前尽调结构。"))
    score = max(0, 100 - len(missing) * 14)
    for chapter_id, chapter in chapters.items():
        if chapter_id in REQUIRED_CHAPTERS and not (chapter.get("summary") or chapter.get("findings") or chapter.get("subsections")):
            issues.append(_issue("P2", "report_structure", f"章节内容较空：{CHAPTER_NAMES.get(chapter_id, chapter_id)}。", "至少输出摘要、发现或结构化小节之一。"))
            score -= 5
    return _clamp(score)


def _score_evidence_depth(evidence: List[Dict[str, Any]], issues: List[QualityIssue]) -> int:
    count = len(evidence)
    high_trust = len([item for item in evidence if item.get("trust_level") == "high" or item.get("reliability") == "high"])
    with_url = len([item for item in evidence if item.get("source_url")])
    score = min(100, count * 4 + high_trust * 4 + with_url * 2)
    if count < 12:
        issues.append(_issue("P1", "evidence_depth", f"证据数量不足：当前 {count} 项。", "完整尽调建议至少归集 16 项证据，覆盖工商、财务、司法、行业、知识库。"))
    if high_trust < 4:
        issues.append(_issue("P1", "evidence_depth", f"高可信证据不足：当前 {high_trust} 项。", "优先接入公告、交易所、财报、政府/司法权威源。"))
    if with_url < 4:
        issues.append(_issue("P2", "evidence_depth", f"可点击来源链接不足：当前 {with_url} 项。", "公开资料证据应保留 source_url，方便客户经理复核。"))
    return _clamp(score)


def _score_inline_citations(chapters: Dict[str, Dict[str, Any]], evidence_ids: set[str], issues: List[QualityIssue]) -> int:
    refs = _all_evidence_refs(chapters)
    valid_refs = [ref for ref in refs if ref in evidence_ids]
    citation_count = _inline_citation_count(chapters)
    if not refs:
        issues.append(_issue("P0", "inline_citations", "报告正文没有 evidence 引用。", "每个关键结论都应绑定 evidence_refs，而不是只在附录堆 evidence。"))
        return 0
    invalid_count = len(refs) - len(valid_refs)
    if invalid_count:
        issues.append(_issue("P1", "inline_citations", f"存在 {invalid_count} 个无效 evidence_refs。", "报告合成层引用 evidence 前需校验 ID 是否存在。"))
    chapter_with_refs = len([chapter for chapter in REQUIRED_CHAPTERS[:-1] if chapters.get(chapter, {}).get("evidence_refs") or _chapter_refs(chapters.get(chapter, {}))])
    score = min(100, citation_count * 8 + chapter_with_refs * 7 - invalid_count * 8)
    if chapter_with_refs < 5:
        issues.append(_issue("P1", "inline_citations", f"正文级引用覆盖章节不足：当前 {chapter_with_refs} 章。", "至少在摘要、财务、行业、司法、交叉验证、授信建议中展示正文级证据引用。"))
    return _clamp(score)


def _score_financial_depth(financial_chapter: Dict[str, Any], corpus: str, issues: List[QualityIssue]) -> int:
    text = _json_text(financial_chapter)
    keyword_hits = _keyword_hits(text + corpus, FINANCIAL_KEYWORDS)
    score = min(100, keyword_hits * 10)
    if "近三年" not in text and "三年" not in text:
        issues.append(_issue("P1", "financial_depth", "财务章节没有明确近三年分析口径。", "财务 prompt 和报告装配层应强制围绕近三年收入、利润、现金流、资产负债展开。"))
        score -= 15
    if not financial_chapter.get("evidence_refs") and not _chapter_refs(financial_chapter):
        issues.append(_issue("P1", "financial_depth", "财务章节缺少证据引用。", "将结构化财报 evidence、公告 evidence 和财务诊断 evidence 绑定到财务正文。"))
        score -= 20
    if _contains_any(text, ["财务专项报告待补充", "财务专项尚未形成充分证据", "暂不可计算"]):
        issues.append(_issue("P1", "financial_depth", "财务章节仍有明显占位或不可用表达。", "优先检查上市公司财报抓取和财务诊断生成是否成功。"))
        score -= 25
    return _clamp(score)


def _score_industry_depth(industry_chapter: Dict[str, Any], corpus: str, sample: Dict[str, Any], issues: List[QualityIssue]) -> int:
    text = _json_text(industry_chapter)
    keyword_hits = _keyword_hits(text + corpus, INDUSTRY_KEYWORDS)
    score = min(100, keyword_hits * 10)
    expected_industry_keywords = [str(item) for item in sample.get("expected_industry_keywords", []) if item]
    if expected_industry_keywords and not any(keyword in text + corpus for keyword in expected_industry_keywords):
        issues.append(_issue("P1", "industry_depth", "行业章节未命中预期细分行业关键词。", "行业识别应结合证券简称、主营构成、年报经营讨论和行业知识库，避免识别到泛行业。"))
        score -= 20
    if not industry_chapter.get("evidence_refs") and not _chapter_refs(industry_chapter):
        issues.append(_issue("P1", "industry_depth", "行业章节缺少证据引用。", "把主营构成、年报经营讨论、研报摘要、行业知识库命中绑定到行业正文。"))
        score -= 20
    if _contains_any(text, ["行业专项报告待补充", "行业专项尚未形成充分证据", "贸易/进出口"]):
        issues.append(_issue("P1", "industry_depth", "行业章节存在占位或疑似错分。", "补强行业 LLM 分类、主营构成证据和行业子赛道校验。"))
        score -= 25
    return _clamp(score)


def _score_legal_business(chapters: Dict[str, Dict[str, Any]], corpus: str, issues: List[QualityIssue]) -> int:
    business_text = _json_text(chapters.get("business", {}))
    legal_text = _json_text(chapters.get("legal", {}))
    hits = _keyword_hits(business_text + legal_text + corpus, LEGAL_BUSINESS_KEYWORDS)
    score = min(100, hits * 9)
    if not chapters.get("business", {}).get("evidence_refs"):
        issues.append(_issue("P2", "legal_business_coverage", "企业主体章节缺少章节级证据引用。", "工商登记、经营范围、股权和异常经营结论需要绑定 evidence。"))
        score -= 10
    if not chapters.get("legal", {}).get("evidence_refs"):
        issues.append(_issue("P2", "legal_business_coverage", "司法合规章节缺少章节级证据引用。", "裁判、执行、处罚、公告线索需要绑定 evidence，并说明权威性边界。"))
        score -= 10
    return _clamp(score)


def _score_credit_coherence(report: Dict[str, Any], chapters: Dict[str, Dict[str, Any]], issues: List[QualityIssue]) -> int:
    score = 100
    risk_score = report.get("risk_score")
    risk_rating = str(report.get("risk_rating") or "")
    decision = report.get("credit_decision") or {}
    suggestion = str(decision.get("suggestion") or report.get("recommendation") or "")
    if not suggestion:
        issues.append(_issue("P1", "credit_coherence", "缺少准入建议。", "报告摘要和信贷方案章节必须输出准入/审慎/暂缓等明确建议。"))
        score -= 30
    if isinstance(risk_score, (int, float)):
        if risk_score >= 78 and risk_rating == "high":
            issues.append(_issue("P1", "credit_coherence", "风险分和风险等级不一致。", "统一风险评分到 risk_rating 的映射规则。"))
            score -= 25
        if risk_score < 60 and any(word in suggestion for word in ["准入", "建议采纳", "推荐"]):
            issues.append(_issue("P1", "credit_coherence", "低分报告却给出偏积极准入建议。", "授信建议应与风险评分、重大缺口和司法风险一致。"))
            score -= 25
    credit_text = _json_text(chapters.get("credit", {}))
    if not _contains_any(credit_text, ["额度", "期限", "担保", "提款", "贷后"]):
        issues.append(_issue("P2", "credit_coherence", "信贷方案缺少额度、期限、担保、提款或贷后条件。", "信贷方案章节应按客户经理审批习惯结构化输出。"))
        score -= 15
    return _clamp(score)


def _score_language_quality(corpus: str, issues: List[QualityIssue]) -> int:
    bad_hits = _find_bad_phrases(corpus)
    bad_count = sum(bad_hits.values())
    score = 100 - bad_count * 10
    if bad_count:
        hit_terms = [f"'{term}'" for term, count in bad_hits.items() if count]
        message = f"发现 {bad_count} 处占位、病句或演示污染表达"
        if hit_terms:
            message += "：" + "、".join(hit_terms)
        issues.append(_issue("P1" if bad_count >= 3 else "P2", "language_quality", message + "。", "加强报告后处理质检，禁止 mock、兜底、不可用堆叠和明显错词进入正式报告。"))
    if len(corpus) < 1200:
        issues.append(_issue("P2", "language_quality", "报告正文过短，可能只输出了摘要或过程信息。", "完整尽调报告应包含 8 章正文、风险结论、授信建议和证据链。"))
        score -= 20
    return _clamp(score)


def _evidence_items(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = report.get("evidence_docs") or report.get("evidence") or []
    return evidence if isinstance(evidence, list) else []


def _chapter_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    chapters = report.get("report_chapters") or []
    return {str(item.get("id")): item for item in chapters if isinstance(item, dict) and item.get("id")}


def _report_text(report: Dict[str, Any]) -> str:
    return _json_text({
        "enterprise_name": report.get("enterprise_name"),
        "recommendation": report.get("recommendation"),
        "executive_summary": report.get("executive_summary"),
        "risk_dimensions": report.get("risk_dimensions"),
        "credit_decision": report.get("credit_decision"),
        "cross_findings": report.get("cross_findings"),
        "report_chapters": report.get("report_chapters"),
    })


def _json_text(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _keyword_hits(text: str, keywords: Iterable[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _contains_any(text: str, patterns: Iterable[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _count_bad_phrases(text: str) -> int:
    return sum(_find_bad_phrases(text).values())


def _find_bad_phrases(text: str) -> Dict[str, int]:
    """Return a map of matched bad-language patterns and their occurrence counts.

    某些 pattern 是合法章节标题的子串（如"状况与偿债能力"⊂"财务状况与偿债能力"），
    需减去合法超集的出现次数，避免对正文标题误报。
    """
    text_lower = text.lower()
    result: Dict[str, int] = {}
    for pattern in BAD_LANGUAGE_PATTERNS:
        if pattern.lower() not in text_lower:
            continue
        count = len(re.findall(re.escape(pattern), text, flags=re.IGNORECASE))
        legit = LEGITIMATE_SUPERSETS.get(pattern)
        if legit and legit.lower() in text_lower:
            count -= len(re.findall(re.escape(legit), text, flags=re.IGNORECASE))
        if count > 0:
            result[pattern] = count
    return result


def _all_evidence_refs(chapters: Dict[str, Dict[str, Any]]) -> List[str]:
    refs: List[str] = []
    for chapter in chapters.values():
        refs.extend(_chapter_refs(chapter))
    return [str(ref) for ref in refs if ref]


def _chapter_refs(chapter: Dict[str, Any]) -> List[str]:
    refs: List[str] = []
    refs.extend(chapter.get("evidence_refs") or [])
    for citation in chapter.get("summary_citations") or []:
        refs.extend(citation.get("evidence_refs") or [])
    for finding in chapter.get("findings") or []:
        refs.extend(finding.get("evidence_refs") or [])
    for subsection in chapter.get("subsections") or []:
        refs.extend(subsection.get("evidence_refs") or [])
    return refs


def _inline_citation_count(chapters: Dict[str, Dict[str, Any]]) -> int:
    count = 0
    for chapter in chapters.values():
        count += len([item for item in chapter.get("summary_citations") or [] if item.get("evidence_refs")])
        count += len([item for item in chapter.get("findings") or [] if item.get("evidence_refs")])
        count += len([item for item in chapter.get("subsections") or [] if item.get("evidence_refs")])
    return count


def _top_recommendations(issues: List[QualityIssue]) -> List[str]:
    seen = set()
    recommendations: List[str] = []
    priority = {"P0": 0, "P1": 1, "P2": 2}
    for issue in sorted(issues, key=lambda item: priority.get(item.severity, 9)):
        if issue.recommendation not in seen:
            recommendations.append(issue.recommendation)
            seen.add(issue.recommendation)
        if len(recommendations) >= 8:
            break
    return recommendations


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "E"


def _issue(severity: str, dimension: str, message: str, recommendation: str) -> QualityIssue:
    return QualityIssue(severity=severity, dimension=dimension, message=message, recommendation=recommendation)


def _clamp(score: int | float) -> int:
    return max(0, min(100, round(score)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a DDG due-diligence report JSON file.")
    parser.add_argument("report", help="Path to report JSON")
    parser.add_argument("--sample", help="Optional regression sample JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()
    result = evaluate_report_file(args.report, args.sample)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
