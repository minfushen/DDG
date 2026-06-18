# backend/app/main.py
"""FastAPI 主应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api import tasks
from app.api import upload
from app.api import report_quality
from app.api.task_store import init_task_store, load_recent_task_snapshots, task_store_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📁 输出目录: {settings.OUTPUT_DIR}")
    print(f"📁 数据库目录: {settings.DB_DIR}")

    # 确保输出目录存在
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    settings.DB_DIR.mkdir(parents=True, exist_ok=True)

    init_task_store()
    restored = 0
    for task in load_recent_task_snapshots():
        task_id = task.get("task_id")
        if not task_id:
            continue
        tasks.tasks[task_id] = tasks.normalize_task_snapshot(task)
        tasks.task_events[task_id] = tasks.asyncio.Event()
        restored += 1
    print(f"📦 任务快照库: {task_store_path()}")
    print(f"♻️ 已恢复任务快照: {restored}")

    yield

    # 关闭时执行
    print(f"🛑 关闭 {settings.APP_NAME}")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="尽调智能体平台后端 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册当前产品形态需要的路由
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(report_quality.router, prefix="/api/v1", tags=["report-quality"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "services": {
            "api": "running",
            "rebecca_engine": "available",
            "langgraph_agent": "available",
            "rag_knowledge": "available",
        },
    }
