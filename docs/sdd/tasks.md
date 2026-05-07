# 任务清单（Tasks）

> 本文是**当前迭代**的可执行任务表。每个任务必须能链接到 [`spec.md`](./spec.md) 或 [`plan.md`](./plan.md) 的条目。
>
> 完成的任务移入"已完成归档"，过期未启动的任务在每周清理。

---

## 0. 任务编号规则

```
TASK-<MILESTONE>-<编号>
```

例如 `TASK-M1-03`、`TASK-M2-12`。

每条任务字段：

- **关联**：`[spec-XX]` 或 `[plan-§Y]` 或 `[ADR-NNN]`
- **类型**：feat / fix / refactor / docs / chore / test
- **优先级**：P0（阻塞迭代）/ P1（迭代内必做）/ P2（有空就做）
- **预估**：S（≤0.5d）/ M（0.5-2d）/ L（2-5d）/ XL（>5d，必须拆）
- **验收**：每条必须有可验证的产出物

---

## 1. 当前迭代：M0 → M1 切换期

> M0 文档对齐已完成。下面是 M1 工程债清理期任务。
> **建议节奏**：2 周完成。每日站会更新此清单。

### 1.1 P0 阻塞任务（不做完不能进 M2）

| ID | 任务 | 关联 | 类型 | 预估 | 验收 | 状态 |
|----|------|------|------|------|------|------|
| TASK-M1-01 | 拆分 `pages/Dashboard/index.tsx` | [plan-§1.2][spec-DASH] | refactor | M | 主文件 ≤ 200 行；任务列表/AI 摘要/快捷入口拆为独立组件 | ⬜ 待开始 |
| TASK-M1-02 | 拆分 `pages/DataIntegration/index.tsx` | [plan-§1.2][spec-DD-1] | refactor | M | 主文件 ≤ 200 行 | ⬜ 待开始 |
| TASK-M1-03 | 拆分 `pages/ReportGenerator/index.tsx` | [plan-§1.2][spec-DD-3] | refactor | L | 主文件 ≤ 200 行；编辑器/章节/导出三块拆开 | ⬜ 待开始 |
| TASK-M1-04 | 全站 5 态审计清单 | [plan-§1.2][const-§5.1] | docs | M | `docs/sdd/audit-5states.md` 列出每个 page 当前 5 态实现情况 | ⬜ 待开始 |
| TASK-M1-05 | 移除 page 直接 import mock | [plan-§2.2] | refactor | M | `rg "from.*services/mock"` 仅 stores 命中 | ⬜ 待开始 |

### 1.2 P1 迭代内任务

| ID | 任务 | 关联 | 类型 | 预估 | 验收 | 状态 |
|----|------|------|------|------|------|------|
| TASK-M1-06 | 抽 `src/utils/logger.ts` | [plan-§1.2][const-§2.2] | feat | S | dev 环境 console，prod 收口；批量替换现有 console.log | ⬜ 待开始 |
| TASK-M1-07 | 添加全局 `<ErrorBoundary>` | [plan-§5.5] | feat | S | 顶层 + 5 大模块各一层；错误页有"刷新/返回首页" | ⬜ 待开始 |
| TASK-M1-08 | 清理 `.claude/settings.local.json` 过期 sed | [plan-§1.2] | chore | S | 移除 6 条 sed 临时记录 | ⬜ 待开始 |
| TASK-M1-09 | 增加 PR 模板 `.github/PULL_REQUEST_TEMPLATE.md` | [const-§4.2] | docs | S | 必填 spec/plan 编号 + 截图占位 | ⬜ 待开始 |
| TASK-M1-10 | 5 态审计后修复缺漏 | [TASK-M1-04] | fix | L | 至少补全 P1 模块的所有 loading/empty/error 态 | ⬜ 待开始 |
| TASK-M1-11 | 补 `pages/Analysis/index.tsx` 修改的提交说明 | git status | docs | S | 已修改未提交，需 squash 或合并 | ⬜ 待开始 |

### 1.3 P2 选做任务

| ID | 任务 | 关联 | 类型 | 预估 | 验收 | 状态 |
|----|------|------|------|------|------|------|
| TASK-M1-12 | 整理 `dist/` 是否需要纳入 gitignore | repo | chore | S | 当前 dist 在仓库内，确认是否合规 | ⬜ 待开始 |
| TASK-M1-13 | 评估 `lucide-react` 版本（package.json 显示 ^1.12.0） | deps | chore | S | 实际最新版是 0.x，需确认是否拼写错误 | ⬜ 待开始 |
| TASK-M1-14 | 给每个 store 加 `reset()` | [const-§5.1] | refactor | M | 7 个 store 全部具备 reset | ⬜ 待开始 |

---

## 2. 下一迭代：M2 后端接入准备期（草稿）

> 进入 M2 前必须完成 M1 全部 P0/P1。

| ID | 任务 | 关联 | 预估 |
|----|------|------|------|
| TASK-M2-01 | 创建 `src/services/{api,mock,index}` 三层 | [plan-§2.3][plan-§4.3] | M |
| TASK-M2-02 | ADR-002 落地：HTTP 客户端选型 | [ADR-002] | S |
| TASK-M2-03 | spike：以 enterprise.list 走通 mock→real 切换 | [plan-§5.2] | M |
| TASK-M2-04 | 引入 GitHub Actions CI（lint + build） | [plan-§6.3] | S |
| TASK-M2-05 | 添加 `<AuthGuard>` 与 token 占位 | [plan-§5.5] | M |
| TASK-M2-06 | 引入 Toast / Modal / Skeleton 全局组件 | [plan-§5.5] | L |
| TASK-M2-07 | 配置 `.env.example`，记录 `VITE_USE_REAL_API` 等 | [plan-§4.3] | S |

---

## 3. 已完成归档

> 完成后从上方移到这里，每月清理一次。

### M1 - 风险追踪演示数据优化 ✅ 2026-05-07 完成

| ID | 任务 | 产出 | 状态 |
|----|------|------|------|
| TASK-M1-15 | 优化风险追踪功能演示数据 | ✅ 预警信号从 4 条扩展到 12 条，覆盖 4 家企业；风险事件从 2 个扩展到 8 个；处置时间线从 2 条扩展到 8 条；贷后检查从 3 条扩展到 8 条；企业风险画像从 1 家扩展到 4 家 | ✅ 已完成 |

### M0 - 文档对齐期 ✅ 2026-05-06 完成

| ID | 任务 | 产出 | 状态 |
|----|------|------|------|
| TASK-M0-01 | 创建 `docs/sdd/README.md` | ✅ SDD 索引 | ✅ 已完成 |
| TASK-M0-02 | 产出 `docs/sdd/constitution.md` | ✅ 项目宪法 | ✅ 已完成 |
| TASK-M0-03 | 产出 `docs/sdd/spec.md` | ✅ 产品规范 | ✅ 已完成 |
| TASK-M0-04 | 产出 `docs/sdd/plan.md` | ✅ 技术方案 + 8 条 ADR | ✅ 已完成 |
| TASK-M0-05 | 产出 `docs/sdd/tasks.md` | ✅ 本文件 | ✅ 已完成 |
| TASK-M0-06 | 产出 `docs/sdd/test.md` | ✅ 测试策略 | ✅ 已完成 |
| TASK-M0-07 | 在 README.md 添加 SDD 入口 | ✅ | ✅ 已完成 |

---

## 4. Bug / Issue 跟踪

> 任何 PR 修复 bug 必须先在此登记，并关联到 spec 哪条用例失效。

| ID | 描述 | 关联 | 严重度 | 状态 |
|----|------|------|--------|------|
| — | （暂无） | — | — | — |

---

## 5. 站会规则（建议）

每天 10 分钟，按"昨天 / 今天 / 阻塞"三句话报告，对应到 tasks 编号：

```
昨天：完成 TASK-M1-01 主文件拆分
今天：开始 TASK-M1-04 5 态审计
阻塞：无
```

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-06 | 首版，初始化 M1 任务（11 项）+ M2 草案（7 项） |
| v1.1 | 2026-05-06 | 同步 M0 完成状态，补充 test.md 任务，明确状态字段语义 |
| v1.2 | 2026-05-07 | 归档 TASK-M1-15（风险追踪演示数据优化） |

