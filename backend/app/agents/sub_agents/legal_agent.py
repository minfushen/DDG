# ========================================
# 司法分析Agent
# 使用联网搜索获取企业司法信息
# ========================================

from typing import Dict, Any
from datetime import datetime
import uuid
import json

from app.agents.tools.search_tool import search_legal_records


async def run_legal_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行司法分析Agent

    Args:
        enterprise_name: 企业名称

    Returns:
        Dict: 分析结果，包含 timeline、evidence、success
    """
    try:
        timeline = []
        evidence = []

        # 步骤1：获取司法记录
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "司法Agent",
            "content": "检索裁判文书网",
            "detail": "查询企业涉诉信息",
            "status": "running",
            "type": "discovery",
        })

        # 调用搜索工具
        result_json = search_legal_records.invoke({"enterprise_name": enterprise_name})
        result = json.loads(result_json)

        # 更新时间轴
        timeline[-1]["status"] = "completed"

        # 步骤2：分析裁判文书
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "司法Agent",
            "content": "分析裁判文书",
            "detail": "合同纠纷、劳动争议等",
            "status": "running",
            "type": "analysis",
        })

        judgments = result.get("裁判文书", [])
        findings = [f"{j['案由']}（{j['状态']}）" for j in judgments]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = findings

        # 添加证据
        evidence.append({
            "label": "裁判文书",
            "value": f"{len(judgments)}份",
            "source": "中国裁判文书网",
        })

        # 步骤3：分析行政处罚
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "司法Agent",
            "content": "查询行政处罚记录",
            "detail": "环保、税务、市场监管等",
            "status": "running",
            "type": "risk",
        })

        penalties = result.get("行政处罚", [])
        findings = [f"{p['处罚类型']} {p['处罚金额']}" for p in penalties]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = findings

        if penalties:
            total_amount = sum(int(p["处罚金额"].replace("万元", "")) for p in penalties)
            timeline[-1]["conclusion"] = f"发现{len(penalties)}条行政处罚，合计{total_amount}万元"

        # 添加证据
        evidence.append({
            "label": "行政处罚",
            "value": f"{len(penalties)}条",
            "source": "国家企业信用信息公示系统",
        })

        # 步骤4：查询失信被执行人
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "司法Agent",
            "content": "查询失信被执行人",
            "detail": "全国法院失信被执行人名单",
            "status": "running",
            "type": "risk",
        })

        dishonest = result.get("失信被执行人", [])
        timeline[-1]["status"] = "completed"

        if dishonest:
            timeline[-1]["findings"] = [f"存在{len(dishonest)}条失信记录"]
            timeline[-1]["conclusion"] = "存在失信被执行记录，需谨慎"
        else:
            timeline[-1]["findings"] = ["无失信被执行记录"]
            timeline[-1]["conclusion"] = "无失信被执行记录"

        # 添加证据
        evidence.append({
            "label": "失信被执行人",
            "value": f"{len(dishonest)}条" if dishonest else "无",
            "source": "中国执行信息公开网",
        })

        # 步骤5：分析股权出质
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "司法Agent",
            "content": "分析股权出质情况",
            "detail": "股权质押、冻结等",
            "status": "running",
            "type": "analysis",
        })

        pledges = result.get("股权出质", [])
        findings = [f"{p['出质人']}质押{p['出质金额']}" for p in pledges]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = findings if pledges else ["无股权出质记录"]

        # 添加证据
        evidence.append({
            "label": "股权出质",
            "value": f"{len(pledges)}条" if pledges else "无",
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
                "agent": "司法Agent",
                "content": "司法分析失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }
