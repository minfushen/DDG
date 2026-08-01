"""评估上市公司年报 PDF 四阶段解析管道。

用法：
    cd backend
    ./venv/bin/python scripts/evaluate_annual_report_pipeline.py \
        --enterprise 三安光电 --stock-code 600703 --exchange SSE
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.tools.cninfo_announcement_tool import search_cninfo_announcements
from app.agents.tools.pdf_extraction_engine import download_pdf
from app.engines.rebecca.parsers.financial_pdf_pipeline import parse_annual_report_pdf


def main():
    parser = argparse.ArgumentParser(description="评估年报 PDF 解析管道")
    parser.add_argument("--enterprise", required=True, help="企业名称")
    parser.add_argument("--stock-code", required=True, help="股票代码")
    parser.add_argument("--exchange", default="SSE", help="交易所 SSE/SZSE/BSE")
    parser.add_argument("--max-extract", type=int, default=1, help="解析几份年报")
    args = parser.parse_args()

    print(f"[1/4] 搜索 {args.enterprise} 年报...")
    cninfo_result = search_cninfo_announcements(
        enterprise_name=args.enterprise,
        stock_code=args.stock_code,
        stock_exchange=args.exchange,
        keyword="年度报告",
        max_results=10,
        extract_pdf_content=False,
    )
    if not cninfo_result.get("success"):
        print("搜索失败:", cninfo_result.get("error"))
        return

    annual_reports = [
        r for r in cninfo_result.get("results", [])
        if r.get("announcement_type") == "annual_report"
        and "摘要" not in r.get("title", "")
        and "英文" not in r.get("title", "")
    ][: args.max_extract]

    print(f"找到 {len(annual_reports)} 份完整年报")
    for item in annual_reports:
        print(" -", item.get("published_at"), item.get("title"))

    summary = []
    for item in annual_reports:
        print(f"\n[2/4] 下载 {item.get('published_at')} 年报 PDF...")
        pdf_url = item.get("pdf_url")
        pdf_bytes = download_pdf(pdf_url, timeout=60)
        if not pdf_bytes:
            print("PDF 下载失败")
            continue
        print(f"    PDF 大小: {len(pdf_bytes) / 1024 / 1024:.2f} MB")

        print("[3/4] 运行四阶段解析管道...")
        title = item.get("title", "")
        m = re.search(r"20\d{2}", title)
        report_year = int(m.group()) if m else None
        if report_year is None:
            published = item.get("published_at") or ""
            m = re.search(r"20\d{2}", published)
            report_year = int(m.group()) if m else None
        result = parse_annual_report_pdf(
            pdf_bytes=pdf_bytes,
            enterprise_name=args.enterprise,
            stock_code=args.stock_code,
            report_year=report_year,
            pdf_url=pdf_url,
        )

        print("[4/4] 结果:")
        print(f"    success: {result.success}")
        print(f"    main_table_coverage: {result.main_table_coverage}")
        print(f"    auto_judgment_rate: {result.auto_judgment_rate:.2%}")
        print(f"    needs_human_review: {result.needs_human_review}")
        print(f"    issues: {result.issues}")

        for statement_type in ["income_statement", "balance_sheet", "cash_flow"]:
            df = getattr(result.statements, statement_type)
            if df is not None and not df.empty:
                print(f"\n    {statement_type}: {len(df)} 个标准字段")
                print(df.head(10).to_string(index=False))

        summary.append({
            "published_at": item.get("published_at"),
            "title": item.get("title"),
            "pdf_url": pdf_url,
            "success": result.success,
            "main_table_coverage": result.main_table_coverage,
            "auto_judgment_rate": result.auto_judgment_rate,
            "needs_human_review": result.needs_human_review,
            "issues": result.issues,
        })

    print("\n=== 汇总 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
