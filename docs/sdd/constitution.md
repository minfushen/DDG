# 项目宪法（Constitution）

> 这是本项目最高优先级的文档。它规定**永恒不变的原则**，违反任意一条都会被 PR Block。
> 修改宪法需要：① 团队评审；② 在本文末尾"修订记录"里说明动因；③ 同步评估对 `plan.md` 的级联影响。

---

## 第一章 项目身份

### 1.1 一句话定义

**面向银行对公信贷场景的尽调智能体工作台**：让客户经理 / 审批人 / 风控员能在同一个 Web 平台上完成贷前尽调、贷中审批、贷后预警、运营分析的全链路作业。

### 1.2 核心用户（按优先级）

1. **客户经理**（张经理）— 高频日常用户，每天打开平台找"今天要做什么"
2. **审批人**— 中频，关注风险结论与证据链
3. **部门主管**— 低频，看团队效率与全局指标
4. **系统管理员**— 极低频，配置数据源与智能体

> 当出现需求冲突时，**客户经理优先**。

### 1.3 不在范围（Out of Scope）

以下内容**永久排除**，不接受讨论：

- ❌ 移动端原生 App（仅响应式 Web）
- ❌ 直接对接征信、税务等真实金融数据源（合规风险，由后端中台统一封装）
- ❌ 交易撮合、放款、还款等资金动作（这是核心业务系统的领域）
- ❌ 替代客户经理的最终决策（平台只做辅助，决策权永远在人）

---

## 第二章 技术红线

以下条款**禁止违反**。CR 中发现立即驳回，不接受"特殊情况"。

### 2.1 技术栈锁定

| 维度 | 锁定值 | 理由 |
|------|--------|------|
| UI 框架 | React 19 | 已选定，跨版本迁移成本高 |
| 语言 | TypeScript 6（strict） | 大型应用必须类型化 |
| 构建 | Vite 8 | 不引入 webpack/turbopack |
| 样式 | TailwindCSS v4 + CSS 变量 | 禁止 styled-components / emotion / sass |
| 状态 | Zustand v5 | 禁止 Redux / MobX / Recoil |
| 路由 | React Router v7 | 禁止 TanStack Router |
| 图表 | ECharts 6 | 禁止 antv / chart.js / recharts |

> 引入新的运行时依赖必须在 `plan.md` 留 ADR，并经技术负责人评审。

### 2.2 编码红线

- ❌ **禁止使用 `any`**：必须显式 unknown / 泛型 / 联合类型
- ❌ **禁止裸 `console.log` 进生产**：用 `src/utils/logger`（待建）
- ❌ **禁止硬编码颜色值**：必须从 `src/theme/tokens.ts` 引用
- ❌ **禁止页面自带 `min-h-screen bg-surface-page p-8`**：用 `MainLayout` + `PageHeader`
- ❌ **禁止 `purple/pink/cyan` 作为业务页主视觉**：仅品牌蓝 + 4 语义色
- ❌ **禁止跨模块直接 import 别人的内部组件**：只能 import `pages/<module>/index.ts` 的导出
- ❌ **禁止把业务逻辑写在 `pages/*/index.tsx`**：超过 200 行必须拆分到 hooks / components / store

### 2.3 状态管理红线

- ✅ **每个业务模块一个 Store**（如 `useApprovalStore`、`usePostLoanStore`）
- ✅ **Store 内只放"跨页面共享"的状态**，组件内部状态用 `useState`
- ❌ **禁止在 Store 里放派生状态**：派生用 selector 即时算
- ❌ **禁止 Store 之间直接 import**：跨域协作走事件或 props

### 2.4 数据层红线

- 当前所有数据来自 `src/services/mock*.ts`（前端 Mock）
- ❌ **禁止页面组件直接 import mock 文件**：必须经过 store 或后续的 service 层
- ❌ **禁止把 Mock 数据 hardcode 进组件**
- ✅ **未来接真后端时**，只能改 `src/services/*` 内部，不允许污染 stores 与 pages

---

## 第三章 设计红线（视觉与交互）

详见 `docs/UI_DESIGN_SPEC.md` 与 `docs/UNIFIED_VISUAL_MASTERPLAN.md`，本节只列**绝对底线**：

- ✅ 全站只有**一种主色**：品牌蓝 `#1E40AF`
- ✅ 状态语义色 1:1 映射（成功绿 / 警告橙 / 危险红 / 信息蓝），全站统一
- ✅ 字体层级 5 档：Page Title 40 / Section 32 / Card 24 / Body 14-16 / Meta 12
- ✅ 卡片圆角统一 16px，按钮高度 40 / 44 / 52 三档
- ✅ 内容最大宽度 1600px，断点 desktop 40 / tablet 24 / mobile 16
- ❌ 禁止页面级重复大 Hero
- ❌ 禁止固定 `h-[600px]` 主内容高度
- ❌ 禁止无断点的 `grid-cols-3 / grid-cols-4`

---

## 第四章 流程红线

### 4.1 SDD 工作流

> "**先改文档，再改代码**" — 没有 plan/spec 支撑的 PR 一律驳回。

```
新增功能：spec.md → plan.md → tasks.md → 代码 → PR
修复 bug：tasks.md（关联 spec 条目）→ 代码 → PR
重构：   plan.md（追加 ADR）→ tasks.md → 多次小 PR
```

### 4.2 PR 红线

- 每个 PR 必须在描述里贴出 `[spec-XX][plan-YY]` 关联编号
- 单次 PR 改动文件数 **不超过 15 个**（重构例外，但需在 plan.md 备注）
- 必须通过：`npm run build`（含 `tsc -b`）+ `npm run lint`
- UI 改动必须附改造前后截图（同分辨率）

### 4.3 提交信息

约定式提交（Conventional Commits）：

```
feat(approval): 增加合同对比的差异高亮  [spec-3.2]
fix(post-loan): 修复风险追踪时间线节点错位  [tasks-#42]
refactor(theme): 抽离 statusToken 到独立文件  [plan-ADR-005]
docs(sdd): 更新 plan.md 第 4 章模块边界
```

---

## 第五章 质量红线

### 5.1 必须做

- ✅ 每个**业务页面**必须覆盖 5 态：loading / empty / error / disabled / hover
- ✅ 每个 **store** 必须有**初始化函数**和**重置函数**
- ✅ 每个**类型定义**必须导出，且禁止 `as any` 兜底
- ✅ 每次 PR 后必须**自测主流程**（首页 → 数据整合 → 分析 → 报告 → 审批 → 贷后）

### 5.2 暂不强制（但鼓励）

- ⚠️ 单元测试：当前没有测试基础设施。`plan.md` 中规划在 M3 阶段引入 Vitest + RTL
- ⚠️ E2E 测试：M4 阶段评估 Playwright
- ⚠️ Storybook：M3 阶段评估，用于沉淀 UI 组件库

> 这两类不是宪法级要求，不进入红线，但 plan.md 会规划其引入时机。

---

## 第六章 不在宪法中的事

以下事项**故意不约束**，留给 plan.md 按迭代灵活决策：

- 具体目录结构调整
- 新增/删减页面
- Mock 数据扩展方式
- 智能体协议（AG-UI / A2UI）的细节演进
- 性能优化策略

---

## 修订记录

| 版本 | 日期 | 修改人 | 变更摘要 |
|------|------|--------|---------|
| v1.0 | 2026-05-06 | 初始 | Vibe → SDD 切换，确立首版宪法 |

