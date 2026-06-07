# backend/tests/conftest.py
"""测试配置"""
import pytest
import os

# 设置测试环境变量
os.environ["LLM_API_KEY"] = "test_key"
os.environ["LLM_BASE_URL"] = "https://test.example.com/v1"


@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
