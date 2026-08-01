# Phase 2：L1 Enterprise Hardening 详细设计

> 对应实施计划：`docs/product/21-prd-v1-implementation-plan.md` Phase 2  
> 目标：在继续扩展 Agent 能力之前，先把 DDG Agent 从 PoC 形态升级为可交付的私有化产品底座。

---

## 1. 设计原则

1. **向后兼容**：当前 SQLite 快照机制保留为开发/演示回退；生产环境切 PostgreSQL。
2. **最小侵入**：JWT、限流、可观测均通过 FastAPI `Depends` 和中间件注入，不破坏现有业务逻辑。
3. **单租户优先**：L1 为单租户私有化，用户表仅用于登录隔离，不做复杂 RBAC。
4. **可观测不绑定商业服务**：Langfuse/Prometheus/Grafana 均通过环境变量启用，缺省时系统仍可运行。

---

## 2. JWT 认证设计

### 2.1 用户模型

```python
# backend/app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

L1 不开放注册；用户通过管理命令或初始化 SQL 创建：

```bash
cd backend
./venv/bin/python -m app.commands.create_user --username admin --password xxx
```

### 2.2 Token 策略

- **Access Token**：JWT，有效期 24 小时（L1 私有化场景可接受）。
- **Refresh Token**：JWT，有效期 7 天，存储于 `refresh_tokens` 表（支持吊销）。
- 算法：`HS256`，密钥来自 `settings.SECRET_KEY`。
- Payload：`{ "sub": user_id, "username": username, "type": "access" | "refresh" }`。

### 2.3 API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/auth/login` | 用户名密码 → access_token + refresh_token |
| POST | `/api/v1/auth/refresh` | refresh_token → 新的 access_token |
| POST | `/api/v1/auth/logout` | 吊销 refresh_token |
| GET | `/api/v1/auth/me` | 返回当前用户信息 |

### 2.4 依赖注入

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config.settings import settings
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not settings.AUTH_ENABLED:
        return None
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    user_id = int(payload.get("sub"))
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user
```

`settings.AUTH_ENABLED` 默认 `false` 用于本地开发；生产环境通过 `.env` 开启。

### 2.5 受保护路由

所有业务路由统一加依赖：

```python
# backend/app/api/tasks.py
from app.api.deps import get_current_user
from app.models.user import User

@router.post("/tasks")
async def create_task(
    request: CreateTaskRequest,
    current_user: User | None = Depends(get_current_user),
):
    ...
```

`task` 记录增加 `user_id` 字段，实现任务数据按用户隔离。

---

## 3. PostgreSQL 持久化设计

### 3.1 目录结构

```text
backend/app/db/
├── __init__.py
├── base.py          # declarative base
├── session.py       # AsyncSession + engine
└── init_db.py       # 创建表（dev 用；生产用 Alembic）

backend/app/models/
├── __init__.py
├── user.py
├── task.py
├── batch_job.py
└── audit_log.py

backend/alembic/
├── env.py
├── script.py.mako
└── versions/
    └── 001_initial.py
backend/alembic.ini
```

### 3.2 配置项

```env
DATABASE_URL=postgresql+asyncpg://ddg:ddg@localhost:5432/ddg_agent
DATABASE_URL_SYNC=postgresql://ddg:ddg@localhost:5432/ddg_agent  # Alembic 使用
# 开发回退
USE_SQLITE_FALLBACK=true
SQLITE_FALLBACK_PATH=db/ddg_tasks.sqlite3
```

### 3.3 Task 表设计

```python
# backend/app/models/task.py
class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    enterprise_name = Column(String(255), nullable=False, index=True)
    objective = Column(String(255), default="完整贷前尽调")
    agent_state = Column(String(32), default="creating_task", index=True)
    report_type = Column(String(64), nullable=True)
    report_mode = Column(String(64), nullable=True)

    # 核心状态 JSONB
    research_state = Column(JSONB, nullable=True)
    approved_research_state = Column(JSONB, nullable=True)
    interrupts = Column(JSONB, default=list)
    human_actions = Column(JSONB, default=list)
    timeline = Column(JSONB, default=list)
    tool_traces = Column(JSONB, default=list)
    report = Column(JSONB, nullable=True)
    quality_evaluation = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

### 3.4 双写与回退策略

迁移阶段：

1. 保留 `backend/app/api/task_store.py` 的 SQLite 快照逻辑。
2. 新增 `TaskRepository`（`backend/app/repositories/task_repository.py`），统一读写 PostgreSQL。
3. 配置 `DATABASE_URL` 时优先写 PostgreSQL；未配置时回退 SQLite。
4. 启动恢复逻辑改为优先从 PostgreSQL 加载未完成任务。

```python
# backend/app/repositories/task_repository.py
class TaskRepository:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.fallback = SQLiteTaskStore() if settings.USE_SQLITE_FALLBACK else None

    async def get(self, task_id: str) -> dict | None:
        if self.db:
            task = await self.db.get(Task, task_id)
            if task:
                return task.to_dict()
        if self.fallback:
            return await self.fallback.get(task_id)
        return None
```

---

## 4. Alembic 迁移

### 4.1 alembic.ini 关键配置

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://ddg:ddg@localhost:5432/ddg_agent
```

### 4.2 alembic/env.py 要点

- 导入 `app.models.*` 和 `app.db.base.Base` 作为 `target_metadata`。
- 运行时使用 `settings.DATABASE_URL_SYNC` 覆盖 URL。
- 支持 async 迁移：`run_migrations_online` 使用 `create_async_engine` 与 `AsyncConnection`。

### 4.3 初始 migration（001_initial.py）

创建表：
- `users`
- `tasks`
- `refresh_tokens`
- `batch_jobs`
- `audit_logs`

---

## 5. 任务恢复设计

### 5.1 启动恢复流程

```python
# backend/app/main.py
@app.on_event("startup")
async def resume_interrupted_tasks():
    if not settings.DATABASE_URL:
        return
    repo = TaskRepository()
    active_states = {"gathering", "analyzing", "report_ready", "waiting_human"}
    tasks = await repo.list_by_states(active_states, limit=100)
    for task_dict in tasks:
        asyncio.create_task(resume_task_lifecycle(task_dict["id"]))
```

### 5.2 恢复入口

复用 `backend/app/api/tasks.py` 中的 resume/interrupt 逻辑：

```python
async def resume_task_lifecycle(task_id: str):
    task = await task_repository.get(task_id)
    if not task:
        return
    if task["agent_state"] == "waiting_human":
        # 仅恢复 SSE 监听，等待人工操作
        return
    # 否则继续执行 DeepResearch graph
    await run_deep_research_due_diligence(...)
```

### 5.3 幂等性保证

- 每个任务在内存 `tasks` dict 中只能有一个运行实例；恢复时检查是否已在运行。
- LangGraph checkpoint 在 Phase 3 接入后，恢复将更可靠；当前阶段通过 `research_state` 全量快照恢复。

---

## 6. API 限流设计

### 6.1 技术选型

- `slowapi` + `limits`（内存存储 `MemoryStorage`）。
- 生产可切 `RedisStorage`（需额外部署 Redis，L1 先不强制）。

### 6.2 限流规则

```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# 通用：每 IP 60 次/分钟
DEFAULT_LIMIT = "60/minute"

# 认证：每 IP 10 次/分钟，防止爆破
AUTH_LIMIT = "10/minute"
```

### 6.3 接入 FastAPI

```python
# backend/app/main.py
from app.middleware.rate_limit import limiter

app = FastAPI(...)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

### 6.4 路由装饰

```python
# backend/app/api/auth.py
@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, ...):
    ...

# backend/app/api/tasks.py
@router.post("/tasks")
@limiter.limit("60/minute")
async def create_task(...):
    ...
```

超限返回 `429 Too Many Requests`，响应头带 `Retry-After`。

---

## 7. 可观测性设计

### 7.1 Langfuse 追踪

```python
# backend/app/observability/langfuse_client.py
from langfuse import Langfuse
from app.config.settings import settings

langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,
) if settings.LANGFUSE_ENABLED else None

@contextmanager
def trace_research_task(task_id: str, enterprise_name: str):
    if not langfuse:
        yield None
        return
    trace = langfuse.trace(name="deep_research", id=task_id, metadata={"enterprise": enterprise_name})
    try:
        yield trace
    finally:
        trace.update(status="success" if ... else "error")
```

在 `graph_engine.py` 中每个 LLM 调用节点加 span：

```python
with trace.span(name="create_research_plan") as span:
    plan = await create_research_plan(...)
    span.update(output=plan)
```

### 7.2 Prometheus 指标

```python
# backend/app/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

task_count = Gauge("ddg_tasks_total", "Total tasks by state", ["state"])
llm_latency = Histogram("ddg_llm_duration_seconds", "LLM call latency", ["model", "node"])
tool_calls = Counter("ddg_tool_calls_total", "Tool calls", ["tool", "status"])

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

在 `tool_router.py` 和 LLM 调用处埋点：

```python
with llm_latency.labels(model=model, node=node).time():
    response = await llm.ainvoke(...)
```

### 7.3 结构化日志

```python
# backend/app/observability/logging.py
import logging
from pythonjsonlogger import jsonlogger

class DDGJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["service"] = "ddg-agent"
        log_record["request_id"] = get_current_request_id()
        log_record["user_id"] = get_current_user_id()
        log_record["task_id"] = get_current_task_id()
```

通过 FastAPI 中间件在 `request.state` 中设置 `request_id`，并用 `contextvars` 传播到业务代码。

### 7.4 Grafana 看板

新增 `infra/grafana/dashboards/ddg-agent.json`，包含面板：

- 任务状态分布（按 `ddg_tasks_total`）
- LLM 调用 P95 延迟
- 工具调用成功率
- 按路由 5xx/4xx 错误率
- 数据源健康度（自定义 Gauge）

`docker-compose.yml` 挂载该看板。

---

## 8. 配置项汇总

```env
# 认证
AUTH_ENABLED=true
SECRET_KEY=your-secret-key-at-least-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7

# 数据库
DATABASE_URL=postgresql+asyncpg://ddg:ddg@localhost:5432/ddg_agent
DATABASE_URL_SYNC=postgresql://ddg:ddg@localhost:5432/ddg_agent
USE_SQLITE_FALLBACK=true

# 限流
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_AUTH=10/minute

# 可观测
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
PROMETHEUS_ENABLED=true
STRUCTURED_LOGGING=true
```

---

## 9. 实施顺序建议

为避免一次性改动过大，建议按以下顺序落地：

1. **JWT 骨架**：`auth.py`、`deps.py`、User 模型、登录 API；默认 `AUTH_ENABLED=false`。
2. **PostgreSQL 连接**：`db/session.py`、Task 模型；与 SQLite 双写。
3. **Alembic 初始迁移**。
4. **业务路由逐步加 `Depends(get_current_user)`** 并写入 `user_id`。
5. **任务恢复**：启动时扫描未完成任务。
6. **slowapi 限流**。
7. **Langfuse + Prometheus + 结构化日志**。
8. **Grafana 看板 + Docker Compose 集成**。

---

## 10. 风险与回退

| 风险 | 回退方案 |
|---|---|
| PostgreSQL 不可用 | `USE_SQLITE_FALLBACK=true` 继续用 SQLite |
| JWT 配置错误 | `AUTH_ENABLED=false` 跳过认证 |
| Langfuse 连不上 | 环境变量关闭，日志降级为本地 JSON |
| 限流误伤 | 提高阈值或按用户 ID 而非 IP 限流 |

---

## 11. 与 Phase 3/4 的衔接

- Phase 3 的 LangGraph native checkpoint 将复用本阶段的 PostgreSQL 连接池，把 checkpoint 写入独立表 `langgraph_checkpoints`。
- Phase 4 的 `batch_jobs` 表在本阶段已创建，APScheduler 只需写入即可。
- Phase 4 的 `pgvector` 记忆后端将复用本阶段 `User`/`Task` 模型中的 `tenant_id`/`user_id` 字段做隔离。

---

## 12. 关键接口草案

### POST /api/v1/auth/login

Request:
```json
{
  "username": "admin",
  "password": "xxx"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### POST /api/v1/tasks（加认证后）

Header: `Authorization: Bearer eyJ...`

Response 增加 `user_id`，任务数据按用户隔离。

### GET /metrics

返回 Prometheus 文本格式。

### GET /health

扩展为检查 PostgreSQL 连接：

```json
{
  "status": "healthy",
  "database": "ok",
  "queue": "ok"
}
```
