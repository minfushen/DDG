"""测试 run_industry_agent 返回类型。"""
import asyncio
import json
import sys
from datetime import datetime

sys.path.insert(0, "/Users/minfushen/Projects/ddg-agent/backend")

from app.agents.sub_agents.industry_agent import run_industry_agent


async def main():
    print(f"[{datetime.now().isoformat()}] 开始运行行业分析...")
    result = await run_industry_agent(
        enterprise_name="三安光电",
        public_info=None,
        annual_report_notes=None,
    )
    print(f"result type: {type(result)}")
    print(f"success={result.get('success') if isinstance(result, dict) else 'N/A'}")
    print(f"error={result.get('error') if isinstance(result, dict) else 'N/A'}")

    output_path = "/Users/minfushen/Projects/ddg-agent/backend/output/test_sanan_industry_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result if isinstance(result, dict) else {"result": str(result)}, f, ensure_ascii=False, indent=2)
    print(f"结果已保存到 {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
