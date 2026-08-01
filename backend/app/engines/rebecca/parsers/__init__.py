"""Rebecca 财报解析器包。

re-export FinancialParser / FinancialData（原 parsers.py 已迁入包内 financial_parser.py），
修复 ``from app.engines.rebecca.parsers import FinancialParser`` 失败问题。
"""
from .financial_parser import FinancialData, FinancialParser

__all__ = ["FinancialData", "FinancialParser"]
