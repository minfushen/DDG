# DDG Agent Backend - 尽调智能体后端

## 项目简介

对公尽调智能体后端服务，基于 FastAPI 提供任务编排、SSE 执行流、财务文件上传解析和结构化报告接口。当前核心产品形态围绕四个专项 Agent 展开：工商分析、财务分析、行业分析、司法分析。

## 技术栈

- **Web 框架**: FastAPI 0.110+
- **Agent 编排**: LangGraph + CrewAI（完整尽调链路仍保留）
- **财务规则引擎**: Rebecca
- **知识检索**: ChromaDB + 本地行业/风控知识库
- **数据处理**: Pandas, NumPy, openpyxl
- **外部数据**: 东方财富公开财报、Tavily 搜索、可选权威工商/司法通道

## 目录结构

```text
backend/
├── app/
│   ├── api/
│   │   ├── tasks.py       # 任务创建、SSE 流、恢复执行、报告读取
│   │   └── upload.py      # 非上市企业财报上传与解析
│   ├── agents/
│   │   ├── orchestrator_v2.py
│   │   ├── state.py
│   │   ├── crew/          # 完整尽调链路依赖，未移除
│   │   ├── sub_agents/    # 工商/财务/行业/司法专项 Agent
│   │   └── tools/         # 数据获取、上市公司识别、行业分类、RAG 等工具
│   ├── engines/rebecca/   # 财务报表解析和指标分析
│   ├── rag/               # 本地知识库检索
│   ├── memory/            # 短期/长期记忆
│   ├── config/            # 配置管理
│   └── main.py            # FastAPI 入口
├── knowledge_base/        # 行业、风控、法规、模板知识文档
├── tests/                 # 单元测试
├── output/                # 上传文件、生成结果等运行时输出
├── db/                    # 本地运行时数据
├── requirements.txt
└── run.py
```

## 快速开始

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

服务启动后访问：

- API 文档: http://localhost:8000/docs
- ReDoc 文档: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## API 接口

### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径 |
| GET | `/health` | 健康检查 |

### 任务接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasks` | 创建尽调或专项分析任务 |
| GET | `/api/v1/tasks/{task_id}/stream` | SSE 流式获取任务执行状态 |
| GET | `/api/v1/tasks/{task_id}` | 获取任务状态快照 |
| POST | `/api/v1/tasks/{task_id}/resume` | 上传财报解析后恢复等待中的财务任务 |
| GET | `/api/v1/tasks/{task_id}/report` | 获取结构化报告 |

### 财报上传接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/upload/financial` | 上传 Excel、CSV 或 PDF 财报文件 |
| GET | `/api/v1/upload/{task_id}/files` | 获取任务已上传文件列表 |
| POST | `/api/v1/upload/{task_id}/parse` | 解析已上传财报并返回标准化三大表数据 |

## 请求示例

### 创建任务

```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{"enterprise_name":"分析一下欣旺达的财务风险情况"}'
```

### 订阅执行流

```bash
curl -N "http://localhost:8000/api/v1/tasks/{task_id}/stream"
```

### 上传并解析非上市公司财报

```bash
curl -X POST "http://localhost:8000/api/v1/upload/financial" \
  -F "task_id={task_id}" \
  -F "document_type=auto" \
  -F "file=@/path/to/三年财务报表.xlsx"

curl -X POST "http://localhost:8000/api/v1/upload/{task_id}/parse"
```

## 测试

```bash
cd backend
source venv/bin/activate
pytest
```

当前本地 `venv312` 可能未安装 pytest，可先执行 `pip install pytest` 或使用项目配置的虚拟环境。

## 当前 Agent 能力

- **财务分析**: 上市公司自动获取公开财报；非上市公司强制上传近三年财报，解析三大表并生成银行风格财务报告。
- **工商分析**: 优先接权威工商通道，失败后使用 Tavily 搜索聚合工商基础信息和风险信号。
- **行业分析**: 使用 `industry_code4.json` 行业代码库分类，并结合本地行业知识库生成景气度、竞争格局、政策环境、授信审查重点等内容。
- **司法分析**: 探测裁判文书网、执行信息公开网等权威来源，并用 Tavily 搜索做公开司法风险兜底。
