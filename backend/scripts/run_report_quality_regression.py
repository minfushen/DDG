#!/usr/bin/env python3
"""Offline report-quality regression runner.

This script evaluates already-generated report JSON files against the listed
company regression samples. It does not create tasks or call the backend API;
that keeps the first regression loop fast and deterministic.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.research_engine.report_quality_evaluator import evaluate_report_quality
from app.config import settings


DEFAULT_SAMPLE_DIR = settings.REGRESSION_SAMPLES_DIR / "listed_companies"
DEFAULT_INPUT_DIR = ROOT / "output" / "reports"
DEFAULT_OUTPUT_ROOT = ROOT / "regression_runs"


def run_offline_regression(
    *,
    input_dir: Path = DEFAULT_INPUT_DIR,
    sample_dir: Path = DEFAULT_SAMPLE_DIR,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    run_id: Optional[str] = None,
    copy_reports: bool = True,
) -> Dict[str, Any]:
    samples = load_samples(sample_dir)
    reports = load_reports(input_dir)
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / run_id
    reports_dir = run_dir / "reports"
    evaluations_dir = run_dir / "evaluations"
    reports_dir.mkdir(parents=True, exist_ok=True)
    evaluations_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for sample in samples:
        matched = match_report_for_sample(sample, reports)
        if not matched:
            result = missing_report_result(sample)
        else:
            report_path, report = matched
            evaluation = evaluate_report_quality(report, sample=sample)
            if copy_reports:
                target_report_path = reports_dir / f"{sample['sample_id']}.json"
                shutil.copyfile(report_path, target_report_path)
            else:
                target_report_path = report_path
            evaluation_path = evaluations_dir / f"{sample['sample_id']}.quality.json"
            evaluation_path.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
            result = sample_result(sample, report_path, target_report_path, evaluation)
        results.append(result)

    summary = build_summary(results, input_dir=input_dir, sample_dir=sample_dir, run_dir=run_dir)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "summary.md").write_text(render_markdown_summary(summary), encoding="utf-8")
    return summary


def load_samples(sample_dir: Path) -> List[Dict[str, Any]]:
    index_path = sample_dir / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"sample index not found: {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    samples = []
    for name in index.get("samples", []):
        path = sample_dir / name
        sample = json.loads(path.read_text(encoding="utf-8"))
        sample["_sample_path"] = str(path)
        samples.append(sample)
    return samples


def load_reports(input_dir: Path) -> List[Tuple[Path, Dict[str, Any], str]]:
    if not input_dir.exists():
        return []
    reports: List[Tuple[Path, Dict[str, Any], str]] = []
    for path in sorted(input_dir.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        searchable = " ".join([
            path.name,
            str(data.get("enterprise_name") or ""),
            str(data.get("company_name") or ""),
            json.dumps(data.get("input_parse") or {}, ensure_ascii=False),
            json.dumps(data.get("basic_info") or {}, ensure_ascii=False),
        ])
        reports.append((path, data, searchable))
    return reports


def match_report_for_sample(sample: Dict[str, Any], reports: List[Tuple[Path, Dict[str, Any], str]]) -> Optional[Tuple[Path, Dict[str, Any]]]:
    sample_id = str(sample.get("sample_id") or "")
    stock_code = str(sample.get("stock_code") or "")
    aliases = [str(item) for item in sample.get("expected_aliases", []) if item]
    display_name = str(sample.get("display_name") or "")
    company_name = str(sample.get("company_name") or "")
    tokens = [sample_id, stock_code, display_name, company_name, *aliases]

    scored: List[Tuple[int, Path, Dict[str, Any]]] = []
    for path, report, searchable in reports:
        haystack = searchable + " " + path.stem
        score = 0
        if sample_id and sample_id in path.stem:
            score += 100
        if stock_code and stock_code in haystack:
            score += 80
        for token in tokens:
            if token and token in haystack:
                score += 20
        if score > 0:
            scored.append((score, path, report))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1], scored[0][2]


def missing_report_result(sample: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sample_id": sample.get("sample_id"),
        "display_name": sample.get("display_name"),
        "company_name": sample.get("company_name"),
        "stock_code": sample.get("stock_code"),
        "status": "missing_report",
        "passed": False,
        "overall_score": 0,
        "grade": "N/A",
        "p0_count": 1,
        "p1_count": 0,
        "p2_count": 0,
        "dimension_scores": {},
        "top_issues": [{
            "severity": "P0",
            "dimension": "report_availability",
            "message": "未找到该样例对应的报告 JSON。",
            "recommendation": "先从前端或 API 生成报告，并将 JSON 保存到 input-dir 后重新运行离线回归。",
        }],
        "report_path": None,
        "copied_report_path": None,
    }


def sample_result(sample: Dict[str, Any], source_path: Path, copied_path: Path, evaluation: Dict[str, Any]) -> Dict[str, Any]:
    issues = evaluation.get("issues", [])
    return {
        "sample_id": sample.get("sample_id"),
        "display_name": sample.get("display_name"),
        "company_name": sample.get("company_name"),
        "stock_code": sample.get("stock_code"),
        "status": "evaluated",
        "passed": bool(evaluation.get("passed")),
        "overall_score": evaluation.get("overall_score"),
        "grade": evaluation.get("grade"),
        "p0_count": len([item for item in issues if item.get("severity") == "P0"]),
        "p1_count": len([item for item in issues if item.get("severity") == "P1"]),
        "p2_count": len([item for item in issues if item.get("severity") == "P2"]),
        "dimension_scores": evaluation.get("dimension_scores", {}),
        "metrics": evaluation.get("metrics", {}),
        "top_issues": issues[:5],
        "top_recommendations": evaluation.get("recommendations", [])[:5],
        "report_path": str(source_path),
        "copied_report_path": str(copied_path),
    }


def build_summary(results: List[Dict[str, Any]], *, input_dir: Path, sample_dir: Path, run_dir: Path) -> Dict[str, Any]:
    evaluated = [item for item in results if item.get("status") == "evaluated"]
    passed = [item for item in evaluated if item.get("passed")]
    scores = [int(item.get("overall_score") or 0) for item in evaluated]
    return {
        "run_id": run_dir.name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "offline",
        "input_dir": str(input_dir),
        "sample_dir": str(sample_dir),
        "run_dir": str(run_dir),
        "total_samples": len(results),
        "evaluated_count": len(evaluated),
        "missing_count": len(results) - len(evaluated),
        "passed_count": len(passed),
        "failed_count": len(evaluated) - len(passed),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "p0_count": sum(int(item.get("p0_count") or 0) for item in results),
        "p1_count": sum(int(item.get("p1_count") or 0) for item in results),
        "p2_count": sum(int(item.get("p2_count") or 0) for item in results),
        "results": results,
    }


def render_markdown_summary(summary: Dict[str, Any]) -> str:
    lines = [
        f"# Report Quality Regression - {summary['run_id']}",
        "",
        f"- Mode: `{summary['mode']}`",
        f"- Input dir: `{summary['input_dir']}`",
        f"- Samples: {summary['total_samples']}",
        f"- Evaluated: {summary['evaluated_count']}",
        f"- Missing: {summary['missing_count']}",
        f"- Passed: {summary['passed_count']}",
        f"- Failed: {summary['failed_count']}",
        f"- Average score: {summary['average_score']}",
        f"- P0/P1/P2: {summary['p0_count']} / {summary['p1_count']} / {summary['p2_count']}",
        "",
        "## Company Results",
        "",
        "| Company | Code | Status | Pass | Score | Grade | P0 | P1 | P2 | Top Issue |",
        "| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for item in summary.get("results", []):
        top_issue = (item.get("top_issues") or [{}])[0].get("message", "-")
        lines.append(
            "| {company} | {code} | {status} | {passed} | {score} | {grade} | {p0} | {p1} | {p2} | {issue} |".format(
                company=item.get("display_name") or item.get("company_name") or "-",
                code=item.get("stock_code") or "-",
                status=item.get("status") or "-",
                passed="Y" if item.get("passed") else "N",
                score=item.get("overall_score") if item.get("overall_score") is not None else "-",
                grade=item.get("grade") or "-",
                p0=item.get("p0_count") or 0,
                p1=item.get("p1_count") or 0,
                p2=item.get("p2_count") or 0,
                issue=_escape_table(str(top_issue))[:120],
            )
        )
    lines.extend(["", "## Top Recommendations", ""])
    recommendations = collect_recommendations(summary.get("results", []))
    if recommendations:
        for recommendation, count in recommendations[:10]:
            lines.append(f"- ({count}) {recommendation}")
    else:
        lines.append("- No recommendations. All evaluated reports passed without major issues.")
    lines.append("")
    return "\n".join(lines)


def collect_recommendations(results: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    for item in results:
        for recommendation in item.get("top_recommendations") or []:
            counts[recommendation] = counts.get(recommendation, 0) + 1
        for issue in item.get("top_issues") or []:
            recommendation = issue.get("recommendation")
            if recommendation:
                counts[recommendation] = counts.get(recommendation, 0) + 1
    return sorted(counts.items(), key=lambda row: row[1], reverse=True)


def _escape_table(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline report-quality regression for listed-company samples.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory containing generated report JSON files")
    parser.add_argument("--sample-dir", default=str(DEFAULT_SAMPLE_DIR), help="Directory containing regression sample JSON files")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Directory for regression run outputs")
    parser.add_argument("--run-id", help="Optional run id; defaults to timestamp")
    parser.add_argument("--no-copy", action="store_true", help="Do not copy matched report JSON into the run directory")
    args = parser.parse_args()

    summary = run_offline_regression(
        input_dir=Path(args.input_dir),
        sample_dir=Path(args.sample_dir),
        output_root=Path(args.output_root),
        run_id=args.run_id,
        copy_reports=not args.no_copy,
    )
    print(json.dumps({
        "run_dir": summary["run_dir"],
        "evaluated_count": summary["evaluated_count"],
        "missing_count": summary["missing_count"],
        "passed_count": summary["passed_count"],
        "average_score": summary["average_score"],
        "summary_md": str(Path(summary["run_dir"]) / "summary.md"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
