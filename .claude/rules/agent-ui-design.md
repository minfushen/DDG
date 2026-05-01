# Agent-UI 设计规范

> 本规范适用于智能体平台前端开发，确保 AI 生成的 UI 与设计系统一致。

## 一、色彩系统

### 品牌色

```
品牌蓝（主色）: from-blue-500 to-indigo-500
CSS 变量: --brand-blue: #3B82F6
```

### 语义色

| 语义 | 渐变类 | CSS 变量 | 用途 |
|------|--------|----------|------|
| 成功/低风险 | `from-emerald-500 to-teal-500` | `--risk-low: #3B6D11` | 完成状态、正常状态 |
| 警告/中风险 | `from-amber-500 to-orange-500` | `--risk-medium: #BA7517` | 待处理、需关注 |
| 危险/高风险 | `from-[#D85A30] to-[#E87040]` | `--risk-high: #D85A30` | 错误、紧急、拒绝 |
| 信息 | 品牌蓝 | `--risk-info: #3B82F6` | 进行中、提示 |

### 禁止事项

- ❌ 直接使用 `purple`、`indigo`、`slate`、`rose` 等未定义的渐变
- ❌ 内联硬编码颜色值（如 `#FF5733`）
- ❌ 使用非标准 CSS 变量

---

## 二、圆角规范

| 元素类型 | Tailwind 类 | 像素值 | 使用场景 |
|----------|-------------|--------|----------|
| 卡片容器 | `rounded-2xl` | 16px | Card 组件、页面区块 |
| 按钮 | `rounded-lg` | 10px | 操作按钮、标签 |
| 输入框 | `rounded-xl` | 12px | 文本框、选择器 |
| 小图标 | `rounded-lg` | 10px | 头像、图标容器 |
| 徽章 | `rounded-lg` | 10px | StatusBadge |

### 禁止事项

- ❌ 混用 `rounded-xl` 和 `rounded-2xl` 于同类元素
- ❌ 使用非标准圆角值（如 `rounded-3xl`）

---

## 三、阴影规范

### 标准阴影

```css
/* 卡片阴影 */
shadow-lg shadow-gray-200/50

/* 按钮阴影 */
shadow-md shadow-blue-500/20

/* 悬浮阴影 */
hover:shadow-lg
```

### 禁止事项

- ❌ 使用纯黑阴影（如 `shadow-black/20`）
- ❌ 过度使用阴影（每层不超过一个阴影）

---

## 四、组件使用规范

### 卡片组件

```tsx
// 标准用法
<Card>
  <SectionHeader icon={Icon} title="标题" subtitle="副标题" />
  {/* 内容 */}
</Card>

// 禁止
<div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 p-6">
  {/* 直接写样式，不复用组件 */}
</div>
```

### 图标组件

```tsx
// 标准用法
<GradientIcon icon={Icon} gradient="blue" size="md" />

// 禁止
<div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500">
  <Icon className="w-5 h-5 text-white" />
</div>
```

### 状态徽章

```tsx
// 标准用法
<StatusBadge status={status} config={taskStatusConfig} />

// 禁止
<span className="px-2 py-0.5 rounded-lg bg-blue-50 text-blue-600">
  {status}
</span>
```

### 主按钮

```tsx
// 标准用法
<button className="bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-lg shadow-md shadow-blue-500/20">
  操作
</button>

// 禁止
<button className="bg-blue-500 text-white rounded-lg">
  操作
</button>
```

### 次按钮

```tsx
// 标准用法
<button className="border border-gray-200 bg-white text-gray-600 rounded-lg hover:bg-gray-50">
  操作
</button>
```

---

## 五、A2UI 协议使用指南

### 组件类型映射

| A2UI 类型 | React 组件 | 说明 |
|-----------|------------|------|
| `Text` | `<p>` | 纯文本 |
| `Markdown` | 自定义渲染 | Markdown 内容 |
| `Button` | `<button>` | 操作按钮 |
| `Card` | `<Card>` | 卡片容器 |
| `StatusBadge` | `<StatusBadge>` | 状态徽章 |
| `FormField` | 表单字段 | 输入控件 |
| `Container` | 布局容器 | 网格布局 |

### 安全渲染原则

1. **AI 只产生意图**：AI 生成的 JSON 只包含组件类型和语义属性
2. **前端控制样式**：所有样式、颜色、圆角由前端组件库控制
3. **属性净化**：移除事件处理器、危险属性（onClick, href, style 等）
4. **类型校验**：验证 gradient、status 等值是否为合法枚举

### 示例

```typescript
// AI 生成的 JSON（安全）
{
  "type": "Card",
  "props": {
    "title": "风险分析",
    "subtitle": "AI 生成"
  },
  "children": [
    {
      "type": "StatusBadge",
      "props": {
        "status": "high",
        "configType": "risk"
      }
    }
  ]
}

// 前端渲染（控制样式）
renderA2UIComponent(schema) // → 使用 Card + StatusBadge 组件
```

---

## 六、AG-UI 协议使用指南

### 事件类型

| 事件类型 | 用途 | 载荷 |
|----------|------|------|
| `text_delta` | 文本增量更新 | `{ content, isComplete }` |
| `status_update` | 智能体状态更新 | `{ status, message, progress }` |
| `tool_call` | 工具调用开始 | `{ tool }` |
| `tool_result` | 工具调用结果 | `{ result }` |
| `ui_render` | UI 渲染指令 | `{ surfaceId, operation, component }` |
| `error` | 错误事件 | `{ code, message, recoverable }` |
| `done` | 会话结束 | `null` |

### 连接管理

```typescript
import { AGUIConnection } from '@/protocol/agui';

const connection = new AGUIConnection({
  sessionId: 'session-123',
  reconnectAttempts: 3,
});

connection.connect({
  onTextDelta: (content, isComplete) => { /* 更新 UI */ },
  onStatusUpdate: (status, message, progress) => { /* 更新状态 */ },
  onToolCall: (tool) => { /* 显示工具调用 */ },
  onToolResult: (result) => { /* 显示结果 */ },
  onUIRender: (payload) => { /* 渲染 A2UI 组件 */ },
  onError: (error) => { /* 处理错误 */ },
  onDone: () => { /* 清理连接 */ },
});
```

---

## 七、检查清单

### 代码审查时检查

- [ ] 所有渐变使用有效的 GradientKey
- [ ] 卡片使用 `rounded-2xl`
- [ ] 按钮使用 `rounded-lg`
- [ ] 阴影使用 `shadow-lg shadow-gray-200/50`
- [ ] 复用 Card、SectionHeader、GradientIcon 组件
- [ ] 状态使用 StatusBadge 组件
- [ ] 无内联硬编码颜色值

### AI 生成代码检查

- [ ] A2UI 组件类型有效
- [ ] 属性经过净化处理
- [ ] gradient 值为合法枚举
- [ ] status 值为合法枚举
- [ ] 无危险属性（onClick, href 等）
