"""行业财务指标中位数取数（P2.1：替换 analyzers.py 硬编码假行业基准）。

按申万/东方财富行业取同行业 A 股成分股，批量拉取财务分析指标，计算各指标中位数，
作为企业同业对标的真实基准。取数失败时返回空 dict，由 analyzers 降级显示
"行业基准暂不可得"，绝不回退到硬编码假值。

设计要点：
- 进程内缓存（按 industry_name），避免重复拉取。
- 成分股限流（默认前 30 家），控制 akshare 调用量与延迟。
- 全程 try/except 降级，任何一步失败都不抛异常，保证分析主流程不被拖垮。
- 指标 key 与 analyzers._analyze_* 对齐（gross_margin / net_margin / roe 等）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 成分股抽样上限：兼顾代表性与延迟。
_MAX_CONSTITUENTS = 30

# akshare stock_financial_analysis_indicator 返回列名 → 统一 benchmark key。
# 列名以 akshare 实际返回为准，兼容常见变体。
_INDICATOR_COLUMN_MAP = {
    "gross_margin": ["销售毛利率(%)", "销售毛利率", "毛利率(%)", "毛利率"],
    "net_margin": ["销售净利率(%)", "销售净利率", "净利率(%)", "净利率"],
    "roe": ["净资产收益率(%)", "净资产收益率", "加权净资产收益率(%)", "ROE(%)"],
    "current_ratio": ["流动比率", "流动比率(倍)"],
    "quick_ratio": ["速动比率", "速动比率(倍)"],
    "debt_ratio": ["资产负债率(%)", "资产负债率"],
    "receivable_turnover": ["应收账款周转率(次)", "应收账款周转率"],
    "inventory_turnover": ["存货周转率(次)", "存货周转率"],
    "revenue_growth": ["主营业务收入增长率(%)", "营业收入同比增长率(%)", "营收同比增长率(%)", "营业收入增长率(%)"],
    "profit_growth": ["净利润增长率(%)", "归母净利润增长率(%)"],
}

# akshare 财务指标列的百分比值通常已是百分比数字（如 35.2 表示 35.2%），
# 需要除以 100 归一化为小数，与 analyzers 计算口径（0~1）一致。
_PERCENT_KEYS = {
    "gross_margin", "net_margin", "roe", "debt_ratio", "revenue_growth", "profit_growth",
}


def _safe_akshare(func, *args, **kwargs) -> Optional[Any]:
    """安全调用 akshare，失败返回 None。"""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        logger.debug("akshare 调用失败: %s", exc)
        return None


def _median(values: List[float]) -> Optional[float]:
    """计算中位数，空列表返回 None。"""
    cleaned = [v for v in values if v is not None and v == v]  # 过滤 None 与 NaN
    if not cleaned:
        return None
    cleaned.sort()
    n = len(cleaned)
    mid = n // 2
    if n % 2 == 1:
        return cleaned[mid]
    return (cleaned[mid - 1] + cleaned[mid]) / 2


class IndustryBenchmarkProvider:
    """行业财务指标中位数提供器。

    Usage::
        provider = IndustryBenchmarkProvider()
        benchmarks = provider.get_benchmarks("半导体")
        # {"gross_margin": 0.352, "roe": 0.121, ...}
    """

    def __init__(self, max_constituents: int = _MAX_CONSTITUENTS):
        self._max_constituents = max_constituents
        self._cache: Dict[str, Dict[str, float]] = {}

    def get_benchmarks(self, industry_name: str) -> Dict[str, float]:
        """获取指定行业的财务指标中位数。

        Args:
            industry_name: 行业名称（如"半导体""化学制药"）。

        Returns:
            各指标中位数 dict，key 见 _INDICATOR_COLUMN_MAP；取数失败返回空 dict。
            百分比类指标已归一化为小数（0.352 表示 35.2%）。
        """
        if not industry_name or not industry_name.strip():
            return {}
        key = industry_name.strip()
        if key in self._cache:
            return self._cache[key]
        benchmarks = self._fetch_benchmarks(key)
        self._cache[key] = benchmarks
        return benchmarks

    def _fetch_benchmarks(self, industry_name: str) -> Dict[str, float]:
        """实际拉取并计算中位数。"""
        try:
            import akshare as ak
        except ImportError:
            logger.warning("akshare 未安装，行业基准中位数不可用")
            return {}

        constituents = self._get_constituents(ak, industry_name)
        if not constituents:
            return {}

        # 收集每个指标的成分股数值列表
        bucket: Dict[str, List[float]] = {k: [] for k in _INDICATOR_COLUMN_MAP}

        for code in constituents[: self._max_constituents]:
            indicator_df = _safe_akshare(
                ak.stock_financial_analysis_indicator,
                symbol=code,
                start_year=str(_latest_report_year()),
            )
            if indicator_df is None or getattr(indicator_df, "empty", True):
                continue
            # 取最新一行
            try:
                latest_row = indicator_df.iloc[-1]
            except Exception:
                continue
            for bench_key, columns in _INDICATOR_COLUMN_MAP.items():
                raw = _pick_column_value(latest_row, columns)
                if raw is not None:
                    bucket[bench_key].append(raw)

        result: Dict[str, float] = {}
        for bench_key, values in bucket.items():
            med = _median(values)
            if med is None:
                continue
            # 百分比归一化：akshare 返回 35.2 表示 35.2%，analyzers 用 0.352
            if bench_key in _PERCENT_KEYS:
                med = med / 100.0
            result[bench_key] = round(med, 4)

        if result:
            logger.info(
                "行业基准中位数取数成功: industry=%s constituents=%d indicators=%d",
                industry_name, len(constituents), len(result),
            )
        return result

    def _get_constituents(self, ak_module: Any, industry_name: str) -> List[str]:
        """获取东方财富行业板块成分股代码列表。

        先按原始行业名直接查；若查不到成分股，则归一化并通过
        ``industry_market_data_tool._map_to_index_symbol`` 映射到标准东方财富
        板块名再查（如"半导体/集成电路产业链"→"半导体"），最大化命中率。
        """
        # 优先用东方财富行业板块成分股接口（原始行业名）
        df = _safe_akshare(
            ak_module.stock_board_industry_cons_em,
            symbol=industry_name,
        )
        codes = self._extract_codes(df)
        if codes:
            return codes

        # 回退：映射到标准东方财富板块名再试
        mapped = self._map_industry_to_board(industry_name)
        if mapped and mapped != industry_name:
            df = _safe_akshare(
                ak_module.stock_board_industry_cons_em,
                symbol=mapped,
            )
            codes = self._extract_codes(df)
            if codes:
                return codes
        return []

    @staticmethod
    def _extract_codes(df: Any) -> List[str]:
        """从成分股 DataFrame 提取 6 位股票代码列表。"""
        if df is None or getattr(df, "empty", True):
            return []
        code_col = None
        for col in ["代码", "symbol", "code"]:
            if col in df.columns:
                code_col = col
                break
        if not code_col:
            return []
        return [str(c).zfill(6) for c in df[code_col].tolist() if c]

    @staticmethod
    def _map_industry_to_board(industry_name: str) -> Optional[str]:
        """把任意行业名映射到东方财富板块名；失败返回 None。"""
        try:
            from app.agents.tools.industry_market_data_tool import _map_to_index_symbol

            return _map_to_index_symbol(industry_name)
        except Exception:
            return None


def _pick_column_value(row: Any, candidate_columns: List[str]) -> Optional[float]:
    """从 DataFrame 行里按候选列名取首个可用数值。"""
    for col in candidate_columns:
        if col in row.index:
            val = row[col]
            return _to_float(val)
    return None


def _to_float(val: Any) -> Optional[float]:
    """把 akshare 返回的指标值转成 float，非法返回 None。"""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def _latest_report_year() -> int:
    """取最近一个完整财年的年份（用于财务指标拉取起始年）。"""
    from datetime import datetime
    # 简单取当前年份，akshare 会返回最近若干期，我们只取最新一行
    return datetime.now().year - 1


# ── 全局单例，供 analyzers 默认使用 ──────────────────────────────
_default_provider: Optional[IndustryBenchmarkProvider] = None


def get_default_provider() -> IndustryBenchmarkProvider:
    """获取进程级默认 provider 单例。"""
    global _default_provider
    if _default_provider is None:
        _default_provider = IndustryBenchmarkProvider()
    return _default_provider


def get_industry_benchmarks(industry_name: str) -> Dict[str, float]:
    """便捷函数：用默认 provider 取行业基准中位数。"""
    return get_default_provider().get_benchmarks(industry_name)
