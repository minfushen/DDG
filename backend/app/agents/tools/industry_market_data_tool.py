"""行业市场数据工具。

通过 akshare 获取行业指数走势，通过公开搜索补充行业规模、竞争格局、政策和产业链线索。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agents.tools.bocha_search_tool import search_with_bocha, source_confidence
from app.config import settings


# 常见标准行业名称 / 语义行业 ID 到东方财富/同花顺行业板块名称的映射。
# 映射优先保证准确率；无法命中时回退到搜索。
_INDUSTRY_INDEX_MAP = {
    "半导体": "半导体",
    "集成电路": "半导体",
    "芯片": "半导体",
    "晶圆": "半导体",
    "功率器件": "半导体",
    "分立器件": "半导体",
    "led": "LED",
    "led芯片": "LED",
    "光电子": "光学光电子",
    "光学光电子": "光学光电子",
    "锂电池": "电池",
    "锂离子": "电池",
    "动力电池": "电池",
    "储能": "电池",
    "电芯": "电池",
    "pack": "电池",
    "bms": "电池",
    "电池": "电池",
    "白酒": "白酒",
    "保险": "保险",
    "银行": "银行",
    "证券": "证券",
    "电力": "电力",
    "电网": "电网设备",
    "电机": "电机",
    "汽车": "汽车整车",
    "整车": "汽车整车",
    "新能源车": "汽车整车",
    "光伏": "光伏设备",
    "风电": "风电设备",
    "医疗器械": "医疗器械",
    "医药": "化学制药",
    "化学制药": "化学制药",
    "生物制品": "生物制品",
    "中药": "中药",
    "cxo": "医疗服务",
    "医疗服务": "医疗服务",
    "软件开发": "软件开发",
    "it服务": "IT服务",
    "互联网服务": "互联网服务",
    "计算机设备": "计算机设备",
    "通信设备": "通信设备",
    "通信服务": "通信服务",
    "消费电子": "消费电子",
    "电子化学品": "电子化学品",
    "专用设备": "专用设备",
    "通用设备": "通用设备",
    "自动化设备": "自动化设备",
    "军工": "军工装备",
    "航空航天": "军工装备",
    "煤炭": "煤炭",
    "钢铁": "钢铁",
    "有色金属": "有色金属",
    "化工": "化学制品",
    "化学制品": "化学制品",
    "石油化工": "石油石化",
    "石油石化": "石油石化",
    "建筑材料": "建筑材料",
    "建筑装饰": "建筑装饰",
    "房地产": "房地产开发",
    "物流": "物流",
    "交运": "航运港口",
    "航运": "航运港口",
    "港口": "航运港口",
    "农业": "种植业",
    "食品饮料": "食品加工",
    "家电": "白色家电",
    "纺织服装": "纺织制造",
}


def _normalize_industry_name(industry_name: str) -> str:
    """将任意行业名称归一化为搜索/映射友好的形式。"""
    name = (industry_name or "").strip().lower()
    # 去掉常见后缀
    for suffix in ["行业", "产业", "制造", "设备", "材料", "服务", "科技"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name.strip() or industry_name.strip()


def _map_to_index_symbol(industry_name: str) -> Optional[str]:
    """根据行业名称映射到东方财富行业板块名称。"""
    normalized = _normalize_industry_name(industry_name)
    # 精确匹配
    if normalized in _INDUSTRY_INDEX_MAP:
        return _INDUSTRY_INDEX_MAP[normalized]
    # 子串匹配
    for key, symbol in _INDUSTRY_INDEX_MAP.items():
        if key in normalized or normalized in key:
            return symbol
    return None


def _safe_akshare_call(func, *args, **kwargs) -> Optional[Any]:
    """安全调用 akshare，失败返回 None。"""
    try:
        import akshare as ak
        return func(*args, **kwargs)
    except Exception:
        return None


def get_industry_index_data(industry_name: str) -> Dict[str, Any]:
    """获取行业指数近期走势数据。

    Returns:
        {
            "success": bool,
            "symbol": str,  # 映射后的板块名称
            "latest_close": float,
            "latest_date": str,
            "year_change_pct": float,  # 近一年涨跌幅
            "avg_turnover": float,     # 近20日平均成交额（亿元）
            "source": str,
            "error": str,
            "quality_level": str,      # ok / stale / anomaly
            "fallback_search": dict,   # 仅在 stale/anomaly 时填充
        }
    """
    from datetime import datetime, timedelta

    symbol = _map_to_index_symbol(industry_name)
    if not symbol:
        return {
            "success": False,
            "symbol": None,
            "error": f"No index mapping for industry '{industry_name}'",
        }

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=370)).strftime("%Y%m%d")

    df = _safe_akshare_call(
        lambda: __import__("akshare").stock_board_industry_hist_em(
            symbol=symbol,
            period="日k",
            start_date=start_date,
            end_date=end_date,
            adjust="",
        )
    )
    if df is None or df.empty:
        return {
            "success": False,
            "symbol": symbol,
            "error": f"No index data returned for '{symbol}'",
        }

    df = df.sort_values("日期").reset_index(drop=True)
    latest = df.iloc[-1]
    first = df.iloc[0]
    recent = df.tail(20)

    year_change = 0.0
    if len(df) >= 2:
        try:
            year_change = round((float(latest["收盘"]) - float(first["收盘"])) / float(first["收盘"]) * 100, 2)
        except Exception:
            pass

    avg_turnover = 0.0
    try:
        avg_turnover = round(float(recent["成交额"].astype(float).mean()) / 1e8, 2)
    except Exception:
        pass

    result = {
        "success": True,
        "symbol": symbol,
        "latest_close": float(latest["收盘"]),
        "latest_date": str(latest["日期"]),
        "year_change_pct": year_change,
        "avg_turnover": avg_turnover,
        "source": "东方财富行业指数",
        "error": "",
        "quality_level": "ok",
        "fallback_search": {},
    }
    if _is_index_data_stale(result):
        result["quality_level"] = "stale"
        result["error"] = (result["error"] + "; " if result["error"] else "") + "指数数据过期"
        result["fallback_search"] = _fallback_index_text_search(industry_name)
    if _is_index_data_anomaly(result):
        result["quality_level"] = "anomaly"
        result["error"] = (result["error"] + "; " if result["error"] else "") + "指数数据异常"
        if not result.get("fallback_search"):
            result["fallback_search"] = _fallback_index_text_search(industry_name)
    return result


def _score_search_result(item: dict, query: str) -> dict:
    """对单条搜索结果评分并附加质量字段。

    Args:
        item: 原始搜索结果字典。
        query: 对应搜索 query。

    Returns:
        合并 trust_level / confidence / source_type / requires_manual_review 后的字典。
    """
    url = item.get("url") or ""
    if not url:
        trust_level, confidence, source_type = "low", 0.42, "unknown"
    else:
        trust_level, confidence, source_type = source_confidence(url)
    item = dict(item)
    item["trust_level"] = trust_level
    item["confidence"] = confidence
    item["source_type"] = source_type
    item["requires_manual_review"] = trust_level not in {"high"}
    item["query"] = query
    return item


def _apply_quality_to_category(category: dict, category_type: str) -> dict:
    """对类别结果逐条评分并计算整体质量分数。

    Args:
        category: 包含 "results" 的类别字典。
        category_type: 类别标识（仅用于兼容）。

    Returns:
        附加 quality_score / quality_level 的类别字典。
    """
    results = category.get("results") or []
    scored = []
    for item in results:
        if isinstance(item, dict):
            scored.append(_score_search_result(item, category.get("queries", [""])[0] if category.get("queries") else ""))
    category = dict(category)
    category["results"] = scored
    if scored:
        quality_score = round(sum(r.get("confidence", 0.0) for r in scored) / len(scored), 4)
    else:
        quality_score = 0.0
    category["quality_score"] = quality_score
    if quality_score >= 0.75:
        quality_level = "high"
    elif quality_score >= 0.55:
        quality_level = "medium"
    elif quality_score >= 0.35:
        quality_level = "low"
    else:
        quality_level = "none"
    category["quality_level"] = quality_level
    return category


def _is_index_data_stale(index_data: dict, days: int = 5) -> bool:
    """判断指数数据是否过期。

    Args:
        index_data: get_industry_index_data 返回的字典。
        days: 过期天数阈值。

    Returns:
        超过 days 天或解析失败返回 True。
    """
    from datetime import datetime

    latest_date = index_data.get("latest_date")
    if not latest_date:
        return True
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            dt = datetime.strptime(str(latest_date), fmt)
            delta = (datetime.now() - dt).days
            return delta > days
        except ValueError:
            continue
    return True


def _is_index_data_anomaly(index_data: dict) -> bool:
    """判断指数数据是否存在异常值。

    Args:
        index_data: get_industry_index_data 返回的字典。

    Returns:
        year_change_pct 不在 [-80, 200] 或 avg_turnover < 0 或 latest_close 为 None/NaN 返回 True。
    """
    import math

    year_change = index_data.get("year_change_pct")
    avg_turnover = index_data.get("avg_turnover")
    latest_close = index_data.get("latest_close")
    if year_change is not None and (year_change < -80 or year_change > 200):
        return True
    if avg_turnover is not None and avg_turnover < 0:
        return True
    if latest_close is None or (isinstance(latest_close, float) and math.isnan(latest_close)):
        return True
    return False


def _fallback_index_text_search(industry_name: str) -> dict:
    """通过 Bocha 文本搜索获取行业指数走势信息。

    Args:
        industry_name: 行业名称。

    Returns:
        {success, results, error}。
    """
    query = f"{industry_name} 行业指数 走势"
    try:
        resp = search_with_bocha(query, max_results=5, summary=True)
        if resp.get("success"):
            return {"success": True, "results": resp.get("results") or [], "error": ""}
        return {"success": False, "results": [], "error": resp.get("error") or "Bocha search failed"}
    except Exception as exc:
        return {"success": False, "results": [], "error": f"{type(exc).__name__}: {exc}"}


def _fallback_search_with_searxng(query: str, max_results: int = 5) -> list:
    """通过 SearXNG 搜索补充结果。

    Args:
        query: 搜索关键词。
        max_results: 最大结果数。

    Returns:
        成功返回 results 列表，失败返回空列表。
    """
    from app.agents.tools.searxng_search_tool import search_with_searxng

    try:
        resp = search_with_searxng(query, max_results=max_results)
        if resp.get("success"):
            return resp.get("results") or []
    except Exception:
        pass
    return []


def _refill_category(category: dict, category_type: str, industry_name: str) -> dict:
    """对质量不足或结果过少的类别进行补充检索。

    Args:
        category: 包含 results 的类别字典。
        category_type: 类别标识。
        industry_name: 行业名称。

    Returns:
        补充检索后的类别字典（最多一轮）。
    """
    if not getattr(settings, "INDUSTRY_MARKET_DATA_ENABLE_REFILL", True):
        return category
    quality_level = category.get("quality_level")
    results = category.get("results") or []
    if quality_level not in ("none", "low") or len(results) >= 2:
        return category
    # 避免重复补充
    if category.get("refilled"):
        return category

    new_results: list = []
    if category_type == "research_reports":
        from app.agents.tools.research_report_search_tool import search_industry_research_reports

        try:
            resp = search_industry_research_reports(industry_name, max_results=5)
            if resp.get("success"):
                new_results = resp.get("results") or []
        except Exception:
            pass
    else:
        # 生成同义 query 备选
        synonyms = {
            "market_size": ["市场规模", "行业规模", "市场容量"],
            "concentration": ["竞争格局", "市场份额", "行业集中度"],
            "policy": ["产业政策", "行业政策", "监管政策"],
            "chain": ["产业链", "上下游", "供应链"],
        }
        base_queries = synonyms.get(category_type, [industry_name])
        alt_queries = [f"{industry_name} {q}" for q in base_queries[1:3]] if len(base_queries) >= 3 else [f"{industry_name} {base_queries[1]}" if len(base_queries) > 1 else f"{industry_name} 行业分析"]
        for q in alt_queries[:2]:
            new_results.extend(_bocha_search(q, max_results=5))
            new_results.extend(_fallback_search_with_searxng(q, max_results=5))

    # 合并去重
    seen = {r.get("url") for r in results if r.get("url")}
    merged = list(results)
    for r in new_results:
        if isinstance(r, dict) and r.get("url") and r.get("url") not in seen:
            seen.add(r["url"])
            merged.append(r)
        elif isinstance(r, dict) and not r.get("url"):
            merged.append(r)
    category = dict(category)
    category["results"] = merged
    category = _apply_quality_to_category(category, category_type)
    category["refilled"] = True
    return category


def _bocha_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """调用 Bocha 搜索并返回结果列表。"""
    if not settings.BOCHA_API_KEY:
        return []
    try:
        result = search_with_bocha(query, max_results=max_results, summary=True)
        if result.get("success"):
            return result.get("results") or []
    except Exception:
        pass
    return []


def search_industry_market_size(industry_name: str, max_results: int = 5) -> Dict[str, Any]:
    """搜索行业规模、增速、渗透率等宏观数据。"""
    queries = [
        f"{industry_name} 市场规模 2024 亿元 CAGR",
        f"{industry_name} 行业规模 增长率 渗透率",
    ]
    results: List[Dict[str, Any]] = []
    for query in queries:
        results.extend(_bocha_search(query, max_results=max_results))
    return _apply_quality_to_category(
        {
            "queries": queries,
            "results": results[:max_results],
        },
        "market_size",
    )


def search_industry_concentration(industry_name: str, max_results: int = 5) -> Dict[str, Any]:
    """搜索行业集中度、市场份额、竞争格局。"""
    queries = [
        f"{industry_name} CR5 CR3 市场份额 竞争格局",
        f"{industry_name} 行业集中度 龙头企业 市占率",
    ]
    results: List[Dict[str, Any]] = []
    for query in queries:
        results.extend(_bocha_search(query, max_results=max_results))
    return _apply_quality_to_category(
        {
            "queries": queries,
            "results": results[:max_results],
        },
        "concentration",
    )


def search_industry_policy(industry_name: str, max_results: int = 5) -> Dict[str, Any]:
    """搜索行业相关政策。"""
    queries = [
        f"{industry_name} 产业政策 2024 2025",
        f"{industry_name} 行业政策 监管 补贴",
    ]
    results: List[Dict[str, Any]] = []
    for query in queries:
        results.extend(_bocha_search(query, max_results=max_results))
    return _apply_quality_to_category(
        {
            "queries": queries,
            "results": results[:max_results],
        },
        "policy",
    )


def search_industry_chain(industry_name: str, max_results: int = 5) -> Dict[str, Any]:
    """搜索产业链上下游信息。"""
    queries = [
        f"{industry_name} 产业链 上游 下游",
        f"{industry_name} 产业链 供应商 客户",
    ]
    results: List[Dict[str, Any]] = []
    for query in queries:
        results.extend(_bocha_search(query, max_results=max_results))
    return _apply_quality_to_category(
        {
            "queries": queries,
            "results": results[:max_results],
        },
        "chain",
    )


def search_industry_research_reports(industry_name: str, max_results: int = 5) -> Dict[str, Any]:
    """搜索行业研报。"""
    queries = [
        f"{industry_name} 行业研究报告 券商研报",
        f"{industry_name} 行业深度报告 PDF",
    ]
    results: List[Dict[str, Any]] = []
    for query in queries:
        results.extend(_bocha_search(query, max_results=max_results))
    return _apply_quality_to_category(
        {
            "queries": queries,
            "results": results[:max_results],
        },
        "research_reports",
    )


def get_industry_market_data(industry_name: str) -> Dict[str, Any]:
    """汇总行业市场数据：指数走势、规模、集中度、政策、产业链、研报。

    Returns:
        {
            "success": bool,
            "industry_name": str,
            "index_data": {...},
            "market_size": {...},
            "concentration": {...},
            "policy": {...},
            "chain": {...},
            "research_reports": {...},
            "quality_summary": {...},
        }
    """
    index_data = get_industry_index_data(industry_name)
    market_size = search_industry_market_size(industry_name)
    concentration = search_industry_concentration(industry_name)
    policy = search_industry_policy(industry_name)
    chain = search_industry_chain(industry_name)
    research_reports = search_industry_research_reports(industry_name)

    categories = {
        "market_size": market_size,
        "concentration": concentration,
        "policy": policy,
        "chain": chain,
        "research_reports": research_reports,
    }
    for cat_type, cat in categories.items():
        categories[cat_type] = _refill_category(cat, cat_type, industry_name)

    quality_scores = []
    categories_present = 0
    categories_missing = []
    needs_refill = False
    for cat_type, cat in categories.items():
        q_score = cat.get("quality_score", 0.0)
        quality_scores.append(q_score)
        if cat.get("results") or (cat_type == "research_reports" and cat.get("total")):
            categories_present += 1
        q_level = cat.get("quality_level", "none")
        if q_level == "none":
            categories_missing.append(cat_type)
            needs_refill = True
        elif q_level == "low" and len(cat.get("results", [])) < 2:
            needs_refill = True

    index_score = 1.0 if index_data.get("success") else 0.0
    quality_scores.append(index_score)
    overall_quality = round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0
    if index_data.get("success"):
        categories_present += 1

    quality_summary = {
        "overall_quality": overall_quality,
        "categories_present": categories_present,
        "categories_missing": categories_missing,
        "needs_refill": needs_refill,
    }

    return {
        "success": True,
        "industry_name": industry_name,
        "index_data": index_data,
        "market_size": categories["market_size"],
        "concentration": categories["concentration"],
        "policy": categories["policy"],
        "chain": categories["chain"],
        "research_reports": categories["research_reports"],
        "quality_summary": quality_summary,
    }
