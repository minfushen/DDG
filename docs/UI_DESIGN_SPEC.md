# UI 设计规范文档

> 以工作台首页（Dashboard）为基准，统一全站设计语言

---

## 一、设计原则

### 1.1 核心原则

- **一致性优先**：相同功能使用相同组件，避免重复造轮子
- **克制使用色彩**：主色调（品牌蓝）+ 3个语义色（成功/警告/危险）
- **圆角统一**：全局使用 `rounded-2xl`（16px）作为主圆角
- **阴影分层**：`shadow-md` → `shadow-lg` → `shadow-xl` 三级阴影

### 1.2 设计 Token 来源

所有颜色、渐变、状态映射统一从 `src/theme/tokens.ts` 引用，禁止硬编码颜色值。

---

## 二、色彩规范

### 2.1 品牌主色

```
品牌蓝：#3B82F6 (blue-500)
品牌蓝渐变：from-blue-500 to-indigo-500
```

**使用场景**：主按钮、激活状态、重要图标、链接

### 2.2 语义色（全局唯一）

| 语义 | 颜色 | CSS变量 | 使用场景 |
|------|------|---------|----------|
| 成功/低风险 | 深绿 #3B6D11 | `--risk-low` | 成功状态、低风险标签 |
| 警告/中风险 | 琥珀 #BA7517 | `--risk-medium` | 警告状态、中风险标签 |
| 危险/高风险 | 橙红 #D85A30 | `--risk-high` | 错误状态、高风险标签 |
| 信息/进行中 | 品牌蓝 #3B82F6 | `--risk-info` | 信息提示、进行中状态 |

### 2.3 渐变映射

```typescript
// 从 tokens.ts 引用
gradients.primary   // 品牌蓝（主按钮、主图标）
gradients.green     // 成功系
gradients.amber     // 警告系
gradients.red       // 危险系
```

### 2.4 禁止使用的颜色

❌ 以下颜色造成视觉混乱，禁止使用：
- `purple-500`、`pink-500`（非语义色）
- `cyan-500`、`teal-500`（非语义色）
- `rose-500`（与危险色冲突）

---

## 三、圆角规范

### 3.1 统一圆角体系

| 组件类型 | 圆角 | Tailwind类 |
|----------|------|------------|
| 卡片/面板 | 16px | `rounded-2xl` |
| 按钮 | 10px | `rounded-lg` |
| 标签/徽章 | 8px | `rounded-lg` |
| 输入框 | 10px | `rounded-lg` |
| 小标签 | 6px | `rounded-md` |
| 进度条 | 全圆 | `rounded-full` |

### 3.2 禁止混用

❌ 错误示例：
```jsx
// 不同页面使用不同圆角
<div className="rounded-xl">  // 12px
<div className="rounded-3xl"> // 24px
```

✅ 正确示例：
```jsx
// 统一使用 rounded-2xl
<div className="rounded-2xl shadow-lg shadow-gray-200/50">
```

---

## 四、阴影规范

### 4.1 阴影层级

| 层级 | Tailwind类 | 使用场景 |
|------|------------|----------|
| 轻阴影 | `shadow-md shadow-gray-200/50` | 小卡片、指标卡片 |
| 标准阴影 | `shadow-lg shadow-gray-200/50` | 主卡片、面板 |
| 重阴影 | `shadow-xl shadow-gray-200/50` | 弹窗、下拉菜单 |
| 悬浮阴影 | `shadow-lg shadow-blue-500/20` | 主按钮悬浮 |

### 4.2 阴影颜色

统一使用 `shadow-gray-200/50`（50%透明度），保持视觉轻盈。

---

## 五、组件规范

### 5.1 卡片组件

**标准卡片**：
```jsx
<div className="rounded-2xl bg-white shadow-lg shadow-gray-200/50 p-6">
  {/* 内容 */}
</div>
```

**可悬浮卡片**：
```jsx
<div className="rounded-2xl bg-white shadow-md shadow-gray-200/50
  hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
```

### 5.2 按钮规范

| 类型 | 样式 | 使用场景 |
|------|------|----------|
| 主按钮 | `bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-lg shadow-md shadow-blue-500/20` | 主要操作 |
| 次按钮 | `bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50` | 次要操作 |
| 幽灵按钮 | `bg-transparent text-gray-600 rounded-lg hover:bg-gray-100` | 辅助操作 |

**按钮尺寸**：
```jsx
// 标准按钮
<button className="px-4 py-2 rounded-lg text-sm font-medium">

// 大按钮
<button className="px-6 py-3 rounded-lg text-base font-medium">

// 小按钮
<button className="px-3 py-1.5 rounded-lg text-xs font-medium">
```

### 5.3 标签/徽章规范

**统一使用圆角矩形**（非胶囊）：

```jsx
// 标准标签
<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700">

// 带图标标签
<span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium">
  <Icon className="w-3 h-3" />
  文字
</span>
```

**语义色标签**：
```jsx
// 成功/低风险
className="bg-[var(--risk-low-bg)] text-[var(--risk-low-text)]"

// 警告/中风险
className="bg-[var(--risk-medium-bg)] text-[var(--risk-medium-text)]"

// 危险/高风险
className="bg-[var(--risk-high-bg)] text-[var(--risk-high-text)]"

// 信息/进行中
className="bg-[var(--risk-info-bg)] text-[var(--risk-info-text)]"
```

### 5.4 图标规范

**图标容器尺寸**：
```jsx
// 小图标容器
<div className="w-8 h-8 rounded-lg flex items-center justify-center">

// 中图标容器
<div className="w-10 h-10 rounded-xl flex items-center justify-center">

// 大图标容器
<div className="w-14 h-14 rounded-2xl flex items-center justify-center">
```

**图标尺寸**：
```jsx
<Icon className="w-4 h-4" />  // 小图标（12px容器内）
<Icon className="w-5 h-5" />  // 中图标（16px容器内）
<Icon className="w-6 h-6" />  // 大图标（20px容器内）
```

### 5.5 区块标题规范

**统一使用 SectionHeader 组件**：
```jsx
<SectionHeader
  icon={IconComponent}
  title="标题"
  subtitle="副标题"
/>
```

**禁止自定义标题样式**：
❌ 错误：
```jsx
<div className="flex items-center gap-3 mb-4">
  <GradientIcon ... />
  <h3 className="text-lg font-bold">标题</h3>
</div>
```

✅ 正确：
```jsx
<SectionHeader icon={Icon} title="标题" subtitle="副标题" />
```

---

## 六、布局规范

### 6.1 页面容器

```jsx
// 标准页面容器
<div className="mx-auto max-w-[1200px] space-y-6 animate-fade-in-up">
```

### 6.2 栅格布局

```jsx
// 三栏布局
<div className="grid grid-cols-3 gap-6">
  <div className="col-span-2">主内容</div>
  <div>侧边栏</div>
</div>

// 四栏布局
<div className="grid grid-cols-4 gap-6">
```

### 6.3 间距规范

| 场景 | 间距 | Tailwind类 |
|------|------|------------|
| 页面区块间 | 24px | `space-y-6` |
| 卡片内边距 | 24px | `p-6` |
| 元素间间距 | 16px | `gap-4` |
| 紧凑间距 | 12px | `gap-3` |

---

## 七、排版规范

### 7.1 字号体系

| 用途 | 字号 | Tailwind类 |
|------|------|------------|
| 页面大标题 | 20px | `text-xl font-bold` |
| 卡片标题 | 18px | `text-lg font-semibold` |
| 区块标题 | 16px | `text-base font-semibold` |
| 正文 | 14px | `text-sm` |
| 辅助文字 | 12px | `text-xs` |
| 小标签 | 11px | `text-[11px]` |

### 7.2 字重规范

| 用途 | 字重 | Tailwind类 |
|------|------|------------|
| 标题 | 600 | `font-semibold` |
| 强调 | 500 | `font-medium` |
| 正文 | 400 | `font-normal` |

### 7.3 行高规范

```jsx
// 标题
<h3 className="leading-tight">

// 正文
<p className="leading-relaxed">
```

---

## 八、动画规范

### 8.1 入场动画

统一使用 `animate-fade-in-up`：
```jsx
<div className="animate-fade-in-up">
```

### 8.2 交互过渡

```jsx
// 标准过渡
className="transition-all duration-200"

// 悬浮效果
className="hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
```

### 8.3 加载状态

```jsx
// 旋转加载
<Loader2 className="w-4 h-4 animate-spin" />

// 脉冲动画
<div className="animate-pulse" />
```

---

## 九、现有问题清单

### 9.1 色彩不一致

| 问题 | 位置 | 修复方案 |
|------|------|----------|
| 使用 `purple-500` | 多处图标渐变 | 改用 `primary` 或语义色 |
| 使用 `cyan-500` | 按钮渐变 | 改用 `from-blue-500 to-indigo-500` |
| 使用 `teal-500` | 部分标签 | 改用 `green` 语义色 |
| 硬编码颜色值 | 多处内联样式 | 使用 CSS 变量 |

### 9.2 圆角不一致

| 问题 | 位置 | 修复方案 |
|------|------|----------|
| `rounded-xl` (12px) | 部分卡片 | 统一为 `rounded-2xl` |
| `rounded-3xl` (24px) | 部分面板 | 统一为 `rounded-2xl` |
| 胶囊形状 `rounded-full` | 部分标签 | 改为 `rounded-lg` |

### 9.3 组件重复定义

| 问题 | 位置 | 修复方案 |
|------|------|----------|
| StatCard 重复定义 | WarningDashboard | 使用 `src/components/ui/StatCard.tsx` |
| 页面标题样式不统一 | 多个页面 | 使用 `SectionHeader` 或 `PageHeader` |
| 图标容器样式不统一 | 多处内联 | 使用 `GradientIcon` 组件 |

### 9.4 阴影不一致

| 问题 | 位置 | 修复方案 |
|------|------|----------|
| 缺少阴影透明度 | 部分卡片 | 添加 `shadow-gray-200/50` |
| 阴影层级混乱 | 多处 | 按规范使用 `shadow-md/lg/xl` |

---

## 十、修复优先级

### P0 - 必须修复

1. 统一色彩为品牌蓝 + 3语义色
2. 统一卡片圆角为 `rounded-2xl`
3. 删除重复的组件定义

### P1 - 建议修复

1. 统一阴影样式
2. 统一按钮样式
3. 统一标签样式

### P2 - 优化项

1. 动画效果统一
2. 间距微调
3. 字号规范化
