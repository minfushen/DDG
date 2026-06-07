# backend/tests/test_intent_router.py
"""意图路由器测试"""
import pytest
from app.agents.intent_router import IntentRouter, IntentResult


@pytest.fixture
def router():
    """创建路由器实例"""
    return IntentRouter()


def test_intent_result_model():
    """测试 IntentResult 模型"""
    result = IntentResult(
        intent="analyze",
        confidence=0.9,
        entities={"enterprise_name": "测试企业"},
        reasoning="测试",
    )
    assert result.intent == "analyze"
    assert result.confidence == 0.9
    assert result.entities["enterprise_name"] == "测试企业"


def test_fallback_分析意图(router):
    """测试降级方案 - 分析意图"""
    result = router._fallback_intent识别("帮我分析一下腾讯的财报")
    assert result.intent == "analyze"
    assert result.confidence == 0.8


def test_fallback_解读意图(router):
    """测试降级方案 - 解读意图"""
    result = router._fallback_intent识别("为什么毛利率下降了")
    assert result.intent == "explain"
    assert result.confidence == 0.8


def test_fallback_报告意图(router):
    """测试降级方案 - 报告意图"""
    result = router._fallback_intent识别("生成报告")
    assert result.intent == "report"
    assert result.confidence == 0.8


def test_fallback_知识意图(router):
    """测试降级方案 - 知识意图"""
    result = router._fallback_intent识别("应收账款周转天数的行业标准是多少")
    assert result.intent == "knowledge"
    assert result.confidence == 0.8


def test_fallback_聊天意图(router):
    """测试降级方案 - 聊天意图"""
    result = router._fallback_intent识别("你好")
    assert result.intent == "chat"
    assert result.confidence == 0.6


def test_extract_entities(router):
    """测试实体提取"""
    entities = router._extract_entities("帮我分析腾讯公司的财报")
    # 简单的实体提取测试
    assert isinstance(entities, dict)
