# 金融工作台 UI 统一整改任务单

> 从"很多好看的单页"收敛成"一套可信的金融工作台"

## 核心原则

### 视觉基线
- **主色**: 品牌蓝作为主操作色，成功/警告/危险只用于状态
- **禁止**: `purple/pink/cyan` 大面积装饰
- **Hero**: 仅两种样式 - 轻量页头 / 风险页头
- **圆角**: 卡片 `rounded-2xl`，按钮/输入框 `rounded-lg`
- **阴影**: 边框分层为主，悬浮才加轻阴影

### 信息架构
- 首屏回答：我在哪、当前最重要的是什么、下一步做什么
- KPI 卡片 ≤ 3 个，超过折叠
- 核心工作区必须进入首屏

### 响应式规范
- mobile: 单列
- tablet: 双列
- desktop: 2/3 + 1/3 或自适应
- 禁止固定 `h-[600px]` 和大面积 `min-h-screen`

---

## A. 全局设计基建

### A.1 `P0` 修改 src/index.css
**目标**: 清理页面级硬编码主色和装饰性渐变的默认依赖

**改动点**:
- [ ] 移除 `purple/pink/cyan` 相关的全局装饰类
- [ ] 补充统一的页面容器工具类: `.page-container`, `.section-container`
- [ ] 补充卡片工具类: `.card-base`, `.card-elevated`
- [ ] 补充表单工具类: `.form-section`, `.form-row`
- [ ] 补充分栏工具类: `.split-2-1`, `.split-1-1`, `.split-1-2`
- [ ] 补充响应式断点约定

**验收标准**: 全局不再新增 `purple/pink/cyan` 业务强调色

### A.2 `P0` 修改 src/theme/tokens.ts
**目标**: 收敛颜色语义，补布局 token

**改动点**:
- [ ] 颜色收敛为五类: `brand`, `success`, `warning`, `danger`, `info`
- [ ] 移除 `ai/purple` 倾向的业务扩散值
- [ ] 补充布局 token: `--page-max-width`, `--sidebar-width`, `--header-height`
- [ ] 补充间距 token: `--section-gap`, `--card-padding`

**验收标准**: 后续页面只从 token 取色

### A.3 `P0` 修改 docs/UI_DESIGN_SPEC.md
**目标**: 规范改成"当前真实实现目标版"

**改动点**:
- [ ] 增加页面骨架规范: PageHeader + SectionHeader + Content 三层结构
- [ ] 增加 Hero 使用条件: 仅轻量页头 / 风险页头两种
- [ ] 增加响应式断点规范
- [ ] 增加表格与工具页规范
- [ ] 移除过时的装饰性渐变示例

---

## B. 通用组件层

### B.1 `P0` 修改 src/components/ui/SectionHeader.tsx
**目标**: 扩展为统一区块头

**改动点**:
- [ ] 支持主副标题 (已有)
- [ ] 支持右侧操作区 (已有 children)
- [ ] 新增 `variant: 'default' | 'risk'` 风险语义模式
- [ ] 新增 `size: 'sm' | 'md' | 'lg'` 尺寸控制

**组件接口**:
```typescript
interface SectionHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  variant?: 'default' | 'risk';
  size?: 'sm' | 'md' | 'lg';
  children?: React.ReactNode;
  className?: string;
}
```

### B.2 `P0` 修改 src/components/ui/PageHeader.tsx
**目标**: 从"白卡页头"升级为真正的页面级头部组件

**改动点**:
- [ ] 支持 `title/subtitle/meta/actions/kpis`
- [ ] 支持 `variant: 'light' | 'risk'` 两种模式
- [ ] 轻量页头: 标题 + 副标题 + 关键操作
- [ ] 风险页头: 仅用于预警/异常页面，允许更强提示色

**组件接口**:
```typescript
interface PageHeaderProps {
  title: string;
  subtitle?: string;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  kpis?: KpiItem[];
  variant?: 'light' | 'risk';
  className?: string;
}

interface KpiItem {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'flat';
  variant?: 'default' | 'success' | 'warning' | 'danger';
}
```

### B.3 `P0` 修改 src/components/ui/StatCard.tsx
**目标**: 统一 KPI 卡的密度、字号、图标、趋势样式

**改动点**:
- [ ] 统一密度: 紧凑型 `py-3 px-4`，标准型 `py-4 px-5`
- [ ] 统一字号: 标题 `text-sm`，数值 `text-2xl`
- [ ] 统一图标尺寸: `w-8 h-8`
- [ ] 支持响应式: 移动端全宽，平板半宽，桌面 1/3 宽

### B.4 `P1` 新增 src/components/ui/SplitPane.tsx
**目标**: 统一双栏/三栏布局

**改动点**:
- [ ] 支持双栏: `left/right` 比例可配置
- [ ] 支持三栏: `left/center/right`
- [ ] 桌面分栏，平板塌缩为上下，移动端单列
- [ ] 支持侧栏折叠

**组件接口**:
```typescript
interface SplitPaneProps {
  left: React.ReactNode;
  right?: React.ReactNode;
  center?: React.ReactNode;
  ratio?: '2-1' | '1-1' | '1-2' | '3-1-1';
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  className?: string;
}
```

### B.5 `P1` 修改 src/components/ui/index.ts
**目标**: 导出新组件

**改动点**:
- [ ] 导出 `PageHeader`
- [ ] 导出 `SplitPane`
- [ ] 更新 `StatCard` 导出

**验收标准**: 页面标题、区块标题、KPI 卡、双栏布局不再各页自定义一套

---

## C. 全局框架

### C.1 `P0` 修改 src/components/layout/Header.tsx
**目标**: 响应式头部，移除假功能

**改动点**:
- [ ] 移除深色模式切换按钮（未实现）
- [ ] 缩弱搜索框权重: 从视觉中心降为辅助入口
- [ ] 标题由路由/页面传入，不再硬编码"对公尽调工作台"
- [ ] 左右固定 `180px` 改成响应式自适应
- [ ] 搜索框添加 `disabled` 或 placeholder 说明"功能开发中"

**当前问题**:
```tsx
// 问题1: 硬编码标题
<h2>{title || '对公尽调工作台'}</h2>

// 问题2: 假深色模式
const [darkMode, setDarkMode] = useState(false);

// 问题3: 搜索框视觉权重过高
<div className="flex flex-1 justify-center px-8">
```

### C.2 `P1` 修改 src/components/layout/MainLayout.tsx
**目标**: 统一主内容区

**改动点**:
- [ ] 统一主内容区宽度: `max-w-[1440px]`
- [ ] 统一滚动策略: 内容区滚动，非页面滚动
- [ ] 统一页面 padding: `p-6` 而非每页自己 `min-h-screen + p-8`

### C.3 `P1` 修改 src/components/layout/Sidebar.tsx
**目标**: 优化折叠态和模块高亮

**改动点**:
- [ ] 折叠态添加 tooltip/label 支持
- [ ] 增加当前模块级高亮（不只高亮单个菜单）
- [ ] 优化分组视觉层级

### C.4 `P1` 修改 src/App.tsx
**目标**: 为每个页面提供稳定标题来源

**改动点**:
- [ ] 路由配置增加 `title` 字段
- [ ] Header 从路由读取当前页面标题

**验收标准**: 所有页面进入统一壳层后，不再各自控制整体视口高度和主边距

---

## D. 第一批高优先级页面

### D.1 `P0` 修改 src/pages/Dashboard/index.tsx
**目标**: 用新组件重构首屏

**改动点**:
- [ ] Hero 改为轻量页头: `PageHeader` + 保留"需关注任务数"
- [ ] 4 个统计卡改为 3 个核心 KPI: `StatCard` 响应式
- [ ] 任务列表提升到首屏核心位置
- [ ] 筛选器重构为真实控制栏: 状态 Tabs + 类型筛选 + 排序
- [ ] `查看月报`、`数据引擎` 降到次级入口

**当前问题**:
```tsx
// 问题1: 大 Hero 占首屏
<div className="bg-gradient-to-r from-blue-600 to-indigo-600 ...">

// 问题2: 4 个统计卡
{stats.map((stat) => (...))}

// 问题3: 任务列表像展示卡，不像工作台
```

### D.2 `P0` 修改 src/pages/Approval/RiskChat/index.tsx
**目标**: 改回品牌蓝灰体系

**改动点**:
- [ ] 移除紫粉视觉，改回品牌蓝灰
- [ ] 去掉固定高度锁死
- [ ] 重做左右结构，强化"证据驱动问答"
- [ ] 左侧文档阅读器增强证据感: 显示文档状态、页码、命中高亮
- [ ] 快捷问题按业务分类展示

**当前问题**:
```tsx
// 问题: 紫粉渐变
<div className="bg-gradient-to-br from-purple-500 to-pink-500">
```

### D.3 `P0` 修改 src/pages/Approval/ContractCompare/index.tsx
**目标**: 重构为"差异主导"的阅读模式

**改动点**:
- [ ] 三栏等宽改为 `30/40/30` 或双栏切换
- [ ] 移除固定 `600px` 文档区
- [ ] 差异卡统一中性底，仅靠侧边色条区分
- [ ] 主按钮文案改为"提交修订建议"

**当前问题**:
```tsx
// 问题1: 固定高度
<div className="h-[600px]">

// 问题2: 三栏等宽
<div className="grid grid-cols-3">

// 问题3: 差异卡颜色过多
className="bg-blue-50" / className="bg-purple-50"
```

**验收标准**: 这三页改完后，能代表整套产品的新视觉方向

---

## E. 第二批核心业务页

### E.1 `P1` 修改 src/pages/DataIntegration/index.tsx
**改动点**:
- [ ] 企业头部改为标准企业页头
- [ ] 三栏改成 `主内容 2/3 + 侧栏 1/3`
- [ ] 上传区单独放大为主任务
- [ ] 解析过程和交叉核验降为次级模块
- [ ] 三张 AI 解析卡只强调当前正在运行的那一项

### E.2 `P1` 修改 src/pages/Analysis/index.tsx
**改动点**:
- [ ] 页头改轻，首屏先给"结论 + 风险等级 + 下一步"
- [ ] 重组层级: 顶部综合评级 + 中部知识图谱 + 底部风险摘要
- [ ] 三个分项评分卡合并为横向评分条
- [ ] 节点详情面板改成右侧抽屉

### E.3 `P1` 修改 src/pages/ReportGenerator/index.tsx
**改动点**:
- [ ] 减少装饰色，用"文档编辑器"逻辑
- [ ] 左侧编辑器更像文档产品: 顶部工具条精简、大纲锚点导航、编辑区背景纯白
- [ ] 右侧面板改成"证据/AI/思维链"三级结构
- [ ] 高亮溯源样式更克制

### E.4 `P1` 修改 src/pages/Approval/ApprovalDashboard/index.tsx
**改动点**:
- [ ] 左侧任务池提升信息密度
- [ ] 详情头部收缩高度
- [ ] 放款前提条件区支持"仅看失败/待补充"
- [ ] 风险变化区支持严重程度排序

### E.5 `P1` 修改 src/pages/Approval/FundFlow/index.tsx
**改动点**:
- [ ] 右侧改为异常账户、无票流向、违规金额三组聚合
- [ ] ECharts 区增强留白和图例层级
- [ ] 侧栏卡片样式简化

**验收标准**: 前中台核心流程页的布局逻辑统一，首屏都能清楚回答"结论和下一步"

---

## F. 第三批规则/工具页

### F.1 `P1` 修改 src/pages/DocumentChecklist/index.tsx
**改动点**:
- [ ] 从"AI 展示页"收敛为"资料管理页"
- [ ] AI 看板卡压缩高度
- [ ] 4 项指标改响应式
- [ ] 缺失清单和 AI 分类标签云二选一

### F.2 `P1` 修改 src/components/ui/ChecklistMatrix.tsx
**改动点**:
- [ ] 强化表格感，弱化卡片感
- [ ] 补移动端横向滚动/分段视图策略

### F.3 `P1` 修改 src/pages/PSAKValidation/index.tsx
**改动点**:
- [ ] 页头收回品牌蓝体系
- [ ] 右侧校验结果增加分组和筛选
- [ ] 通过/失败/偏差统计放成顶部摘要带

### F.4 `P1` 修改 src/pages/PostLoan/WarningConfig/index.tsx
**改动点**:
- [ ] 移除 `purple` 渐变
- [ ] 改成规则后台样式: 顶部总览 + 筛选条 + 规则列表
- [ ] 一条规则一张大卡改为列表行 + 展开详情

### F.5 `P1` 修改 src/pages/AgentConfig/index.tsx
**改动点**:
- [ ] 从 demo 展示感改成配置后台感
- [ ] 弱化渐变和装饰
- [ ] 强化编排区秩序
- [ ] Prompt 区更像配置表单

### F.6 `P1` 修改 src/pages/Analytics/index.tsx
**改动点**:
- [ ] 与主系统统一
- [ ] 降低呼吸光效
- [ ] 减少彩色状态标签数量

**验收标准**: 工具/配置页与业务页虽然信息形态不同，但看起来属于同一个系统

---

## G. 第四批贷后页面

### G.1 `P1` 修改 src/pages/PostLoan/WarningDashboard/index.tsx
**改动点**:
- [ ] 保留风险语义但压缩黄色 Hero
- [ ] 修复浅底白图标对比度问题 (Shield 白字浅底)
- [ ] 4 个 KPI 压到 3 个，"本月新增"放到次级区
- [ ] 增加"按企业聚合/按来源聚合"切换

### G.2 `P1` 修改 src/pages/PostLoan/RiskTracking/index.tsx
**改动点**:
- [ ] 头部收缩
- [ ] 重排成"预警详情/处置时间线/状态操作"三段式
- [ ] 时间线卡片更像案件处理流

### G.3 `P1` 修改 src/pages/PostLoan/PostLoanCheck/index.tsx
**改动点**:
- [ ] 头部压缩
- [ ] 卡片表格化，提升批量管理效率
- [ ] "新建检查"固定在页面主标题区

**验收标准**: 贷后模块形成统一的"风险运营后台"体验

---

## H. 清理与回归

### H.1 `P0` 全仓扫描清理
**目标**: 清理旧风格代码

**清理清单**:
- [ ] `purple-` 相关类名
- [ ] `pink-` 相关类名
- [ ] `h-[600px]` 固定高度
- [ ] `grid-cols-4` 无断点网格
- [ ] 重复 Hero 组件
- [ ] 页面级 `min-h-screen bg-surface-page`

### H.2 `P1` 检查状态组件
**文件**:
- src/components/ui/Skeleton.tsx
- src/components/ui/Toast.tsx
- src/components/business/EnterpriseHeader.tsx

**目标**: 保证状态组件也跟新设计一致

### H.3 `P1` 补交互状态
**目标**: 关键页落地五类状态

**状态清单**:
- [ ] loading - 加载态
- [ ] empty - 空状态
- [ ] error - 错误态
- [ ] disabled - 禁用态
- [ ] focus/hover - 聚焦/悬浮态

**验收标准**: 不再存在明显"旧风格页面"或"旧风格组件"

---

## 执行顺序

```
Phase 1: 全局 token、Header、PageHeader、SectionHeader、StatCard
    ↓
Phase 2: Dashboard、RiskChat、ContractCompare (代表页)
    ↓
Phase 3: DataIntegration、Analysis、ReportGenerator、ApprovalDashboard、FundFlow
    ↓
Phase 4: Checklist、PSAK、WarningConfig、AgentConfig、Analytics
    ↓
Phase 5: WarningDashboard、RiskTracking、PostLoanCheck
    ↓
Phase 6: 全仓清理和回归
```

---

## 创建时间
2026-05-02
