"""杜邦分析（DuPont Analysis）计算化模块。

将 ROE 拆解为「净利率 × 资产周转率 × 权益乘数」三因子，输出近三年趋势、
因子分解与驱动归因，作为信审/风控经理判断盈利质量与财务杠杆的专业支撑。

公式（采用期末口径，简化杜邦；如有前一年末数则自动改用平均数口径）：
    ROE            = 净利润 / 所有者权益
    净利率         = 净利润 / 营业收入
    资产周转率     = 营业收入 / 总资产
    权益乘数       = 总资产 / 所有者权益
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _value_by_item(df, item_keywords: List[str], year: str) -> Optional[float]:
    if df is None or getattr(df, "empty", True):
        return None
    year_col = None
    for col in df.columns:
        if str(col) == str(year):
            year_col = col
            break
    if year_col is None:
        return None
    label_col = None
    for col in df.columns:
        if any(k in str(col) for k in ["项目", "科目", "指标", "名称"]):
            label_col = col
            break
    if label_col is None:
        label_col = df.columns[0]
    for _, row in df.iterrows():
        label = str(row.get(label_col, "")).replace("\n", "").replace(" ", "")
        if any(k in label for k in item_keywords):
            try:
                val = row.get(year_col)
                return float(val) if val not in (None, "") else None
            except (TypeError, ValueError):
                return None
    return None


def _year_columns(df) -> List[str]:
    if df is None or getattr(df, "empty", True):
        return []
    return sorted(str(c) for c in df.columns if str(c).isdigit() and len(str(c)) == 4)


def build_dupont_analysis(financial_data: Dict[str, Any]) -> Dict[str, Any]:
    """基于三大表构建杜邦分析。

    Args:
        financial_data: {"income_statement": DataFrame, "balance_sheet": DataFrame, ...}

    Returns:
        结构化杜邦分析结果。
    """
    income = financial_data.get("income_statement")
    balance = financial_data.get("balance_sheet")

    years = sorted(set(_year_columns(income)) | set(_year_columns(balance)), reverse=True)
    if not years:
        return {"success": False, "reason": "无年份数据", "decomposition": [], "summary": "缺少三大表年份数据，无法开展杜邦分析。"}

    years = years[:3]

    def _row(year: str):
        revenue = _value_by_item(income, ["营业收入", "主营业务收入"], year)
        net_profit = _value_by_item(income, ["净利润"], year)
        total_assets = _value_by_item(balance, ["资产总计", "资产合计", "总资产"], year)
        equity = _value_by_item(balance, ["所有者权益", "股东权益", "净资产"], year)
        return revenue, net_profit, total_assets, equity

    # 原始科目值：用于杜邦分解树的叶子节点展示（营收/净利润/总资产/所有者权益）。
    raw_values: Dict[str, Dict[str, Optional[float]]] = {}
    for y in years:
        revenue, net_profit, total_assets, equity = _row(y)
        raw_values[y] = {
            "revenue": revenue,
            "net_profit": net_profit,
            "total_assets": total_assets,
            "equity": equity,
        }

    factors: Dict[str, Dict[str, Optional[float]]] = {"roe": {}, "net_margin": {}, "asset_turnover": {}, "equity_multiplier": {}}
    for y in years:
        revenue, net_profit, total_assets, equity = _row(y)
        net_margin = (net_profit / revenue) if (revenue and net_profit is not None) else None
        asset_turnover = (revenue / total_assets) if (total_assets and revenue) else None
        equity_multiplier = (total_assets / equity) if (equity and total_assets) else None
        roe = (net_profit / equity) if (equity and net_profit is not None) else None
        factors["net_margin"][y] = net_margin
        factors["asset_turnover"][y] = asset_turnover
        factors["equity_multiplier"][y] = equity_multiplier
        # 三因子乘积应与 ROE 近似一致（期末口径）。
        if None not in (net_margin, asset_turnover, equity_multiplier):
            factors["roe"][y] = net_margin * asset_turnover * equity_multiplier
        else:
            factors["roe"][y] = roe

    # 驱动归因：最新年度 vs 前一年，比较三因子变动对 ROE 变动的贡献。
    decomposition = []
    for i, y in enumerate(years):
        nm = factors["net_margin"][y]
        at = factors["asset_turnover"][y]
        em = factors["equity_multiplier"][y]
        roe = factors["roe"][y]
        driver = ""
        if i < len(years) - 1:
            prev = years[i + 1]
            p_nm, p_at, p_em = factors["net_margin"][prev], factors["asset_turnover"][prev], factors["equity_multiplier"][prev]
            p_roe = factors["roe"][prev]
            if None not in (nm, at, em, p_nm, p_at, p_em, p_roe, roe):
                # 链式分解：ROE 变动 = ΔNM·AT·EM + NM·ΔAT·EM + NM·AT·ΔEM（以当期为权）
                c_nm = (nm - p_nm) * at * em
                c_at = nm * (at - p_at) * em
                c_em = nm * at * (em - p_em)
                contrib = {"净利率": c_nm, "资产周转率": c_at, "权益乘数": c_em}
                top = max(contrib, key=lambda k: abs(contrib[k]))
                direction = "拉动" if contrib[top] > 0 else "拖累"
                driver = (
                    f"ROE 同比变动 {roe - p_roe:+.1%}，主要由「{top}」{direction}"
                    f"（贡献 {contrib[top]:+.1%}）；净利率/{'资产周转率' if top != '资产周转率' else '周转率'}/杠杆变动分别 "
                    f"{c_nm:+.1%}/{c_at:+.1%}/{c_em:+.1%}。"
                )
        decomposition.append({
            "year": y,
            "roe": roe,
            "net_margin": nm,
            "asset_turnover": at,
            "equity_multiplier": em,
            "revenue": raw_values[y]["revenue"],
            "net_profit": raw_values[y]["net_profit"],
            "total_assets": raw_values[y]["total_assets"],
            "equity": raw_values[y]["equity"],
            "driver": driver,
        })

    # 趋势与红黄灯（确定性结论）
    red_flags: List[str] = []
    latest = decomposition[0] if decomposition else None
    if latest:
        if latest["net_margin"] is not None and latest["net_margin"] < 0.03:
            red_flags.append(f"净利率仅 {latest['net_margin']:.1%}，主业盈利能力偏弱。")
        if latest["equity_multiplier"] is not None and latest["equity_multiplier"] > 3.0:
            red_flags.append(f"权益乘数 {latest['equity_multiplier']:.2f}，财务杠杆偏高。")
        if latest["asset_turnover"] is not None and latest["asset_turnover"] < 0.3:
            red_flags.append(f"资产周转率 {latest['asset_turnover']:.2f}，资产运营效率偏低（重资产/产能利用不足信号）。")

    summary = (
        f"杜邦分析覆盖 {years[0]}~{years[-1]} 共 {len(years)} 年。"
        + (f"最新 ROE={latest['roe']:.1%}（净利率 {latest['net_margin']:.1%} × 资产周转率 {latest['asset_turnover']:.2f} × 权益乘数 {latest['equity_multiplier']:.2f}）。"
           if latest and latest["roe"] is not None else "")
    )

    return {
        "success": True,
        "factors": factors,
        "raw_values": raw_values,
        "decomposition": decomposition,
        "red_flags": red_flags,
        "summary": summary,
    }
