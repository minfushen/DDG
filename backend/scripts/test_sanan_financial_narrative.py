"""测试三安光电财务叙事生成，验证行业上下文和核心判断。"""
import asyncio
import json
import sys
import traceback
from datetime import datetime

sys.path.insert(0, "/Users/minfushen/Projects/ddg-agent/backend")

from app.agents.sub_agents.financial_agent import run_financial_agent


async def main():
    print(f"[{datetime.now().isoformat()}] 开始运行三安光电财务分析...")
    try:
        result = await run_financial_agent(
            enterprise_name="三安光电",
            session_id=None,
            task_id=None,
        )
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] 运行异常: {e}")
        traceback.print_exc()
        return

    output_path = "/Users/minfushen/Projects/ddg-agent/backend/output/test_sanan_financial_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().isoformat()}] 结果已保存到 {output_path}")
    print(f"success={result.get('success')}")
    if result.get("error"):
        print(f"error={result['error']}")

    report = result.get("financial_analysis_report") or {}
    sections = report.get("sections") or []
    print("\n=== 财务小节 narrative 检查 ===")
    for sec in sections:
        for sub in sec.get("subsections") or []:
            title = sub.get("title", "")
            analysis = sub.get("analysis", [])
            source = sub.get("narrative_source", "rule")
            text = " ".join(analysis) if isinstance(analysis, list) else str(analysis)
            has_core = "核心判断" in text
            print(f"\n[{title}] source={source}, has_core={has_core}")
            print(text[:400] + "..." if len(text) > 400 else text)

    print("\n=== 关键检查 ===")
    full_text = json.dumps(report, ensure_ascii=False)
    print(f"包含'核心判断': {'核心判断' in full_text}")
    print(f"包含'LED': {'LED' in full_text}")
    print(f"包含'SiC': {'SiC' in full_text}")
    print(f"包含'产能过剩': {'产能过剩' in full_text}")
    print(f"包含'产能爬坡': {'产能爬坡' in full_text}")
    print(f"包含'资产结构相对轻量': {'资产结构相对轻量' in full_text}")


if __name__ == "__main__":
    asyncio.run(main())
