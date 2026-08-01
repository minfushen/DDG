# P0-1 第三阶段：HITL 原生 interrupt() 迁移方案

> 本文是 P0-1 第二阶段评估的产出。结论：HITL 原生 `interrupt()` 在现有架构下需独立大重构，
> 不宜与"自动续跑"合并冒险。建议作为 P0-1 第三阶段单独推进。

---

## 一、现有 HITL 架构（基于代码核实）

### 挂起机制
- `run_deepresearch_task_background`（`tasks.py:304`）在 prepare 后 **`return` 结束协程**（不是 await 阻塞）
- 靠内存 `tasks[task_id]` 字典保存状态 + `asyncio.Event` 通知 SSE
- 恢复靠 `schedule_task_background`（`tasks.py:465`）**重入同一函数**，用 `plan_approved`/`approved_research_state` 标志位跳过已完成阶段

### 4 个中断点
| 中断 | 时机 | 是否在图执行流内 |
|---|---|---|
| `confirm_entity` | `create_task` 同步阶段（图未跑） | ❌ 无法迁图内 |
| `approve_plan` | prepare 后、execute 前 | ⚠️ 图已 END，需合并 |
| `approve_gap` | execute 后、报告发布前 | ⚠️ execute 已 END，需合并 |
| `upload_material` | 财报上传流程（文件 IO） | ❌ 无法迁图内 |

### resume 契约
- `POST /tasks/{id}/interrupts/{id}/resume`（通用）+ `POST /tasks/{id}/resume`（财报）
- 前端传 `{resolution:{action,...}}`，按 action 分支
- **不调 `resume_deep_research`**，走 schedule 重入

---

## 二、原生 interrupt() 的根本冲突

LangGraph `interrupt()` 要求：
1. 图是**连续流**（prepare→interrupt→execute→...→interrupt→END）
2. 一次 `ainvoke` 跑到 interrupt 自然暂停，checkpoint 保存
3. 恢复用 `ainvoke(Command(resume=value), config=thread_id)` 续跑

现有架构是**两次独立 ainvoke**（prepare→END，execute→END）+ **return 挂起** + **schedule 重入**。两者不兼容。

### 迁移必须的改动
1. **合并图拓扑**：去掉 `phase` 路由，改为 `prepare→plan_approval_interrupt→execute_round1→...→synthesize→gap_approval_interrupt→END` 连续流
2. **执行模型重构**：`run_deepresearch_task_background` 从"return 挂起 + schedule 重入"改为"ainvoke 跑到 interrupt + Command resume 续跑"
3. **resume 端点重构**：`approve_plan`/`approve_gap` 的 resume 从 schedule 重入改为 `ainvoke(Command(resume))`
4. **中断数据结构**：`interrupt()` 返回值替代 `active_interrupt`，但前端契约（`/interrupts/{id}/resume` + `resolution.action`）需保持兼容
5. **混合架构**：`confirm_entity`/`upload_material` 保留 tasks.py 层（不在图内），与图内 interrupt 共存

### 不可迁移的中断点
- `confirm_entity`：create_task 同步阶段，图未启动 → 永远保留 tasks.py 层
- `upload_material`：涉及文件上传+解析，不在图执行流 → 永远保留 tasks.py 层

---

## 三、风险评估

| 风险 | 等级 | 说明 |
|---|---|---|
| 破坏端到端流程 | 极高 | 执行模型从"return挂起"改为"interrupt暂停"，触及核心调度 |
| 前端契约破坏 | 高 | SSE 中断信号、resume 接口路径/action 语义可能变 |
| 双路径维护 | 中 | 混合架构（图内 interrupt + tasks.py 层 interrupt）复杂度上升 |
| checkpoint 与 interrupt 配合 | 中 | 需验证 interrupt 暂停时 checkpoint 正确保存、Command resume 正确续跑 |
| 测试覆盖不足 | 高 | 4 个中断点的中断-恢复路径都要重测 |

**工作量估算**：3-5 天（含测试）

---

## 四、建议推进方式

### 方式 A：独立大重构（推荐）
作为 P0-1 第三阶段单独推进，先写详细设计 + 充分测试，再切换。不与其它功能并行。

### 方式 B：approve_plan 单点试点（次选）
只迁 `approve_plan` 到图内 interrupt，用 `ENABLE_NATIVE_INTERRUPT` feature flag 控制：
- 默认 False：走现有 tasks.py 层 HITL（不破坏流程）
- True：prepare 节点内调 `interrupt()`，resume 用 `Command(resume)`
- 验证原生 interrupt + checkpointer 配合可行后，再迁 approve_gap

代价：双路径代码维护，flag 开启时仍要改执行模型。

### 方式 C：维持现状（不推荐）
保留 tasks.py 层 HITL，仅用 P0-1 第一阶段的 checkpointer 做 execute 中途崩溃恢复（自动续跑已覆盖此场景）。HITL 中断仍走 return挂起+schedule重入。
- 代价：HITL 中断不享受 LangGraph 原生 interrupt 的 checkpoint 一致性，但现有机制可用。

---

## 五、与自动续跑的关系

P0-1 第二阶段的"自动续跑"已实现（`tasks.automatic_resume_crashed_tasks`）：
- 进程重启后，`agent_state` 处于执行中途（calling_tools/analyzing/...）且无活跃 HITL 中断的任务，自动调 `resume_deep_research(task_id)` 从 checkpoint 断点续跑
- HITL 等待中（waiting_human）和已完成的任务不续跑
- 这覆盖了"execute 中途崩溃恢复"场景，与 HITL 中断迁移正交

即：**自动续跑解决"崩溃恢复"，HITL 原生 interrupt 解决"中断一致性"**，两者独立。自动续跑已闭环崩溃恢复，HITL 迁移可按本方案独立推进。

---

## 六、结论

HITL 原生 interrupt() 是有价值的演进（统一中断模型、享受 checkpoint 一致性），但在现有"两次 ainvoke + return挂起"架构下需重构执行模型，风险极高。建议：
1. **当前**：自动续跑已实现，崩溃恢复闭环
2. **下一步**：按方式 A 独立推进 HITL 原生 interrupt 重构（P0-1 第三阶段），不在高风险下盲目合并
