# UI Refactor Task List

> 目标：将当前项目前端从“页面各自为战”收敛为“统一设计语言、统一布局骨架、统一交互语义”的金融工作台系统。

## 1. 使用说明

- 本文档按文件拆分改造任务，适合作为前端实施清单、设计对齐清单、PR 拆分依据。
- 优先级说明：
  - `P0`：先做，影响全站一致性或高频页面体验。
  - `P1`：第二阶段，影响核心流程完整性。
  - `P2`：收尾优化，影响精致度和长期维护性。
- 验收方式：
  - 页面视觉一致性
  - 响应式表现
  - 交互状态完整性
  - 是否清除硬编码和重复样式

---

## 2. 全局改造原则

### 2.1 统一视觉语言

- 业务页主色统一为品牌蓝体系。
- 成功、警告、危险、信息色仅用于状态语义，不再作为随意装饰色大面积铺开。
- 停止在业务页继续使用 `purple/pink/cyan` 作为主视觉强调。
- Hero 只保留两类：
  - 轻量页头：标题、副标题、关键操作。
  - 风险页头：仅用于预警、异常、审查告警类页面。

### 2.2 统一布局骨架

- 页头、区块头、KPI 卡、双栏/三栏布局必须组件化。
- 不允许页面继续大量自定义 `min-h-screen bg-surface-page p-8`。
- 所有 `grid-cols-3`、`grid-cols-4`、固定高度布局改为响应式。
- 重信息页面优先保障首屏核心任务区，不允许被装饰性 Hero 挤压。

### 2.3 统一交互语义

- 所有关键页面必须补齐：
  - loading
  - empty
  - error
  - disabled
  - hover
  - focus
- 不做真实功能的入口不能伪装成可用功能。
- 状态表达优先通过结构和文案，其次才是颜色。

---

## 3. 分阶段执行建议

### Phase 1：全局基础设施

- `P0` `src/index.css`
- `P0` `src/theme/tokens.ts`
- `P0` `src/components/ui/SectionHeader.tsx`
- `P0` `src/components/ui/PageHeader.tsx`
- `P0` `src/components/ui/StatCard.tsx`
- `P0` `src/components/layout/Header.tsx`
- `P1` `src/components/layout/MainLayout.tsx`
- `P1` `src/components/layout/Sidebar.tsx`
- `P1` `src/components/ui/index.ts`
- `P0` `docs/UI_DESIGN_SPEC.md`

### Phase 2：高优先级代表页

- `P0` `src/pages/Dashboard/index.tsx`
- `P0` `src/pages/Approval/RiskChat/index.tsx`
- `P0` `src/pages/Approval/ContractCompare/index.tsx`

### Phase 3：核心业务流程页

- `P1` `src/pages/DataIntegration/index.tsx`
- `P1` `src/pages/Analysis/index.tsx`
- `P1` `src/pages/ReportGenerator/index.tsx`
- `P1` `src/pages/Approval/ApprovalDashboard/index.tsx`
- `P1` `src/pages/Approval/FundFlow/index.tsx`

### Phase 4：工具与配置页

- `P1` `src/pages/DocumentChecklist/index.tsx`
- `P1` `src/components/ui/ChecklistMatrix.tsx`
- `P1` `src/pages/PSAKValidation/index.tsx`
- `P1` `src/pages/PostLoan/WarningConfig/index.tsx`
- `P1` `src/pages/AgentConfig/index.tsx`
- `P1` `src/pages/Analytics/index.tsx`

### Phase 5：贷后运营页

- `P1` `src/pages/PostLoan/WarningDashboard/index.tsx`
- `P1` `src/pages/PostLoan/RiskTracking/index.tsx`
- `P1` `src/pages/PostLoan/PostLoanCheck/index.tsx`

### Phase 6：回归清理

- `P0` 全仓样式扫描与收尾
- `P1` 通用状态组件回归

---

## 4. 按文件拆分任务单

### 4.1 全局样式与 Token

#### `P0` [src/index.css](/Users/admin/due-diligence-platform/src/index.css)

**目标**

- 把当前“全局可用但不够约束”的样式层改成真正的设计基础层。

**改造任务**

- 收敛全局背景、文字、边框、滚动条、动画默认值。
- 增加统一页面容器类约定：
  - 页面外层容器
  - 内容最大宽度容器
  - 标准区块间距
  - 响应式栅格间距
- 补充统一的卡片、表单、表格、列表、侧栏布局语义类。
- 弱化全局装饰性渐变默认存在感。

**验收标准**

- 页面容器不再需要每页重复写大段基础背景和留白类名。
- 视觉层级以边框和留白为主，阴影为辅。

#### `P0` [src/theme/tokens.ts](/Users/admin/due-diligence-platform/src/theme/tokens.ts)

**目标**

- 让 token 真正成为唯一设计语义来源。

**改造任务**

- 保留并强化以下语义：
  - brand
  - success
  - warning
  - danger
  - info
- 审核并收敛不适合业务页扩散使用的渐变和语义别名。
- 增加布局 token 说明：
  - page spacing
  - content width
  - card density
- 对组件常用状态映射补注释和命名约束。

**验收标准**

- 新页面不需要手写品牌色 hex。
- 后续页面中主视觉来源能追溯到 token。

#### `P0` [docs/UI_DESIGN_SPEC.md](/Users/admin/due-diligence-platform/docs/UI_DESIGN_SPEC.md)

**目标**

- 将现有规范升级为与代码演进一致的执行规范。

**改造任务**

- 增加页面骨架规范：
  - `PageHeader`
  - `SectionHeader`
  - `KpiStrip`
  - `SplitPane`
- 补充 Hero 使用场景边界。
- 补充响应式规范：
  - 单列
  - 双列
  - 2/3 + 1/3
- 补充工具页、分析页、配置页、列表页四类页面模板。
- 增加禁用模式清单：
  - 紫粉聊天视觉
  - 固定 600px 主内容高度
  - 页面级重复大 Hero

**验收标准**

- 文档能直接指导后续 PR。
- 文档与代码不再相互冲突。

---

### 4.2 通用 UI 组件

#### `P0` [src/components/ui/SectionHeader.tsx](/Users/admin/due-diligence-platform/src/components/ui/SectionHeader.tsx)

**目标**

- 统一区块头结构，替代页面内自定义标题块。

**改造任务**

- 支持：
  - `title`
  - `subtitle`
  - `actions`
  - `meta`
  - `tone`
- 提供普通、风险、成功三类轻语义模式。
- 统一标题字号、图标尺寸、间距。

**验收标准**

- 页面区块不再手写 `icon + h3 + p` 组合。

#### `P0` [src/components/ui/PageHeader.tsx](/Users/admin/due-diligence-platform/src/components/ui/PageHeader.tsx)

**目标**

- 替换大部分页面当前的重 Hero 或零散标题。

**改造任务**

- 统一页头 API：
  - `title`
  - `subtitle`
  - `meta`
  - `primaryAction`
  - `secondaryActions`
  - `kpis`
  - `variant`
- 支持两种变体：
  - standard
  - risk
- 兼容企业信息页头、流程页头、列表页头。

**验收标准**

- 页面首屏无需再手写大面积蓝色块。

#### `P0` [src/components/ui/StatCard.tsx](/Users/admin/due-diligence-platform/src/components/ui/StatCard.tsx)

**目标**

- 把 KPI 卡统一成一套密度和层级。

**改造任务**

- 统一卡片高度、图标容器、数字字号、趋势信息层级。
- 加入响应式表现，避免在窄屏一排 4 个挤压。
- 提供普通、风险、成功三类 tone。

**验收标准**

- Dashboard、WarningDashboard、Analytics 等页复用同一 KPI 卡风格。

#### `P1` `src/components/ui/SplitPane.tsx`

**目标**

- 提供标准双栏/三栏布局封装。

**改造任务**

- 支持：
  - `two-column`
  - `three-column`
  - `main-sidebar`
  - `document-compare`
- 内置断点塌缩规则。
- 支持固定侧栏和自适应主内容。

**验收标准**

- 数据整合、分析、报告、对比、贷后详情等页不再各自拼布局。

#### `P1` [src/components/ui/index.ts](/Users/admin/due-diligence-platform/src/components/ui/index.ts)

**目标**

- 统一导出入口，降低后续页面改造摩擦。

**改造任务**

- 导出 `PageHeader`、`SectionHeader`、`StatCard`、`SplitPane`。
- 清理历史命名和未使用导出。

---

### 4.3 布局框架

#### `P0` [src/components/layout/Header.tsx](/Users/admin/due-diligence-platform/src/components/layout/Header.tsx)

**目标**

- 将 Header 从“静态顶栏”改成“全局导航 + 当前页面上下文”。

**改造任务**

- 让页面标题由路由或页面传入，不再固定默认文案。
- 将搜索框降为辅助入口，不再占据视觉中心。
- 移除未实现的深色模式切换，或改为非交互状态。
- 优化窄屏宽度分配，移除固定 `180px + 180px + min 320px` 挤压模型。
- 精简通知、用户区域视觉噪音。

**验收标准**

- 中等宽度窗口下不拥挤。
- Header 对当前页面有明确上下文表达。

#### `P1` [src/components/layout/MainLayout.tsx](/Users/admin/due-diligence-platform/src/components/layout/MainLayout.tsx)

**目标**

- 全局统一主内容滚动和边距策略。

**改造任务**

- 把页面通用 padding、内容宽度、滚动方式沉入 Layout。
- 减少页面自己控制最外层高度。
- 为大内容页和标准内容页提供差异化容器能力。

**验收标准**

- 页面不再普遍写 `min-h-screen bg-surface-page p-8`。

#### `P1` [src/components/layout/Sidebar.tsx](/Users/admin/due-diligence-platform/src/components/layout/Sidebar.tsx)

**目标**

- 提升折叠态可用性和模块级导航清晰度。

**改造任务**

- 为折叠态补 tooltip 或最小文案提示。
- 强化当前模块级高亮，而不只是单个菜单项高亮。
- 优化分组标题与菜单项密度。

**验收标准**

- 折叠态仍可识别导航意图。

#### `P1` [src/App.tsx](/Users/admin/due-diligence-platform/src/App.tsx)

**目标**

- 建立页面标题与全局壳层的映射。

**改造任务**

- 为路由补页面标题配置。
- 配合 Header 传递当前页面语义。

---

### 4.4 第一批高优先级页面

#### `P0` [src/pages/Dashboard/index.tsx](/Users/admin/due-diligence-platform/src/pages/Dashboard/index.tsx)

**目标**

- 把工作台改成真正高频操作入口。

**改造任务**

- 用 `PageHeader` 替换大蓝 Hero。
- 保留 1 个主按钮和 1 至 2 个次级入口。
- KPI 从 4 个压缩到 3 个主指标。
- 任务列表上移到首屏核心。
- 将筛选区重构为真实控制栏：
  - 状态
  - 类型
  - 排序
- 提升任务列表信息密度，降低装饰性卡片感。

**验收标准**

- 用户首屏能直接看到任务列表并开始操作。

#### `P0` [src/pages/Approval/RiskChat/index.tsx](/Users/admin/due-diligence-platform/src/pages/Approval/RiskChat/index.tsx)

**目标**

- 将聊天页从“泛 AI 助手”改为“基于底稿证据的风险问答”。

**改造任务**

- 全量去掉紫粉主视觉，收回品牌蓝灰体系。
- 取消固定 `h-[calc(100vh-180px)]`。
- 文档区改成更强证据面板：
  - 当前文档
  - 引用命中
  - 页码
  - 快速跳转
- 欢迎态文案改为业务导向。
- 快捷问题按业务主题分组。
- 输入区和消息区状态统一。

**验收标准**

- 页面不再像独立聊天产品。
- 文档与问答关系更明确。

#### `P0` [src/pages/Approval/ContractCompare/index.tsx](/Users/admin/due-diligence-platform/src/pages/Approval/ContractCompare/index.tsx)

**目标**

- 强化“差异处理”而非“三栏平均展示”。

**改造任务**

- 头部改为轻量流程页头。
- 三栏改成响应式比重布局：
  - 文档 30
  - 差异 40
  - 文档 30
- 去掉固定 `600px` 高度。
- 文档区改成更中性的可读底板。
- 差异卡减少同时出现的蓝底、紫底、风险底。
- CTA 文案改为更明确的动作型语言。

**验收标准**

- 差异列表成为视觉主轴。
- 文档阅读不再拥挤和疲劳。

---

### 4.5 第二批核心业务页

#### `P1` [src/pages/DataIntegration/index.tsx](/Users/admin/due-diligence-platform/src/pages/DataIntegration/index.tsx)

**改造任务**

- 页头改为标准企业页头。
- 主体改成 `2/3 + 1/3`。
- 上传区成为首屏主任务区。
- AI 解析过程和交叉核验降为次级信息。
- 右侧 CTA 固定在侧栏逻辑收尾区。

#### `P1` [src/pages/Analysis/index.tsx](/Users/admin/due-diligence-platform/src/pages/Analysis/index.tsx)

**改造任务**

- 页头标准化。
- 结构改为：
  - 结论与评级
  - 图谱
  - 风险摘要与风险因素
- 分项评分收敛为更紧凑的横向结构。
- 节点详情改成侧板或抽屉。

#### `P1` [src/pages/ReportGenerator/index.tsx](/Users/admin/due-diligence-platform/src/pages/ReportGenerator/index.tsx)

**改造任务**

- 减少编辑器区装饰性视觉。
- 工具条做轻量专业化。
- 大纲区改为更像文档导航。
- 右侧面板重组为证据、AI 辅助、思维链三段。
- 高亮溯源样式更克制。

#### `P1` [src/pages/Approval/ApprovalDashboard/index.tsx](/Users/admin/due-diligence-platform/src/pages/Approval/ApprovalDashboard/index.tsx)

**改造任务**

- 左侧任务池提升信息密度和选中识别度。
- 头部高度压缩。
- 放款前提条件支持“仅看失败/待补充”。
- 风险变化区按严重度排序。

#### `P1` [src/pages/Approval/FundFlow/index.tsx](/Users/admin/due-diligence-platform/src/pages/Approval/FundFlow/index.tsx)

**改造任务**

- 图谱为主，异常侧栏聚合为辅。
- 增强违规路径、可疑节点、无票流向的聚焦能力。
- 右侧面板统一为异常清单结构。

---

### 4.6 第三批工具与配置页

#### `P1` [src/pages/DocumentChecklist/index.tsx](/Users/admin/due-diligence-platform/src/pages/DocumentChecklist/index.tsx)

**改造任务**

- 从 AI 展示页收敛为资料管理页。
- 压缩 AI 看板高度。
- 缺失清单与分类标签云减少重复表达。
- 提升清单明细的管理感。

#### `P1` [src/components/ui/ChecklistMatrix.tsx](/Users/admin/due-diligence-platform/src/components/ui/ChecklistMatrix.tsx)

**改造任务**

- 强化矩阵表格感。
- 弱化卡片嵌套卡片感。
- 补窄屏横向滚动或分组切换方案。

#### `P1` [src/pages/PSAKValidation/index.tsx](/Users/admin/due-diligence-platform/src/pages/PSAKValidation/index.tsx)

**改造任务**

- 页头并入统一系统视觉。
- 右侧结果面板增加摘要和分组。
- 校验动作区上收，明确主任务。

#### `P1` [src/pages/PostLoan/WarningConfig/index.tsx](/Users/admin/due-diligence-platform/src/pages/PostLoan/WarningConfig/index.tsx)

**改造任务**

- 去掉 `purple` 图标渐变。
- 从卡片瀑布流改成规则后台结构：
  - 顶部总览
  - 筛选
  - 规则列表
  - 展开或抽屉详情
- 提升信息密度与可扫描性。

#### `P1` [src/pages/AgentConfig/index.tsx](/Users/admin/due-diligence-platform/src/pages/AgentConfig/index.tsx)

**改造任务**

- 减少“展示感”，提升“配置感”。
- 编排区加强秩序和选中态准备。
- Prompt 区更像配置表单，不像 demo 文本块。

#### `P1` [src/pages/Analytics/index.tsx](/Users/admin/due-diligence-platform/src/pages/Analytics/index.tsx)

**改造任务**

- 与主系统视觉统一。
- 降低呼吸光效和运营大盘感。
- KPI 与图形组件复用统一卡片体系。

---

### 4.7 第四批贷后运营页

#### `P1` [src/pages/PostLoan/WarningDashboard/index.tsx](/Users/admin/due-diligence-platform/src/pages/PostLoan/WarningDashboard/index.tsx)

**改造任务**

- 风险页头保留，但压缩高度和装饰。
- KPI 从 4 个压到 3 个首屏主指标。
- 修复浅底白图标对比度问题。
- 强化“紧急预警”和“待处理预警”的运营列表感。

#### `P1` [src/pages/PostLoan/RiskTracking/index.tsx](/Users/admin/due-diligence-platform/src/pages/PostLoan/RiskTracking/index.tsx)

**改造任务**

- 页头压缩。
- 主体改成详情、时间线、操作三段式。
- 时间线改成案件处理流风格。
- 状态变更按钮层级更明确。

#### `P1` [src/pages/PostLoan/PostLoanCheck/index.tsx](/Users/admin/due-diligence-platform/src/pages/PostLoan/PostLoanCheck/index.tsx)

**改造任务**

- 压缩头部。
- 强化列表化和批量管理感。
- “新建检查”提升到页头主操作位置。

---

### 4.8 回归与清理

#### `P0` 全仓样式扫描

**扫描重点**

- `purple-`
- `pink-`
- 固定 `h-[600px]`
- 页面级重复 Hero
- 大量 `grid-cols-4`
- 页面自带 `min-h-screen bg-surface-page`

#### `P1` 状态组件回归

**涉及文件**

- [src/components/ui/Skeleton.tsx](/Users/admin/due-diligence-platform/src/components/ui/Skeleton.tsx)
- [src/components/ui/Toast.tsx](/Users/admin/due-diligence-platform/src/components/ui/Toast.tsx)
- [src/components/business/EnterpriseHeader.tsx](/Users/admin/due-diligence-platform/src/components/business/EnterpriseHeader.tsx)

**改造任务**

- 与新卡片、边框、阴影规范统一。
- 避免旧风格残留。

---

## 5. 建议 PR 拆分

### PR 1：全局设计基础层

- `src/index.css`
- `src/theme/tokens.ts`
- `src/components/ui/SectionHeader.tsx`
- `src/components/ui/PageHeader.tsx`
- `src/components/ui/StatCard.tsx`
- `src/components/ui/index.ts`
- `docs/UI_DESIGN_SPEC.md`

### PR 2：全局布局壳层

- `src/components/layout/Header.tsx`
- `src/components/layout/MainLayout.tsx`
- `src/components/layout/Sidebar.tsx`
- `src/App.tsx`

### PR 3：高优先级代表页

- `src/pages/Dashboard/index.tsx`
- `src/pages/Approval/RiskChat/index.tsx`
- `src/pages/Approval/ContractCompare/index.tsx`

### PR 4：核心业务页

- `src/pages/DataIntegration/index.tsx`
- `src/pages/Analysis/index.tsx`
- `src/pages/ReportGenerator/index.tsx`
- `src/pages/Approval/ApprovalDashboard/index.tsx`
- `src/pages/Approval/FundFlow/index.tsx`

### PR 5：工具与配置页

- `src/pages/DocumentChecklist/index.tsx`
- `src/components/ui/ChecklistMatrix.tsx`
- `src/pages/PSAKValidation/index.tsx`
- `src/pages/PostLoan/WarningConfig/index.tsx`
- `src/pages/AgentConfig/index.tsx`
- `src/pages/Analytics/index.tsx`

### PR 6：贷后运营页与回归

- `src/pages/PostLoan/WarningDashboard/index.tsx`
- `src/pages/PostLoan/RiskTracking/index.tsx`
- `src/pages/PostLoan/PostLoanCheck/index.tsx`
- `src/components/ui/Skeleton.tsx`
- `src/components/ui/Toast.tsx`
- `src/components/business/EnterpriseHeader.tsx`

---

## 6. 最终验收清单

- 所有页面都能明确看出属于同一个产品。
- 高风险页面和普通业务页面有区别，但不割裂。
- 中等宽度窗口下不出现严重挤压。
- 不再存在明显的紫粉聊天页、固定 600px 主内容区、重复蓝色 Hero 模板。
- 区块标题、页头、KPI、双栏布局均已组件化。
- 页面首屏都能回答：
  - 我在哪
  - 当前最重要的是什么
  - 下一步做什么
