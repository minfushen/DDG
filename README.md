# 对公尽调智能体平台 (DDG Agent)

面向对公信贷场景的 AI 尽调工作台，用户输入企业名称后，Agent 自动完成工商、财务、司法、行业分析并生成授信建议报告。

## 产品形态

极简 3 页流程：

| 页面 | 路由 | 设计风格 | 说明 |
|---|---|---|---|
| **入口页** | `/` | ChatGPT 风格 | 单一输入框，输入企业名称即开始尽调 |
| **执行页** | `/execution/:taskId?name=xxx` | Manus 风格 | 左侧计划 + 中央时间轴 + 右侧证据，SSE 流式展示 Agent 执行过程 |
| **报告页** | `/report/:taskId` | DeepResearch 风格 | 授信建议（真实数据）+ 风险评级/财务/司法/行业（参考数据）+ 附件证据 |

## 技术栈

- **框架**：React 19 + TypeScript 6
- **构建工具**：Vite 8
- **样式系统**：TailwindCSS v4
- **路由**：React Router v7
- **图标**：Lucide React

## 快速开始

```bash
npm install
npm run dev
```

前端运行在 `http://localhost:5173`，API 请求通过 Vite proxy 代理到后端 `http://localhost:8000`。

## 后端服务

见 `backend/README.md`。后端基于 FastAPI + LangGraph，提供：

- `POST /api/v1/tasks` — 创建尽调任务
- `GET /api/v1/tasks/:id/stream` — SSE 流式执行状态
- `GET /api/v1/tasks/:id/report` — 获取尽调报告

## 目录结构

```text
src/
├── pages/
│   └── AgentWorkbench/
│       ├── AgentWorkbench.tsx      # 首页入口
│       └── ExecutionWorkspace.tsx  # Agent 执行页
│   └── Report/
│       └── index.tsx               # 尽调报告页
├── services/
│   └── agentApi.ts                 # 后端 API 对接（任务/流式/报告/上传）
├── styles/                         # CSS 样式（被 index.css 引用）
├── App.tsx                         # 路由定义（3 个路由）
├── main.tsx                        # 应用入口
└── index.css                       # 全局样式 + Tailwind
```

## 前后端数据流

```
用户输入企业名
    ↓
POST /api/v1/tasks → 获取 task_id
    ↓
GET /api/v1/tasks/:id/stream (SSE) → 实时接收 Agent 状态
    ↓
状态: creating_task → planning → calling_tools → analyzing → forming_conclusion → generating_report → waiting_confirm
    ↓
GET /api/v1/tasks/:id/report → 获取最终报告
```

## 已知限制

- 后端 LLM 调用依赖外部 API Key，余额不足时会回退到默认计划并生成简化报告
- 报告页风险评级、财务指标、司法风险、行业分析等章节当前展示行业基准参考数据，待后端数据丰富后逐步替换为真实分析结果

## 相关文档

- `backend/README.md` — 后端架构、API 文档、Agent 工作流
