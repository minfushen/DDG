# UI 重构设计 · 方案 C（混合分期）

> **决策**：采用「全局骨架与 Token 先行 → 按导航顺序逐页降噪」的混合路线。  
> **依据**：`docs/UNIFIED_VISUAL_MASTERPLAN.md`（两轮收敛 §6）、`docs/UI_DESIGN_SPEC.md`（PageHeader / SplitPane / KPI 上限）、`docs/specs/sdd-plan.md`（pages 薄层、组件化骨架）。

---

## 1. 目标与非目标

### 1.1 目标（本轮）

- **降低信息密度**：首屏「主焦点」≤ 5 个（舒适度验收 §5.1）。
- **降低视觉噪声**：减少重复 KPI、弱化装饰性渐变、统一状态语义色。
- **统一版式比例**：主栏 `1fr` + 侧栏固定语义宽度区间（约 `360–400px` 或等价 `grid` 比例），与 masterplan 对齐。
- **不引入新业务逻辑**：本次以布局、层级、展示折叠为主；数据仍来自现有 stores/mock。

### 1.2 非目标（刻意不做）

- 不接后端、不改协议层（AG-UI/A2UI）。
- 不大爆炸式重写所有页面为一个巨型组件。
- 不把视觉改成「炫彩营销站」；仍以金融工作台克制风格为准。

---

## 2. 分期交付（与现有代码对齐）

### 阶段 A · 全局骨架（1–2 个 PR）

**范围**：`MainLayout`、`Header`、`Sidebar`（必要时）、`PageHeader`、`SplitPane`、`SectionHeader`、`Card`、全局间距变量。

**具体动作（设计层面）**：

1. **页面外边距与节奏**：将内容区内边距对齐 masterplan（desktop **40** / tablet **24** / mobile **16**）。当前 `MainLayout` 为 `px-8 py-8 lg:px-10`，改为 token 化断点（避免 Magic Number 散落在页面）。
2. **区块纵向间距**：正文区块统一 `gap-6`（24px）；卡片内边距统一（大卡 24 / 小卡 16），优先落在共享组件而非每个页面。
3. **`SplitPane`（main-sidebar）**：在 `lg+` 下为右侧栏增加 **`max-w-[400px]`（或 `minmax(360px,400px)`）**，避免侧栏在不同页面「忽宽忽窄」造成比例跳跃。
4. **`PageHeader`**：维持 KPI ≤ 3（已在组件层 `slice(0,3)`）；审视是否仍有页面绕过 `PageHeader` 自建 KPI 墙——迁移到 `PageHeader.kpis` 或折叠到次级区域。
5. **噪声控制**：审查页面级渐变 Hero / 大块渐变背景；仅保留 `variant="risk"` 页面的警告渐变。

**验收**：任意相邻两页的「标题层级 + 外边距 + 侧栏宽度」无明显断裂；切换路由后 3 秒内能说出页面目的（舒适度 §5 第 4 条）。

---

### 阶段 B · 按导航顺序逐页降噪（多个小 PR）

顺序严格跟随 `docs/UNIFIED_VISUAL_MASTERPLAN.md` §6：

1. `Dashboard`（工作台）
2. `DataIntegration`
3. `Analysis`
4. `DocumentChecklist`
5. `PSAKValidation`
6. `Approval/*`（Dashboard → ContractCompare → RiskChat → FundFlow）
7. `PostLoan/*`
8. `Analytics`

**每页通用手法（设计模板）**：

| 手法 | 适用场景 |
|------|---------|
| **单一焦点** | 首页以任务列表为主；分析页以「评分摘要 + 图谱」为主，右侧画像为辅 |
| **折叠次要模块** | 说明性文案、历史记录、附加洞察 → `details` / `Accordion` / Tab |
| **合并重复 KPI** | 同一语义指标只出现一组；其余下沉到「展开查看更多」 |
| **固定侧栏信息架构** | 侧栏放「决策摘要 / 下一步动作」，不放第二套 KPI |
| **图表占位与最小高度** | 图谱区遵循 masterplan 最小高度理念，但避免固定死 `h-[600px]` 类违反 UI spec 的红线——改用 `min-h` + 自适应 |

**验收（每页 PR）**：对照 `UNIFIED_VISUAL_MASTERPLAN.md` §5 六条自检 + `UI_DESIGN_SPEC.md` 对应章节。

---

## 3. 架构约束（SDD）

- **Pages 保持薄**：降噪产生的结构组件放入 `src/components/business/` 或页面子目录 `components/`，避免单文件超 200 行（`plan.md` §1.2 工程债）。
- **不在页面直接 import mock**：若重构触碰数据，统一从 store 注入（与 `plan.md` §2.2 一致）。
- **颜色**：继续只认 `src/theme/tokens.ts`（`constitution.md` §2.2）。

---

## 4. 测试与回归（务实）

与 `docs/specs/test.md` v1.1 对齐：**本轮不以覆盖率门槛阻塞**，以手工回归为主：

- `npm run build`、`npm run lint` 必须通过。
- 关键路径冒烟：工作台 → 数据整合 → 智能分析 → 报告（至少验证布局不崩、滚动正常）。

自动化测试留在 **M3** 按 `test.md` 引入 Vitest 后补。

---

## 5. 开放决策（实施前需你拍板）

1. **侧栏宽度策略**：全局固定 `max-w-[400px]` vs 按页面 `380/400` 微调——默认采用 **全局固定上限**，减少切换跳跃。
2. **折叠交互**：优先原生 `<details>` / 轻量按钮展开，避免引入新依赖。

---

## 6. 审批 Gate

- [ ] 产品/设计认同阶段 A + 阶段 B 的范围与顺序  
- [ ] 技术认同 SplitPane / MainLayout 的调整不会影响路由与状态  

**批准后**：进入实现阶段（建议每个页面独立 PR，附前后截图与同分辨率对比）。

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-05-06 | 用户选定方案 C，输出混合分期设计 |

