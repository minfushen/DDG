# UI 设计规范文档 v3.0

> 金融工作台统一设计语言 — 统一视觉、统一骨架、统一交互

---

## 一、设计原则

### 1.1 核心原则

- **一致性优先**：相同功能使用相同组件，避免重复造轮子
- **克制使用色彩**：主色调（品牌蓝）+ 语义色（成功/警告/危险/信息）
- **边框分层为主**：阴影为辅，减少视觉噪音
- **响应式优先**：所有布局必须支持移动端到桌面端

### 1.2 设计 Token 来源

所有颜色、渐变、状态映射统一从 `src/theme/tokens.ts` 引用，禁止硬编码颜色值。

### 1.3 禁止事项

❌ 以下内容禁止使用：

- `purple/pink/cyan` 作为业务页主视觉
- 固定 `h-[600px]` 主内容高度
- 页面级重复大 Hero
- 无断点的 `grid-cols-3/4`
- 页面自带 `min-h-screen bg-surface-page p-8`

---

## 二、色彩规范

### 2.1 品牌主色（唯一主操作色）

```
品牌蓝：#1E40AF
品牌蓝浅：#3B82F6
品牌蓝背景：#DBEAFE
```

**使用场景**：主按钮、激活状态、重要图标、链接、主操作

### 2.2 语义色（仅用于状态）

| 语义 | 颜色 | CSS变量 | 使用场景 |
|------|------|---------|----------|
| 成功/低风险 | 深绿 #059669 | `--success` | 成功状态、低风险标签 |
| 警告/中风险 | 琥珀 #D97706 | `--warning` | 警告状态、中风险标签 |
| 危险/高风险 | 红 #DC2626 | `--danger` | 错误状态、高风险标签 |
| 信息/进行中 | 品牌蓝 #1E40AF | `--info` | 信息提示、进行中状态 |

### 2.3 渐变映射

```typescript
// 从 tokens.ts 引用
gradients.primary   // 品牌蓝（主按钮、主图标）
gradients.green     // 成功系 — 仅用于成功状态
gradients.amber     // 警告系 — 仅用于警告状态
gradients.red       // 危险系 — 仅用于危险状态
```

---

## 三、页面骨架规范

### 3.1 页面结构三层

```
┌─────────────────────────────────────────┐
│              PageHeader                 │  ← 页面级标题、操作、KPI
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐    │
│  │        SectionHeader            │    │  ← 区块标题
│  ├─────────────────────────────────┤    │
│  │        Content                  │    │  ← 内容区
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │        SectionHeader            │    │
│  ├─────────────────────────────────┤    │
│  │        Content                  │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### 3.2 PageHeader 组件

**两种变体**：

1. **standard（标准页头）**：标题 + 副标题 + 操作按钮
2. **risk（风险页头）**：仅用于预警/异常页面，允许更强提示色

```tsx
interface PageHeaderProps {
  title: string;
  subtitle?: string;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  kpis?: KpiItem[];
  variant?: 'standard' | 'risk';
}

// 使用示例
<PageHeader
  title="工作台"
  subtitle="今日有 3 项待处理任务"
  actions={<Button>发起尽调</Button>}
  kpis={[{ label: '待处理', value: 12 }]}
/>
```

### 3.3 SectionHeader 组件

```tsx
interface SectionHeaderProps {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  variant?: 'default' | 'risk' | 'success';
}

// 使用示例
<SectionHeader
  icon={FileText}
  title="任务列表"
  actions={<Button size="sm">筛选</Button>}
/>
```

### 3.4 KpiStrip 组件

**限制**：首屏 KPI 不超过 3 个，超过则折叠到次级区域。

```tsx
interface KpiItem {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'flat';
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

// 使用示例
<KpiStrip items={[
  { label: '待处理', value: 12 },
  { label: '进行中', value: 5, variant: 'warning' },
  { label: '已完成', value: 48, variant: 'success' },
]} />
```

### 3.5 SplitPane 组件

**布局模式**：

| 模式 | 比例 | 使用场景 |
|------|------|----------|
| main-sidebar | 2/3 + 1/3 | 数据整合、分析、报告 |
| equal | 1/2 + 1/2 | 对比、双栏表单 |
| compare | 30/40/30 | 合同对比 |

**响应式规则**：
- 桌面（≥1024px）：分栏显示
- 平板（768-1023px）：双栏或上下
- 移动端（<768px）：单列上下

---

## 四、Hero 使用边界

### 4.1 轻量页头（默认）

**适用**：所有普通业务页面

```tsx
<PageHeader
  title="页面标题"
  subtitle="副标题"
  actions={<Button>主操作</Button>}
/>
```

**禁止**：
- 大面积蓝色渐变背景
- 装饰性图标和插图
- 超过 2 个主操作按钮

### 4.2 风险页头（特殊）

**适用**：仅限预警、异常、审查告警类页面

```tsx
<PageHeader
  variant="risk"
  title="风险预警"
  subtitle="当前有 3 条高风险预警需处理"
  actions={<Button>立即处理</Button>}
/>
```

**允许**：
- 黄色/红色背景提示风险
- 更强的视觉警示

---

## 五、圆角规范

| 组件类型 | 圆角 | Tailwind类 |
|----------|------|------------|
| 卡片/面板 | 16px | `rounded-2xl` |
| 按钮 | 10px | `rounded-lg` |
| 标签/徽章 | 10px | `rounded-lg` |
| 输入框 | 10px | `rounded-lg` |
| 小标签 | 8px | `rounded-md` |

---

## 六、阴影规范

### 6.1 阴影层级

| 层级 | 使用场景 |
|------|----------|
| 无阴影 | 默认卡片，以边框分层 |
| `shadow-sm` | 悬浮卡片 |
| `shadow-md` | 弹窗、下拉菜单 |

### 6.2 阴影颜色

统一使用 `shadow-gray-200/50` 或品牌色阴影 `shadow-blue-500/20`。

---

## 七、响应式规范

### 7.1 断点定义

| 断点 | 宽度 | 布局 |
|------|------|------|
| mobile | <768px | 单列 |
| tablet | 768-1023px | 双列 |
| desktop | ≥1024px | 2/3 + 1/3 或自适应 |

### 7.2 栅格布局

```tsx
// ❌ 错误：无断点固定列数
<div className="grid grid-cols-4 gap-6">

// ✅ 正确：响应式栅格
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
```

### 7.3 固定高度

```tsx
// ❌ 错误：固定高度
<div className="h-[600px]">

// ✅ 正确：视口内弹性
<div className="min-h-0 flex-1 overflow-auto">
```

---

## 八、页面模板

### 8.1 工具型页面

**特点**：表格、分组、步骤流优先

```
┌─────────────────────────────────────────┐
│              PageHeader                 │
├─────────────────────────────────────────┤
│  筛选条  │  状态 Tabs  │  排序          │
├─────────────────────────────────────────┤
│                                         │
│              表格/列表                  │
│                                         │
└─────────────────────────────────────────┘
```

### 8.2 分析型页面

**特点**：结论、证据、动作优先

```
┌─────────────────────────────────────────┐
│              PageHeader + KPI           │
├─────────────────────────────────────────┤
│  ┌───────────────────┬───────────────┐  │
│  │     主内容区       │    侧栏区     │  │
│  │   (图谱/图表)      │  (详情/操作)  │  │
│  │      2/3          │      1/3      │  │
│  └───────────────────┴───────────────┘  │
└─────────────────────────────────────────┘
```

### 8.3 配置型页面

**特点**：列表、筛选、状态优先

```
┌─────────────────────────────────────────┐
│              PageHeader                 │
├─────────────────────────────────────────┤
│  顶部总览/统计                          │
├─────────────────────────────────────────┤
│  筛选条                                 │
├─────────────────────────────────────────┤
│  规则列表（表格化）                     │
└─────────────────────────────────────────┘
```

---

## 九、交互状态规范

### 9.1 必须补齐的状态

| 状态 | 说明 |
|------|------|
| loading | 加载中，显示骨架屏或 spinner |
| empty | 空状态，显示引导文案和插图 |
| error | 错误状态，显示错误信息和重试按钮 |
| disabled | 禁用状态，降低透明度，禁用交互 |
| hover | 悬浮状态，显示边框或背景变化 |
| focus | 聚焦状态，显示焦点环 |

### 9.2 假功能处理

**原则**：不做真实功能的入口不能伪装成可用功能。

```tsx
// ❌ 错误：假功能伪装成可用
<Button>深色模式</Button>  // 实际未实现

// ✅ 正确：降级展示
<Button disabled title="功能开发中">
  深色模式
  <Badge variant="info">即将推出</Badge>
</Button>

// ✅ 正确：移除假功能
// 直接不显示未实现的功能入口
```

---

## 十、组件使用规范

### 10.1 必须复用的组件

| 组件 | 用途 | 文件 |
|------|------|------|
| PageHeader | 页面标题 | `src/components/ui/PageHeader.tsx` |
| SectionHeader | 区块标题 | `src/components/ui/SectionHeader.tsx` |
| StatCard | KPI 卡片 | `src/components/ui/StatCard.tsx` |
| StatusBadge | 状态徽章 | `src/components/ui/StatusBadge.tsx` |
| Card | 卡片容器 | `src/components/ui/Card.tsx` |

### 10.2 禁止重复定义

❌ 页面内自定义：
- 页面标题样式
- KPI 卡片样式
- 状态徽章样式
- 图标容器样式

✅ 必须使用统一组件。

---

## 十一、验收清单

### 视觉一致性

- [ ] 所有页面使用品牌蓝作为主操作色
- [ ] 无 `purple/pink/cyan` 业务装饰色
- [ ] 卡片圆角统一 `rounded-2xl`
- [ ] 按钮圆角统一 `rounded-lg`

### 布局一致性

- [ ] 页面使用 PageHeader 组件
- [ ] 区块使用 SectionHeader 组件
- [ ] KPI 使用 StatCard 组件
- [ ] 分栏使用 SplitPane 或工具类

### 响应式

- [ ] 所有栅格有断点
- [ ] 无固定 `h-[600px]`
- [ ] 移动端可正常使用

### 交互状态

- [ ] 关键页面有 loading 状态
- [ ] 列表页有 empty 状态
- [ ] 表单有 error 状态
- [ ] 按钮有 disabled 状态
