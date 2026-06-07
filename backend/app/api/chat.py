# backend/app/api/chat.py
"""聊天 API 路由 - SSE 流式响应"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
import asyncio

from app.agents.due_diligence_agent import due_diligence_agent
from app.agents.intent_router import intent_router

router = APIRouter()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: str = Field(..., description="会话 ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class ChatResponse(BaseModel):
    """聊天响应"""
    type: str = Field(..., description="响应类型")
    content: Optional[str] = Field(None, description="响应内容")
    tool: Optional[str] = Field(None, description="工具名称")
    args: Optional[Dict] = Field(None, description="工具参数")
    result: Optional[Any] = Field(None, description="工具结果")


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Agent 对话接口（SSE 流式响应）

    支持流式输出 Agent 的思考过程和工具调用
    """
    try:
        # 提取上下文
        enterprise = None
        has_analysis = False

        if request.context:
            enterprise = request.context.get("enterprise_name")
            has_analysis = request.context.get("has_analysis", False)

        async def event_generator():
            """SSE 事件生成器"""
            try:
                # 发送思考状态
                yield f"data: {json.dumps({'type': 'thinking', 'content': '正在理解您的问题...'}, ensure_ascii=False)}\n\n"

                # 意图识别
                intent_result = await intent_router.identify_intent(
                    user_input=request.message,
                    current_enterprise=enterprise,
                    has_analysis_result=has_analysis,
                )

                # 发送意图识别结果
                yield f"data: {json.dumps({'type': 'intent', 'content': intent_result.intent, 'confidence': intent_result.confidence}, ensure_ascii=False)}\n\n"

                # 运行 Agent（流式）
                async for event in due_diligence_agent.stream(
                    user_input=request.message,
                    enterprise=enterprise,
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                # 发送完成标记
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                # 发送错误
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/sync")
async def chat_sync(request: ChatRequest):
    """
    Agent 对话接口（同步响应）

    等待 Agent 完成后返回完整结果
    """
    try:
        # 提取上下文
        enterprise = None
        if request.context:
            enterprise = request.context.get("enterprise_name")

        # 运行 Agent
        result = await due_diligence_agent.run(
            user_input=request.message,
            enterprise=enterprise,
        )

        # 提取最后一条 AI 消息
        last_message = result["messages"][-1]
        content = last_message.content if hasattr(last_message, "content") else ""

        return {
            "status": "success",
            "content": content,
            "enterprise": enterprise,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
