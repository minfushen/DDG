# DDG Agent Backend - 尽调智能体后端

## 项目简介

尽调智能体平台后端服务，基于 FastAPI 构建，集成 Rebecca 规则引擎和 LangGraph Agent 进行智能财务分析。

## 技术栈

- **Web 框架**: FastAPI 0.110+
- **Agent 框架**: LangGraph 0.2+（状态图编排）
- **LLM 集成**: LangChain + DashScope (qwen-max)
- **规则引擎**: Rebecca（10 维度财务分析）
- **向量库**: ChromaDB（RAG 知识检索）
- **数据处理**: Pandas, NumPy
- **文档生成**: python-docx

## 目录结构

```
backend/
├── app/
│   ├── api/              # API 路由
│   │   ├── analysis.py   # 分析接口
│   │   ├── chat.py       # 对话接口
│   │   └── knowledge.py  # 知识库接口
│   ├── config/           # 配置管理
│   ├── engines/
│   │   └── rebecca/      # Rebecca 规则引擎
│   ├── models/           # 数据模型
│   ├── agents/           # LangGraph Agent
│   │   ├── state.py      # Agent 状态定义
│   │   ├── intent_router.py  # 意图识别
│   │   ├── due_diligence_agent.py  # 尽调 Agent
│   │   └── tools/        # Agent 工具
│   └── rag/              # RAG 知识库
│       ├── vector_store.py   # 向量存储
│       ├── knowledge_base.py # 知识库
│       └── retriever.py      # 检索器
├── knowledge_base/       # 知识文档
│   ├── regulations/      # 法规文档
│   ├── industry_guides/  # 行业指南
│   ├── case_studies/     # 案例库
│   └── risk_frameworks/  # 风险框架
├── tests/                # 单元测试
├── output/               # 输出目录
├── db/                   # 数据库目录
├── requirements.txt      # 依赖清单
└── run.py                # 启动脚本
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件配置 LLM API Key 等参数
```

### 3. 启动服务

```bash
python run.py
```

服务启动后访问：
- API 文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## API 接口

### 1. 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径 |
| GET | `/health` | 健康检查 |

### 2. 分析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/analysis/parse` | 解析财报文件 |
| POST | `/api/v1/analysis/analyze` | 执行财务分析 |
| POST | `/api/v1/analysis/report` | 生成尽调报告 |
| GET | `/api/v1/reports/{filename}` | 下载报告文件 |

### 3. 对话接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | Agent 对话（SSE 流式） |
| POST | `/api/v1/chat/sync` | Agent 对话（同步） |

### 4. 知识库接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/knowledge/search` | 检索知识库 |
| POST | `/api/v1/knowledge/ingest` | 导入知识文档 |
| POST | `/api/v1/knowledge/ingest-directory` | 导入知识库目录 |

## 请求示例

### 财务分析

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise_name": "测试企业",
    "financial_data": {
      "income_statement": {"revenue": 1000000000},
      "balance_sheet": {"total_assets": 5000000000},
      "cash_flow": {"operating_cash_flow": 300000000}
    }
  }'
```

### Agent 对话

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我分析一下腾讯的财报",
    "session_id": "sess_123",
    "context": {
      "enterprise_name": "腾讯"
    }
  }'
```

### 知识库检索

```bash
curl "http://localhost:8000/api/v1/knowledge/search?query=应收账款&knowledge_type=regulation&top_k=5"
```

## 测试

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_analysis_api.py

# 运行测试并显示覆盖率
pytest --cov=app
```

## 开发计划

- **M1**: 后端基础 + Rebecca 集成 ✅
- **M2**: LLM Agent 集成（LangGraph）✅
- **M3**: RAG 知识库（ChromaDB）✅
- **M4**: 前端对话界面 ✅
- **M5**: 联调优化 ✅

## 架构说明

### Agent 工作流

```
用户输入 → 意图识别 → Agent 决策 → 工具调用 → 结果整合 → 流式输出
                ↓
        ┌───────┴───────┐
        ↓       ↓       ↓
    分析工具  解读工具  知识工具
        ↓       ↓       ↓
    Rebecca   LLM     ChromaDB
```

### 10 维度分析

1. 盈利能力
2. 偿债能力
3. 营运能力
4. 成长能力
5. 现金流分析
6. 成本结构
7. 资产质量
8. 负债结构
9. 盈利趋势
10. 风险评估
