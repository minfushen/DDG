# ========================================
# 工商分析Agent
# 使用联网搜索获取企业工商信息
# ========================================

from typing import Dict, Any, List
from datetime import datetime
import uuid
import json

from app.agents.tools.search_tool import search_enterprise_info


async def run_business_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行工商分析Agent

    Args:
        enterprise_name: 企业名称

    Returns:
        Dict: 分析结果，包含 timeline、evidence、success
    """
    try:
        timeline = []
        evidence = []

        # 步骤1：获取工商信息
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "工商Agent",
            "content": "获取企业工商信息",
            "detail": "统一社会信用代码、注册资本、经营范围",
            "status": "running",
            "type": "discovery",
        })

        # 调用搜索工具
        result_json = search_enterprise_info._run(enterprise_name=enterprise_name)
        result = json.loads(result_json)

        # 更新时间轴
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"成立于{result.get('成立日期', '未知')}",
            f"注册资本{result.get('注册资本', '未知')}",
            f"经营范围覆盖{result.get('经营范围', '未知')[:20]}...",
        ]

        # 添加证据
        evidence.append({
            "label": "统一社会信用代码",
            "value": result.get("统一社会信用代码", ""),
            "source": "国家企业信用信息公示系统",
        })
        evidence.append({
            "label": "注册资本",
            "value": result.get("注册资本", ""),
            "source": "工商登记信息",
        })

        # 步骤2：分析股东结构
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "工商Agent",
            "content": "分析股东结构",
            "detail": "股东信息、持股比例",
            "status": "running",
            "type": "analysis",
        })

        shareholders = result.get("股东信息", [])
        findings = [f"{s['股东名称']}持股{s['持股比例']}" for s in shareholders]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = findings

        # 步骤3：分析对外投资
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "工商Agent",
            "content": "分析对外投资",
            "detail": "关联企业、投资关系",
            "status": "running",
            "type": "analysis",
        })

        investments = result.get("对外投资", [])
        findings = [f"{i['企业名称']}（持股{i['持股比例']}）" for i in investments]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = findings
        timeline[-1]["conclusion"] = f"发现关联企业{len(investments)}家"

        # 添加证据
        evidence.append({
            "label": "关联企业",
            "value": f"{len(investments)}家",
            "source": "工商登记信息",
        })

        return {
            "success": True,
            "timeline": timeline,
            "evidence": evidence,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "工商Agent",
                "content": "工商分析失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }
