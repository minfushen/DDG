# 04 测试记录与 Bug 修复日志

## 测试范围

本阶段测试覆盖：

- 前端输入到后端创建任务。
- 后端意图解析、任务状态流转、SSE/状态更新。
- 单 Agent 财务分析。
- 非上市企业上传财报分析。
- 上市公司完整尽调。
- 完整报告页展示。
- RAG 检索和 Evidence Store 输出。
- LLM 诊断式文本生成与 fallback。

## 端到端链路测试

### 前端输入到任务创建

测试命令：

```bash
curl -s -w '\nHTTP=%{http_code} TIME=%{time_total}\n' \
  -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{"enterprise_name":"分析一下士兰微这个上市公司"}'
```

验证结果：

- 后端直接创建任务约 0.002s 返回。
- 前端代理创建任务约 0.005s 返回。
- 创建任务不再阻塞在 LLM 意图识别。

### 服务启动

可靠启动方式：

```bash
cd /Users/minfushen/Projects/ddg-agent/backend
venv312/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info

cd /Users/minfushen/Projects/ddg-agent
npm run dev -- --host 127.0.0.1
```

测试观察：

- 在本地桌面环境中，`nohup` 后台启动 uvicorn 有时会静默退出。
- 持久终端 session 更可靠。

## 关键 Bug 与修复记录

### Sequential Thinking MCP 最小接入测试

测试命令：

```bash
cd /Users/minfushen/Projects/ddg-agent/backend
venv312/bin/python -m py_compile app/agents/research_engine/*.py app/config/settings.py

venv312/bin/python - <<'PY'
from app.agents.research_engine import run_deep_research_due_diligence_sync
res = run_deep_research_due_diligence_sync('士兰微', max_iterations=1)
print(res['success'], res['research_state'].get('sequential_thinking'))
PY

ENABLE_SEQUENTIAL_THINKING=true SEQUENTIAL_THINKING_MCP_TIMEOUT_SECONDS=30 venv312/bin/python - <<'PY'
from app.agents.research_engine import run_deep_research_due_diligence_sync
res = run_deep_research_due_diligence_sync('士兰微', max_iterations=1)
print(res['success'], res['research_state'].get('sequential_thinking'))
PY
```

验证结果：

- 未启用时使用规则规划器，任务可正常完成。
- 启用后可通过 `npx -y @modelcontextprotocol/server-sequential-thinking` 加载 `sequentialthinking` 工具。
- Research Engine timeline 会展示 MCP 启用和计划复核状态。
- MCP 仅记录研究计划/证据缺口检查点，不直接生成结构化规划；结构化输出仍由规则 planner、reflector 和后续 LLM/RAG 节点负责。
- 测试环境未配置 `BOCHA_API_KEY` 时，公开搜索会记录配置缺失错误，但不影响 MCP 接入链路验证。

### LLM Planner 节点测试计划

实现后验证：

- `ENABLE_LLM_RESEARCH_PLANNER=false`：必须使用默认规则计划，流程正常完成。
- `ENABLE_LLM_RESEARCH_PLANNER=true` 且 LLM 可用：应生成 `planner_source=llm` 的研究计划。
- LLM 返回非 JSON、空任务、缺少必填字段：必须 fallback 到默认规则计划。
- 启用 Sequential Thinking MCP 时：MCP 只记录计划检查点，不覆盖 LLM Planner 输出。
- 创建任务接口仍需毫秒级返回，LLM Planner 不得放到同步创建任务阶段。

已完成验证：

- 关闭 `ENABLE_LLM_RESEARCH_PLANNER` 后，`planner.source=rule_fallback`，流程正常输出报告。
- 清空 `LLM_API_KEY` 后，记录 `LLM_API_KEY not configured` 并 fallback，流程不中断。
- 使用当前主 LLM 配置时出现 `APITimeoutError`，已关闭 planner 重试并确认可以 fallback。
- timeline 会展示 `LLM Planner 降级到规则计划`，便于测试时判断是否实际使用 LLM 规划。
- DeepSeek 专用 Planner 配置验证：`deepseek-v4-pro` 可用但单次规划约 32s；`deepseek-chat` 曾约 5-6s 完成结构化规划，但因模型生命周期风险，当前 Planner 默认改用 `deepseek-v4-flash`。
- `deepseek-v4-flash` 连通性验证通过，小请求约 1.5s；Planner 结构化规划约 8-10s，`planner.source=llm`。
- 完整 DeepResearch 最小任务验证：`planner.source=llm`，timeline 展示 `LLM Planner / 生成动态研究计划`。

待补验证：

- 构造 mock LLM 返回无效 JSON，验证 schema 校验和 fallback 覆盖率。

### Bug 1：首页创建任务长时间转圈

现象：

- 用户输入 `分析一下士兰微这个上市公司` 后，页面卡在“创建执行任务 / 生成任务ID并进入执行工作台”。

原因：

- 创建任务阶段曾调用 LLM 或公开搜索做意图识别。
- 后端响应没有先返回 task_id，导致前端等待。
- 前端没有展示创建失败错误，看起来像无限转圈。

修复：

- 新增 `fast_extract_user_intent()`，本地快速解析企业名和任务类型。
- `/api/v1/tasks` 创建任务后用 `schedule_task_background()` 延迟启动后台任务。
- 前端 `createTask` 展示后端错误。
- Vite proxy 改为 `127.0.0.1:8000`。

验证：

- 后端和前端代理 POST 均能毫秒级返回。

### Bug 2：执行页持续闪屏

现象：

- 任务执行页面一直闪烁，没有稳定态。

原因：

- 状态更新和渲染逻辑导致 UI 反复重绘。
- 部分 loading 状态没有进入 completed/failed 稳定状态。

修复：

- 调整执行页状态管理和 CSS。
- 确保任务节点有明确的 running/completed/failed 状态。
- 减少由 timeline 变化引发的布局抖动。

验证：

- 执行页不再持续闪烁。

### Bug 3：财务分析使用模拟数据

现象：

- 对上市公司或上传财报企业，财务报告中的指标像 mock 数据。

原因：

- 早期 `search_financial_data` 返回模拟数据。
- 上传 Excel 中的更多科目没有解析到标准字段。

修复：

- 非上市企业强制上传近三年财报。
- 支持利润表、资产负债表、现金流量表的重点科目解析。
- 指标由 `financial_report_builder.py` 从表格计算。
- LLM 只写诊断文本，不生成指标。

测试数据：

- `/tmp/ddg-hunan-second-engineering-financial/湖南省第二工程有限公司_三年财务报表_测试数据.xlsx`

验证：

- 毛利率、净利率、资产负债率、现金流等核心证据来自上传文件。

### Bug 4：财务报告文案不通顺、不专业

现象：

- 报告出现“资产持有率”“经营活动量净额”“销售额为”等不通顺表达。
- 文案只描述最新一年，缺少近三年趋势和风险归因。

原因：

- 兜底模板过于机械。
- LLM prompt 缺少财务尽调领域知识。
- 没有质量闸门识别错误术语。

修复：

- 引入财务异常信号知识库。
- `financial_narrative_writer.py` 强制输出三类诊断维度。
- Prompt 要求分析近三年趋势。
- 禁止错误表达和未授权数字。
- 前端展示 LLM/fallback 来源和质量告警。

验证：

- 单独测试湖南省第二工程有限公司上传财报时，LLM 财务叙述可通过质量闸门。

### Bug 5：行业识别将士兰微误判为贸易/进出口

现象：

- 士兰微作为半导体科技公司，行业分析显示“贸易/进出口”。

原因：

- 规则匹配过度关注经营范围中的“货物进出口、技术进出口”等通用噪声。
- 未充分使用上市公司主营业务和 LLM 语义判断。

修复：

- 新增 `industry_llm_classifier.py` 对候选行业做 LLM 裁判。
- 增加上市公司映射提示。
- 输出 `ignored_noise`，明确忽略进出口类噪声。

验证：

- 士兰微识别结果为 `3973 集成电路制造`。
- 标准路径为 `制造业 > 计算机、通信和其他电子设备制造业 > 电子器件制造 > 集成电路制造`。

### Bug 6：行业分析泛泛而谈

现象：

- 行业分析只有“竞争激烈、政策利好、市场空间广阔”等泛化描述。

原因：

- 行业知识库缺少尽调式诊断规则。
- LLM 没有被要求绑定行业 KPI、上下游、周期、政策和授信核查动作。

修复：

- 新增行业领域知识和 `industry_analysis_rules.json`。
- 新增 `industry_diagnostic_writer.py`。
- 对泛化表达设置质量闸门和改写策略。
- 半导体行业 fallback 聚焦技术节点、产能利用率、库存周期、CAPEX、折旧和现金流压力。

验证：

- 士兰微行业识别稳定。
- 当 LLM 输出空泛表达时，质量闸门拦截并 fallback。
- fallback 不编造良率和市场份额，而是标记 `[需补充]` 并给出核查动作。

### Bug 7：CrewAI / LiteLLM 限流

现象：

- 完整尽调出现 `litellm.RateLimitError: Too many requests`。

原因：

- 完整 CrewAI 流程并发/多次调用上游模型，触发限流。

修复：

- 单 Agent 任务不走 CrewAI。
- 完整尽调默认由确定性单 Agent 顺序执行。
- CrewAI 综合审查作为可选 advisory。
- `run_node_with_rate_limit_retry()` 对限流做退避重试。

### Bug 8：DuckDuckGo MCP 不稳定（已移除）

现象：

- 搜索阶段多次出现 `Failed to get the VQD`。

影响：

- 工商上下文、司法公开搜索、行业公开线索可能变慢或失败。

当前处理：

- 将搜索结果作为线索，不作为强证据。
- RAG 本地知识库和上市公司工具作为更稳定来源。
- DuckDuckGo MCP 已从主链路和默认配置移除，避免 VQD 错误拖慢任务。

后续建议：

- 优先 Exa/Tavily。
- 对工商/司法接入正式 API。

## 构建与编译验证

### CodeAct 自动质检闭环验证

覆盖点：

- 报告生成后自动调用 `evaluate_report_quality`。
- 报告顶层写入 `quality_evaluation`、`quality_score`、`quality_passed`、`quality_issues`。
- timeline 追加“报告质检”节点，展示评分和 P0/P1 问题数量。
- 手动质量评测 API 仍保持兼容。

验证命令：

```bash
cd backend
./venv312/bin/python -m py_compile app/agents/research_engine/report_quality_gate.py app/agents/research_engine/graph_engine.py app/api/tasks.py tests/test_report_quality_gate.py
./venv312/bin/python -m pytest tests/test_report_quality_gate.py tests/test_report_quality_evaluator.py tests/test_report_quality_api.py -q
```

验证结果：

- `5 passed`

后续待测：

- 真实完整尽调任务中，执行页是否能看到“报告质检”时间轴节点。
- 报告页第一屏是否需要更突出展示 `quality_score` 和 P0/P1 摘要。

前端构建：

```bash
npm run build
```

后端编译示例：

```bash
cd backend
venv312/bin/python -m py_compile app/api/tasks.py app/agents/planning/intent_extractor.py
venv312/bin/python -m py_compile app/agents/sub_agents/industry_diagnostic_writer.py app/agents/sub_agents/industry_report_builder.py app/agents/sub_agents/full_report_builder.py
```

知识库入库：

```bash
cd backend
venv312/bin/python scripts/ingest_knowledge_base.py --reset
```

## 测试结论

当前 MVP 已具备端到端可运行能力，但测试中暴露出三个仍需优先处理的问题：

1. 外部搜索通道稳定性不足。
2. 上市公司公开资料包还不够深，行业地位、诉讼公告、担保质押、研报摘要需要更稳定数据源。
3. LLM 生成质量仍需持续通过 prompt、RAG、规则和错例反馈优化。
