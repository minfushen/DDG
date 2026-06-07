# 测试策略与规范（Test Plan）

> 本文是 [`plan.md`](./plan.md) §6（质量保障体系）的**展开**。
> 当前项目处于 plan-M1 阶段，**没有任何自动化测试**。本文先**写清楚目标**，等 M3 阶段引入工具时按此文档落地。

---

## 1. 测试理念

### 1.1 我们的立场

| 立场 | 说明 |
|------|------|
| ✅ 测试是**长期维护**的杠杆，不是早期 vibe 阶段的奢侈品 | 进入 SDD 后必须建立 |
| ✅ 测试**金字塔**而非冰激凌锥 | 单元 > 集成 > E2E |
| ✅ 测试**信任度** > 测试**覆盖率** | 70% 覆盖率但每个测试都关键，胜过 95% 覆盖率但充满样板 |
| ✅ 不测**显而易见**的代码 | 不测 getter/setter / 简单类型映射 |
| ✅ 测试是**第一公民代码** | 与生产代码同等的 Lint / 评审标准 |

### 1.2 不做的事

- ❌ **不追求 100% 覆盖率** — 投入产出比低
- ❌ **不测第三方库** — 不测 React Router 自己工作
- ❌ **不测 UI 像素级渲染** — 视觉回归用 Storybook + Chromatic（M4 评估）
- ❌ **不写"为了测试而测试"的占位测试**

---

## 2. 测试金字塔

```
        ╱─────╲
       ╱  E2E  ╲          ← 5-10 条主旅程，Playwright（M4）
      ╱─────────╲
     ╱  集成测试  ╲        ← 跨组件 / 跨 store / 跨 service，~30 个（M3）
    ╱─────────────╲
   ╱   单元测试    ╲      ← hooks / store / utils / 协议解析，~150 个（M3）
  ╱─────────────────╲
```

| 层级 | 数量级 | 速度 | 工具 | 引入时机 |
|------|--------|------|------|---------|
| 单元 | 100-200 | < 5s 全跑 | Vitest + RTL | plan-M3 |
| 集成 | 20-50 | < 30s 全跑 | Vitest + RTL | plan-M3 |
| E2E | 5-15 | < 5min 全跑 | Playwright | plan-M4 |
| 视觉回归 | （评估）| — | Storybook + Chromatic | plan-M4 |

---

## 3. 测试范围矩阵

> 决定"什么必测、什么可选、什么不测"。

| 模块 | 单元测试 | 集成测试 | E2E | 优先级 |
|------|---------|---------|------|-------|
| `stores/*` | ✅ 必测 | ✅ 必测 | — | P0 |
| `protocol/agui` | ✅ 必测（事件解析、状态机） | ✅ 必测（与 store 联动） | — | P0 |
| `protocol/a2ui` | ✅ 必测（schema 验证） | ✅ 必测 | — | P1 |
| `services/api` | ✅ 必测（请求构造、错误映射） | ✅ 必测（mock server） | — | P0 |
| `services/mock` | ⚠️ 选测 | — | — | P2 |
| `utils/*` | ✅ 必测 | — | — | P0 |
| `hooks/*` | ✅ 必测 | ✅ 必测 | — | P0 |
| `components/ui/*` | ⚠️ 选测（关键组件） | ✅ 必测（PageHeader / SectionHeader） | — | P1 |
| `components/business/*` | ✅ 必测 | ✅ 必测 | — | P1 |
| `components/charts/*` | ⚠️ 选测（数据转换函数） | — | — | P2 |
| `components/layout/*` | ⚠️ 选测 | ✅ 必测（路由集成） | — | P1 |
| `pages/*` | ❌ 不测（薄层） | ✅ 必测（关键页面） | ✅ 主旅程 | P0 |
| `theme/tokens.ts` | ❌ 不测（纯常量） | — | — | — |

> "薄层"指 page 应该只做组合，业务逻辑下沉到 hooks/store。如果 page 需要单测，说明该重构。

---

## 4. 工具链与配置

### 4.1 选型决策

| 工具 | 选型 | 理由 |
|------|------|------|
| 测试运行器 | **Vitest** | 与 Vite 同源，零配置，快 |
| React 组件测试 | **@testing-library/react** | 社区标准，鼓励"用户视角" |
| DOM 模拟 | **happy-dom** | 比 jsdom 快 2-3 倍 |
| 断言 | Vitest 内置 expect | 兼容 Jest |
| Mock | Vitest 内置 vi.mock | 零依赖 |
| HTTP Mock | **MSW (Mock Service Worker)** | 拦截网络层，与 service 解耦 |
| 用户交互 | **@testing-library/user-event v14** | 真实模拟 |
| 覆盖率 | **@vitest/coverage-v8** | 原生 V8，最快 |
| E2E | **Playwright** | 多浏览器、自动等待、调试好 |

### 4.2 安装清单（M3 第一周执行）

```bash
npm i -D vitest @vitest/coverage-v8 @vitest/ui happy-dom \
        @testing-library/react @testing-library/user-event \
        @testing-library/jest-dom msw

# E2E（M4）
npm i -D @playwright/test
npx playwright install
```

### 4.3 目录结构

```
src/
├── stores/
│   ├── useApprovalStore.ts
│   └── useApprovalStore.test.ts          # 单元测试与源码同目录
├── utils/
│   ├── logger.ts
│   └── logger.test.ts
├── components/business/
│   ├── TaskCard.tsx
│   └── TaskCard.test.tsx                  # 集成测试
└── __tests__/                             # 跨文件的集成测试
    ├── flows/
    │   ├── approval-flow.test.tsx
    │   └── post-loan-flow.test.tsx
    └── helpers/
        ├── render.tsx                     # 自定义 renderWithProviders
        └── mock-server.ts                 # MSW handlers

tests/                                     # E2E（M4）
├── e2e/
│   ├── due-diligence.spec.ts
│   └── approval.spec.ts
└── playwright.config.ts
```

### 4.4 关键配置（M3 引入）

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/__tests__/helpers/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      thresholds: {
        // M3 阶段目标（已调整为务实基线）
        statements: 50,
        branches: 45,
        functions: 50,
        lines: 50,
      },
      exclude: [
        '**/*.test.{ts,tsx}',
        '**/types/**',
        '**/data/demo-story.ts',
        'src/main.tsx',
        'src/App.tsx',
      ],
    },
  },
});
```

```typescript
// package.json scripts
{
  "test": "vitest",
  "test:ui": "vitest --ui",
  "test:run": "vitest run",
  "test:coverage": "vitest run --coverage",
  "test:e2e": "playwright test"
}
```

---

## 5. 覆盖率目标

> **覆盖率是结果不是目标**。下面的数字是健康基线，不是 KPI。
>
> **原则**：先保证关键路径有测试，再追求覆盖率数字。对无测试基础的项目，起步门槛不宜过高。

| 指标 | M3 出口 | M4 出口 | 长期 |
|------|--------|---------|------|
| 总行覆盖 | ≥ 50% | ≥ 65% | ≥ 70% |
| stores/ | ≥ 70% | ≥ 80% | ≥ 85% |
| utils/ | ≥ 75% | ≥ 85% | ≥ 90% |
| protocol/ | ≥ 60% | ≥ 70% | ≥ 80% |
| services/api/ | ≥ 60% | ≥ 75% | ≥ 80% |
| hooks/ | ≥ 60% | ≥ 75% | ≥ 80% |
| components/business/ | ≥ 40% | ≥ 55% | ≥ 65% |
| pages/ | — | E2E 覆盖主旅程 | — |

> **注**：M3 阶段优先保证 stores/utils/hooks 核心模块达到目标，其他模块可放宽。

---

## 6. 关键 E2E 旅程（5 条主旅程）

> 这 5 条是产品的"生命线"，必须每次构建都跑过。引入时机：plan-M4。

### Journey-1：贷前完整旅程（最高优先级）

```
登录 → 工作台首页
     → 选择 created 任务 → 数据整合（上传材料）
     → 进入 analyzing → 等到 report_ready
     → 报告生成 → 编辑 → 提交审批
     → 任务状态 = under_review
```

**关键断言**：
- 任务状态机正确流转（不允许跳态）
- 数据引擎健康度展示正确
- 报告自动化率展示正确
- 提交后任务从张经理工作台消失，出现在审批人工作台

---

### Journey-2：贷中审批旅程

```
登录（审批人） → 审批看板 → 选 under_review 任务
              → 看摘要 → 看证据（合同对比）
              → 风险问答（AG-UI 流式）
              → 通过 / 退回 / 驳回
```

**关键断言**：
- 通过 → 状态变 approved
- 退回 → 状态回到 report_ready，附结构化意见
- 驳回 → 状态变 rejected
- 风险问答有引用、有流式输出

---

### Journey-3：贷后预警旅程

```
预警触发（mock 后端推送）
       → 工作台首页红色横条
       → 进入预警看板 → 风险追踪时间线
       → 处置（创建新尽调任务）
```

**关键断言**：
- 新预警 1 秒内出现在首页
- 时间线节点样式统一
- 处置动作能创建新尽调任务（自动跳转 created 态）

---

### Journey-4：智能体协议（AG-UI）

```
进入风险问答 → 输入问题
            → 流式接收 text_delta 事件
            → 中间出现 tool_call / tool_result
            → 最终 done
```

**关键断言**：
- 文本逐字渲染
- 工具调用过程可见（思考过程可观测）
- 异常时 error 事件能正确展示

---

### Journey-5：跨模块状态一致性

```
A 标签页：客户经理在 /report 编辑
B 标签页：审批人查看同一任务
A 提交审批 → B 实时看到状态变化（M4 引入 WS 后）
```

**关键断言**：
- 状态变更通过协议层广播
- 不出现"我刚改完，他还看到旧的"

---

## 7. 测试编写规范

### 7.1 命名

```typescript
// ✅ 推荐：describe 用名词，it 用"should + 行为"
describe('useApprovalStore', () => {
  it('should transition task from under_review to approved when approve() called', () => {});
  it('should preserve rejection reason when reject() called', () => {});
});

// ❌ 不推荐：含糊
describe('store', () => {
  it('test 1', () => {});
});
```

### 7.2 AAA 模式（Arrange-Act-Assert）

```typescript
it('should add comment to task on review', () => {
  // Arrange
  const { result } = renderHook(() => useApprovalStore());
  act(() => result.current.loadTask('task-001'));

  // Act
  act(() => result.current.addComment('需要补充流水'));

  // Assert
  expect(result.current.currentTask.comments).toHaveLength(1);
  expect(result.current.currentTask.comments[0].text).toBe('需要补充流水');
});
```

### 7.3 测试隔离

- 每个 `it` 必须**独立可跑**，不依赖前一个测试的副作用
- 用 `beforeEach` 重置 store / mock
- 用 `afterEach` 清理 timer / network mock

### 7.4 用户视角断言（RTL 哲学）

```typescript
// ✅ 推荐：找用户能看到的东西
expect(screen.getByRole('button', { name: '提交审批' })).toBeEnabled();

// ❌ 不推荐：找实现细节
expect(container.querySelector('.submit-btn-primary')).toBeTruthy();
```

### 7.5 异步测试

```typescript
// ✅ findBy 自动等待，3 秒超时
expect(await screen.findByText('已提交审批')).toBeInTheDocument();

// ❌ 不要写 setTimeout / sleep
```

---

## 8. Mock 策略

### 8.1 不同层级的 Mock

| 层级 | 工具 | 用法 |
|------|------|------|
| HTTP 网络层 | **MSW** | service 层之外，最真实 |
| 模块依赖 | `vi.mock('@/services/api')` | 单元测试隔离 service |
| 时间 | `vi.useFakeTimers()` | 测时间相关逻辑 |
| 浏览器 API | `happy-dom` 内置 / 手写 stub | localStorage / matchMedia |
| 协议事件流 | 手写 mock generator | AG-UI / A2UI 测试 |

### 8.2 MSW 示例

```typescript
// src/__tests__/helpers/mock-server.ts
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/enterprises/:id', ({ params }) => {
    return HttpResponse.json({ id: params.id, name: 'Mock Inc.' });
  }),
];

export const server = setupServer(...handlers);
```

```typescript
// src/__tests__/helpers/setup.ts
import { server } from './mock-server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 8.3 测试数据策略

- ✅ **Factory** 模式：`createMockTask({ status: 'under_review' })` 而非散落 fixture
- ✅ **demo-story** 数据可用于集成测试，但不能直接用于单元测试（耦合太重）
- ❌ 不要在测试里 hardcode 大段 JSON

---

## 9. CI 集成

> plan-M2 引入 GitHub Actions，plan-M3 加入测试 step。

```yaml
# .github/workflows/ci.yml
name: CI
on: [pull_request, push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm run lint
      - run: npx tsc -b --noEmit
      - run: npm run test:coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  e2e:                                   # M4 引入
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run build
      - run: npm run test:e2e
```

### 9.1 PR 质量门

- 单元 / 集成测试 **必须全绿**
- 覆盖率不能比 main 分支下降 > 2 个百分点
- E2E 主旅程必须全绿（M4 之后）

---

## 10. 测试不健康的信号

> 如果出现下面任何一个信号，停手讨论：

| 信号 | 含义 | 应对 |
|------|------|------|
| 改一行业务代码要改 5 个测试 | 测试与实现耦合过紧 | 重构测试，从用户视角断言 |
| 测试经常 flaky（时灵时不灵） | 异步处理 / Mock 不干净 | 立刻修，flaky 测试 = 没有测试 |
| 全套测试 > 30 秒（单元层） | 测试太重 / 真实 IO 没 mock | 隔离 IO，下沉到集成层 |
| 覆盖率高但 bug 不断 | 测试覆盖不到分支 | 看分支覆盖率，加用例 |
| 没人愿意写测试 | 工具链有问题 / 流程没强制 | 简化工具，CI 强制 |

---

## 11. 当前阶段的过渡方案（M0-M2）

由于 M3 才引入测试基础设施，**当前 0-3 个月用什么保证质量**？

| 阶段 | 替代方案 |
|------|---------|
| M0-M1 | TypeScript strict + ESLint + 手工 5 态自测清单（[tasks-TASK-M1-04]） |
| M2 | + CI lint/build 阻塞 + 1 条样例端到端切换冒烟 |
| M3 | 正式引入单元 + 集成测试 |
| M4 | 正式引入 E2E |

---

## 12. 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-06 | 首版，规划测试金字塔 + 5 条 E2E 主旅程 + 工具链选型 |
| v1.1 | 2026-05-06 | 降低覆盖率目标（M3: 50% 起步），使其更务实可达成 |

