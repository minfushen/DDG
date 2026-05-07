# 技术实施方案（Plan）

> SDD 体系的**核心交付物**。它回答 spec.md 的"WHAT"如何落到代码上的"HOW"。
> 本文是工程师的"主地图"：架构、模块边界、数据流、迭代路线、风险与决策记录都在这里。
>
> **每个 PR 必须能在本文找到对应章节作为依据。**

---

## 目录

1. [现状评估（Where We Are）](#1-现状评估where-we-are)
2. [目标架构（Target Architecture）](#2-目标架构target-architecture)
3. [模块边界（Module Boundaries）](#3-模块边界module-boundaries)
4. [数据流与状态管理](#4-数据流与状态管理)
5. [前端 → 后端演进路径](#5-前端--后端演进路径)
6. [质量保障体系](#6-质量保障体系)
7. [迭代路线图（Roadmap M0–M4）](#7-迭代路线图roadmap-m0m4)
8. [风险登记册](#8-风险登记册)
9. [架构决策记录（ADR）](#9-架构决策记录adr)

---

## 1. 现状评估（Where We Are）

### 1.1 代码资产盘点

| 维度 | 数据 | 备注 |
|------|------|------|
| 总代码文件 | 84 个 `.ts/.tsx` | 见 `src/` |
| 路由页面 | 16 个 | 5 大模块全覆盖 |
| Zustand Stores | 7 个 | 按业务域拆分 |
| Mock 服务文件 | 3 个 | `mockData / mockApprovalData / mockPostLoanData` |
| 类型定义文件 | 7 个 | `types/` 下，已 export 聚合 |
| 协议适配层 | 2 套 | AG-UI（事件流）/ A2UI（动态 UI） |
| Git 提交数 | 6 次 | 已经历 3 轮 UI 重构（feat → refactor → refactor） |

### 1.2 Vibe 阶段遗留的工程债（已识别）

| 债务项 | 体现 | 处置时机 |
|--------|------|---------|
| 无单元测试 | 无 `vitest.config` / `__tests__` | M3 引入 |
| 无 CI | 无 `.github/workflows` | M2 引入 |
| 临时 sed 修复痕迹 | `.claude/settings.local.json` 内的 sed 命令 | 已修复，本文记录原因 |
| 部分页面超过 300 行 | `Dashboard 305` / `DataIntegration 312` / `ReportGenerator 400` | M1 拆分 |
| Mock 与组件耦合 | 个别页面直接 import `mockData` | M1 全部走 store |
| 缺失 5 态覆盖审计 | 没有清单确认每页 loading/empty/error/disabled/hover | M1 完成审计 |
| 无错误边界 | 没有 `<ErrorBoundary>` | M2 引入 |
| 无统一 logger | 直接 `console.log` 散落 | M2 抽 `src/utils/logger.ts` |

### 1.3 已沉淀的好资产（不要破坏）

- ✅ **设计 Token 体系**：`src/theme/tokens.ts` 已统一颜色 / 渐变 / 状态色 / 卡片样式
- ✅ **业务状态机权威**：`docs/BUSINESS-DESIGN.md` 已定义 8 态生命周期
- ✅ **UI 设计规范 v3.0**：`docs/UI_DESIGN_SPEC.md` 已收敛"页头 + 区块头 + 统一卡片"
- ✅ **AG-UI / A2UI 协议骨架**：`src/protocol/` 已铺好对话型智能体的事件协议
- ✅ **演示数据故事化**：`src/data/demo-story.ts` 围绕 4 家企业（浙江华创科技、江苏恒远制造、宁波新材料科技、杭州鼎盛贸易）讲完整贷后管理流程，含 12 条预警信号、8 个风险事件、8 项贷后检查

---

## 2. 目标架构（Target Architecture）

### 2.1 总体分层

```
┌────────────────────────────────────────────────────────────────┐
│                    Pages (路由页面，view-controller)             │
│                       薄层，不放业务逻辑                          │
└─────────┬──────────────────────────────────────────────┬───────┘
          │                                              │
          ▼                                              ▼
┌─────────────────────────┐               ┌──────────────────────┐
│  Hooks (业务编排)        │               │  Components (展示)   │
│  封装跨页复用流程         │               │  layout/ui/business/charts │
└──────────┬──────────────┘               └──────────┬───────────┘
           │                                          │
           ▼                                          │
┌────────────────────────────────────────────────────┴──────────┐
│                  Stores (Zustand)                              │
│         跨页面共享状态 + Action（业务编排）                       │
└──────────┬─────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────────┐
│                  Services (数据访问层)                           │
│      Mock 适配器 / 真实 API 适配器 / Protocol 适配器              │
└──────────┬─────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────────┐
│            Mock JSON  /  真实 HTTP API  /  WebSocket / SSE      │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 关键约束

- **Pages 不能直接 import Mock**：必须经 store 或 service
- **Components 不能 import Stores**：UI 组件保持纯展示，状态由 page/hook 注入
- **Stores 之间不直接 import**：跨域通过事件总线或 page 编排
- **Protocol 层独立**：AG-UI / A2UI 不依赖任何业务模块

### 2.3 目录结构（目标）

```text
src/
├── App.tsx                        # 路由聚合
├── main.tsx                       # 应用入口
├── index.css                      # Tailwind + 全局变量
│
├── pages/                         # 16 个路由页面（薄层）
│   ├── Dashboard/
│   ├── DataIntegration/
│   ├── Analysis/
│   ├── ReportGenerator/
│   ├── AgentConfig/
│   ├── DocumentChecklist/
│   ├── PSAKValidation/
│   ├── Approval/{ApprovalDashboard,ContractCompare,RiskChat,FundFlow}/
│   ├── PostLoan/{WarningDashboard,RiskTracking,PostLoanCheck,WarningConfig}/
│   └── Analytics/
│
├── components/
│   ├── layout/                    # MainLayout / Header / Sidebar
│   ├── ui/                        # PageHeader / SectionHeader / StatCard / Button / ...
│   ├── business/                  # 业务半成品（任务卡 / 风险标签 / 时间线）
│   ├── charts/                    # ECharts 二次封装
│   └── common/                    # 跨业务通用（ErrorBoundary 等）
│
├── stores/                        # Zustand，按业务域拆分
│   ├── useDueDiligenceStore.ts    # 贷前
│   ├── useApprovalStore.ts        # 贷中
│   ├── usePostLoanStore.ts        # 贷后
│   ├── usePSAKStore.ts            # PSAK
│   ├── useReportStore.ts          # 报告生成
│   ├── useAgentSessionStore.ts    # 智能体会话
│   └── useDemoStore.ts            # 演示数据聚合（M2 后逐步淘汰）
│
├── services/                      # ⚠️ 待 M2 重构：抽出统一接口
│   ├── api/                       # 真实 API 适配器（M2 引入）
│   │   └── ...
│   ├── mock/                      # Mock 适配器（仅本目录可使用 mock 数据）
│   │   ├── enterprises.ts
│   │   ├── approval.ts
│   │   └── postLoan.ts
│   └── index.ts                   # 暴露统一接口，运行时按 env 切换 mock/real
│
├── protocol/
│   ├── agui/                      # 智能体事件流协议
│   └── a2ui/                      # 动态 UI 渲染协议
│
├── theme/
│   └── tokens.ts                  # ⭐ 唯一颜色 / 状态 / 尺寸源
│
├── types/                         # 全局类型定义
│   └── ...
│
├── utils/
│   ├── logger.ts                  # M2 引入：替代 console.log
│   ├── download.ts                # 已存在
│   └── ...
│
├── data/
│   └── demo-story.ts              # 统一 Demo 故事（一家企业贯穿全流程）
│
└── config/                        # 展示配置 / 路由元信息 / 状态映射表
```

> 与当前实际结构的差异在 **§7 路线图 M1 / M2** 中给出迁移步骤。

---

## 3. 模块边界（Module Boundaries）

### 3.1 五大业务模块的边界

| 模块 | Pages | Store | 协议 | 跨域依赖 |
|------|-------|-------|------|---------|
| 贷前尽调 | Dashboard / DataIntegration / Analysis / ReportGenerator / AgentConfig | useDueDiligenceStore + useReportStore | — | → 贷中（report_ready 时移交） |
| 智能尽调 | DocumentChecklist / PSAKValidation | usePSAKStore | — | ← 贷前共用 enterprise 上下文 |
| 贷中审批 | ApprovalDashboard / ContractCompare / RiskChat / FundFlow | useApprovalStore + useAgentSessionStore | AG-UI（RiskChat） | ← 贷前 |
| 贷后预警 | WarningDashboard / RiskTracking / PostLoanCheck / WarningConfig | usePostLoanStore | — | → 贷前（触发新尽调） |
| 运营分析 | Analytics | useDemoStore | — | 只读所有域 |

### 3.2 共享层

```
所有模块共享：
- types/                  # 类型契约（Enterprise / Task / RiskLevel ...）
- theme/tokens.ts         # 视觉契约
- components/ui/          # UI 组件契约
- components/layout/      # 布局契约
- protocol/               # 协议契约（AG-UI / A2UI）
```

### 3.3 跨模块通信规则

- ✅ **通过 props / hooks 传递**：`<RiskChat enterpriseId={id} />`
- ✅ **通过路由参数**：`/post-loan/risk-tracking/:id`
- ✅ **通过共享 types**：`DueDiligenceTask` 跨模块流转
- ❌ **禁止**：A 模块的 store 内 import B 模块的 store
- ❌ **禁止**：A 模块组件 import B 模块的内部组件（只能 import 顶层 export）

---

## 4. 数据流与状态管理

### 4.1 状态分类

```
组件本地状态 (useState)         — 表单输入、临时 UI 开关
        │
        ▼
跨组件共享状态 (Zustand)         — 任务列表、当前选中企业、AI 会话
        │
        ▼
派生状态 (selector)              — 过滤后的任务、统计聚合（不持久化）
        │
        ▼
持久化状态 (localStorage 待引入) — 用户偏好、最近查看、Demo 进度
        │
        ▼
服务端状态 (M2 后)               — 真实 API 数据、智能体推理结果
```

### 4.2 Zustand Store 设计模板

每个 store 必须遵循以下骨架：

```typescript
interface XxxState {
  // 1. 数据
  items: Item[];
  loading: boolean;
  error: string | null;

  // 2. 同步 Action（只改 state）
  setItems: (items: Item[]) => void;

  // 3. 异步 Action（编排 service 层）
  fetchItems: () => Promise<void>;

  // 4. 重置
  reset: () => void;
}
```

**约束**：

- 派生状态用 selector，不写进 state
- 异步 Action 内部统一 `try/finally` 处理 loading
- 所有 store 必须有 `reset()`（用于路由切换 / 退出）

### 4.3 Mock → Real API 的切换设计（M2 关键）

```typescript
// services/index.ts （M2 引入）
import * as mock from './mock';
import * as api from './api';

const useReal = import.meta.env.VITE_USE_REAL_API === 'true';

export const enterpriseService = useReal ? api.enterprise : mock.enterprise;
export const approvalService   = useReal ? api.approval   : mock.approval;
// ...
```

> Stores 只 `import { enterpriseService } from '@/services'`，不关心底层是 mock 还是 real。

### 4.4 智能体协议数据流

```
用户输入
  │
  ▼
RiskChat / 任意会话页
  │
  ▼  emit
useAgentSessionStore.send(message)
  │
  ▼
protocol/agui/connection.ts （SSE / WebSocket，待 M2 接真后端）
  │
  ▼
后端智能体（暂用 mock 流式数据模拟）
  │
  ▼  事件流
[text_delta] [status_update] [tool_call] [tool_result] [ui_render] [done]
  │
  ▼
useAgentSessionStore.append(event)
  │
  ▼
RiskChat 订阅渲染
```

---

## 5. 前端 → 后端演进路径

> 当前是纯前端 + Mock 项目。本节定义"接真后端时**最小化代码改动**"的策略。

### 5.1 隔离层设计

唯一允许触碰真实后端的层是 `src/services/api/`。其他所有代码都通过 `services/index.ts` 暴露的统一接口访问数据，**不感知底层是 mock 还是 real**。

### 5.2 接入步骤（M2 执行）

1. 在 `src/services/api/` 下按业务域建文件，签名与 `mock/` 完全一致
2. `services/index.ts` 按环境变量动态选择实现
3. 引入 `axios` 或 `ky` 作为 HTTP 客户端（在本文 ADR-002 评估）
4. 引入 React Query / TanStack Query？— **暂不引入**（理由见 ADR-003）
5. 接入认证：在 `MainLayout` 顶层添加 `<AuthGuard>`
6. 接入错误处理：HTTP 错误统一在 service 层映射成 `AppError`，store 捕获并写入 `state.error`

### 5.3 对 Stores 的影响

**零改动**目标。Store 内部只 `await enterpriseService.list()`，不关心是文件还是 HTTP。

### 5.4 对 Pages / Components 的影响

**零改动**目标。

### 5.5 不可避免的新增

| 新增项 | 位置 | 时机 |
|--------|------|------|
| 认证 token 管理 | `services/auth.ts` | M2 |
| 全局 axios 拦截器 | `services/api/http.ts` | M2 |
| Loading skeleton 全局组件 | `components/ui/Skeleton.tsx` | M2 |
| Error Boundary | `components/common/ErrorBoundary.tsx` | M2 |
| Toast 通知 | `components/ui/Toast.tsx` | M2 |

---

## 6. 质量保障体系

### 6.1 静态质量（已就位）

- ✅ TypeScript strict（`tsconfig.app.json`）
- ✅ ESLint + typescript-eslint
- ✅ `npm run build` = `tsc -b && vite build`（类型 + 构建双检）

### 6.2 动态质量（路线规划）

| 层级 | 工具 | 时机 | 目标覆盖率 |
|------|------|------|-----------|
| 单元 | Vitest + React Testing Library | M3 | 关键 hooks/store ≥ 70% |
| 集成 | Vitest + RTL（多组件） | M3 | 主流程 ≥ 50% |
| 视觉回归 | Storybook + Chromatic? | M4 评估 | UI 库覆盖 |
| E2E | Playwright | M4 | 5 条主旅程 |
| 类型 | tsc | 已就位 | 0 error |
| Lint | ESLint | 已就位 | 0 error |

### 6.3 CI 流水线（M2 引入）

```yaml
# .github/workflows/ci.yml
on: [pull_request, push]
jobs:
  build:
    steps:
      - install
      - lint            # npm run lint
      - typecheck       # tsc -b --noEmit
      - build           # npm run build
      - test            # M3 起
```

### 6.4 PR 质量门

每个 PR 必过：
- 关联 spec / plan / tasks 编号
- `npm run build` 绿
- `npm run lint` 绿
- UI 改动附前后截图
- Reviewer 至少 1 人

---

## 7. 迭代路线图（Roadmap M0–M4）

> **M = Milestone**。每个 milestone 2-4 周，结束时做"舒适度验收 + ADR 沉淀"。

### M0 - 文档对齐期 ✅（本次）

**目标**：建立 SDD 文档体系，停止 Vibe 模式。

- [x] 创建 `docs/sdd/` 目录与四件套
- [x] 收编已有 BUSINESS-DESIGN / UI_DESIGN_SPEC / UNIFIED_VISUAL_MASTERPLAN
- [x] 在 README 增加 SDD 索引

**出口标准**：
- 团队成员都已读过 constitution.md + spec.md + plan.md
- PR 模板更新（关联 spec/plan 编号）

---

### M1 - 工程债清理期（建议 2 周）

**目标**：消除 Vibe 阶段遗留的 8 项工程债中的高优先级 5 项。

| 任务 | 输出 | 负责人 |
|------|------|--------|
| 拆分超过 300 行的 page | Dashboard/DataIntegration/ReportGenerator | 前端 |
| 5 态审计 | 每个 page 的 loading/empty/error/disabled/hover 清单 | 前端 |
| 移除 page 直接 import mock | 全部经 store | 前端 |
| 抽 `utils/logger.ts` | 替代 console.log | 前端 |
| 增 `<ErrorBoundary>` | 顶层 + 业务模块层 | 前端 |
| 清理 `.claude/settings.local.json` 中过期 sed | — | 维护者 |

**出口标准**：
- 所有 pages/*/index.tsx ≤ 200 行
- 没有任何文件 `import` mock 服务（除 store/service）
- Dashboard 主流程通过 5 态自检

---

### M2 - 后端接入准备期（建议 3 周）

**目标**：建立 service 隔离层、CI、认证基础设施，**为接真后端做好结构准备**（即使后端没就绪，也先把切换开关打通）。

| 任务 | 输出 |
|------|------|
| 建立 `src/services/{api,mock,index}` 三层 | 切换开关：`VITE_USE_REAL_API` |
| 引入 HTTP 客户端 | ADR 决定 axios / ky（见 ADR-002） |
| 设计 `AuthGuard` 与 token 存取 | `services/auth.ts` |
| 引入 GitHub Actions CI | `.github/workflows/ci.yml` |
| 引入 Toast / Modal / Skeleton 全局组件 | 补全 ui/ |
| 接 1 条端到端样例：Mock → Real API 切换 | 以 enterprise.list 为试点 |

**出口标准**：
- 切换 `VITE_USE_REAL_API=true` 后，UI 能响应（即便后端打 mock-server）
- CI 阻塞 lint/build 不通过的 PR

---

### M3 - 测试与可观测期（建议 4 周）

**目标**：引入测试与监控，让代码改动可量化。

| 任务 | 输出 |
|------|------|
| 引入 Vitest + RTL | 单元测试基础 |
| 关键 store 全覆盖 | 7 个 store 单测 ≥ 70% |
| 关键 hooks 单测 | 自定义 hooks 100% |
| 引入 Sentry / 自建错误日志 | 前端错误捕获 |
| 评估 Storybook | 决定是否引入 |
| 性能基线 | LCP / TTI 数据采集 |

---

### M4 - 智能体协议落地期（建议 3 周）

**目标**：让 AG-UI / A2UI 协议真正驱动业务页面，而不是当前的演示骨架。

| 任务 | 输出 |
|------|------|
| AG-UI 接 SSE 后端 | RiskChat / Analysis 页流式更新 |
| A2UI 渲染器扩展 | 支持表格/图表/卡片三类动态描述 |
| 引入 Playwright | 5 条主旅程 E2E |
| 性能优化 | 路由懒加载、ECharts 按需引入 |

---

### 路线总览

```
M0  M1   M2     M3        M4
 │   │    │      │         │
文档  债  服务   测试      协议
对齐  务  隔离   监控      落地
 ✓   2w   3w     4w        3w
```

---

## 8. 风险登记册

| 编号 | 风险 | 等级 | 触发条件 | 应对 |
|------|------|------|---------|------|
| R-1 | 后端 API 长期不就绪 | 高 | 业务方排期延期 > 2 月 | M2 完整建好 mock server，独立可用 |
| R-2 | Tailwind v4 / React 19 生态不稳 | 中 | 依赖更新破坏构建 | 锁版本，依赖更新走 ADR |
| R-3 | 单页 SPA 体积膨胀 | 中 | 体积 > 1MB | M4 路由懒加载 + ECharts 按需 |
| R-4 | 无认证导致 demo 数据外泄 | 中 | 部署到公网 | 部署文档强调内网或加 Basic Auth |
| R-5 | AG-UI 协议升级破坏现存对话页 | 低 | Anthropic / OpenAI 推出新版 | protocol/ 层独立，可平滑替换 |
| R-6 | 多人协作分支冲突 | 中 | 同时多人改 stores | 按业务域单 store，分支按模块拆 |
| R-7 | 文档与代码漂移 | 高 | SDD 流程未严格执行 | 在 PR 模板强制要求 spec/plan 编号 |

---

## 9. 架构决策记录（ADR）

> 所有重大决策必须以 ADR 形式记录在此，**禁止只在聊天里口头决定**。

### ADR-001：状态管理选 Zustand 而非 Redux

- **日期**：2026-05-06（追溯，Vibe 阶段决策）
- **状态**：✅ 已采纳
- **决策**：业务域级状态采用 Zustand v5
- **理由**：
  - Zustand 无 boilerplate，store 体积小
  - 本项目状态相对扁平，无需 Redux DevTools / time-travel
  - 与 React 19 兼容良好
- **代价**：派生状态需要手写 selector，无内建 RTK Query
- **替代方案**：
  - Redux Toolkit — 复杂度过剩
  - Jotai / Recoil — 原子化适合极细粒度，本项目用不到
  - Context API — 大量数据时性能差

---

### ADR-002：HTTP 客户端选型

- **日期**：2026-05-06
- **状态**：✅ 已采纳
- **决策**：采用 **ky** 作为 HTTP 客户端
- **理由**：
  - 与本项目 Vite 8 / ESM 调性一致
  - 体积仅 4KB（axios 13KB），对 SPA 打包体积友好
  - 原生 TypeScript 支持，无需额外类型定义
  - API 简洁：`ky.get(url).json()` 比 axios 更符合现代风格
  - 拦截器机制足够满足需求（auth token 注入、错误统一处理）
- **代价**：
  - 生态比 axios 小，部分边缘场景需手写
  - 浏览器兼容依赖原生 fetch（IE 不支持，但本项目已排除 IE）
- **替代方案**：
  - axios — 生态成熟但体积偏大，API 略繁琐
  - native fetch — 0 依赖但需自己写拦截器/重试/超时
- **落地时机**：M2 第一周引入，在 `services/api/http.ts` 封装基础实例

---

### ADR-003：暂不引入 React Query

- **状态**：✅ 已采纳
- **决策**：当前阶段不引入 React Query / TanStack Query
- **理由**：
  - 数据全是 mock，无真正的 server state 复杂度
  - Zustand 已足够承载异步 action
  - 引入会增加心智负担，与 Zustand 双写状态
- **重新评估时机**：M2 接真 API 后，如出现以下情况则升级：
  - 多页共享同一份请求结果且需缓存
  - 需要乐观更新 / 自动重试 / 后台轮询
- **替代方案**：在 store 内手写缓存层（已足够）

---

### ADR-004：UI 设计 Token 集中化

- **日期**：2026-05-02（Vibe 阶段已落地）
- **状态**：✅ 已采纳
- **决策**：所有颜色 / 渐变 / 状态色 / 卡片样式收敛到 `src/theme/tokens.ts`
- **理由**：
  - 历史上 6 次提交里有 3 次是 UI 重构，痛点是颜色散落
  - Tailwind v4 + CSS 变量天然支持 token 化
- **强制执行**：constitution.md §3 红线，CR 阶段拦截

---

### ADR-005：智能体协议分层（AG-UI vs A2UI）

- **状态**：✅ 已采纳
- **决策**：
  - **AG-UI**：处理"事件流"——文本增量、状态、工具调用，用于会话型场景
  - **A2UI**：处理"动态 UI 描述"——服务端推送 schema，前端按 schema 渲染卡片/表格/图表
- **理由**：两者职责正交，硬塞在一起会让 schema 膨胀
- **强制约束**：所有"对话型页面"（RiskChat / Analysis 智能解读）必须经 AG-UI；所有"AI 渲染卡片"必须经 A2UI，不允许各自实现

---

### ADR-006：演示数据故事化（demo-story）

- **状态**：✅ 已采纳
- **决策**：所有跨模块的演示流程围绕核心企业（浙江华创科技）展开，同时扩展到关联企业（江苏恒远制造、宁波新材料科技、杭州鼎盛贸易）以展示多企业管理场景。确保用户在 Dashboard → 数据整合 → 分析 → 报告 → 审批 → 贷后 的旅程中"故事不断"
- **理由**：Vibe 阶段早期数据散乱，体验割裂。演示故事化后 demo 收益显著。2026-05-07 扩展到 4 家企业以丰富贷后预警场景
- **影响**：M2 接真 API 后保留这个机制，作为"演示模式"开关

---

### ADR-007：暂不做移动端原生

- **状态**：✅ 已采纳
- **决策**：仅响应式 Web，不做 RN / Flutter / 微信小程序
- **理由**：
  - 用户角色（客户经理 / 审批人）核心办公场景是桌面端
  - 移动端只用于"通勤路上看待办"，响应式足够
- **重新评估时机**：业务侧明确给出移动端 KPI 时

---

### ADR-008：保留三份既有 UI 文档而非重写

- **状态**：✅ 已采纳
- **决策**：`BUSINESS-DESIGN.md` / `UI_DESIGN_SPEC.md` / `UNIFIED_VISUAL_MASTERPLAN.md` 不被废弃，被 SDD 引用
- **理由**：内容仍准确，重写浪费且容易丢信息
- **强制约束**：当这三份与 SDD 冲突时，以 SDD 为准；否则以原文件为准

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-06 | 首版，确立 5 阶段路线 + 8 条 ADR |
| v1.1 | 2026-05-06 | ADR-002 闭环决策：采用 ky 作为 HTTP 客户端 |
| v1.2 | 2026-05-07 | 更新 1.3 节演示数据描述：从单一企业扩展到 4 家企业 |

