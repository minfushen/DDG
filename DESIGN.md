---
version: alpha
name: b2b-saas-design-system
description: A professional, high-density design system for B2B SaaS products — enterprise dashboards, data-heavy workbenches, forms, and analytical reports. Inspired by Airbnb's token discipline and component-state completeness, but tuned for trust, efficiency, and Chinese readability.
---

# B2B SaaS Design System

A design system for business-facing SaaS products where efficiency, clarity, and trust matter more than visual flourish. The visual language is intentionally restrained: a single brand blue, a small set of semantic accents, and a neutral surface palette. Components are defined by their purpose and state, not by decoration.

The default canvas is light (`{colors.canvas}`). Dark mode (`{colors.canvas-dark}`) is reserved for immersive dashboards, charts, and low-light environments. Both modes share the same spacing, typography, and component vocabulary; only surfaces, borders, and text colors invert.

**Key Characteristics:**
- **Restrained palette**: one brand blue + four semantic accents + four neutral surfaces. No decorative gradients.
- **State-complete components**: every interactive component defines default, hover, active, disabled, and focus states.
- **Data-first density**: compact table rows (44px), tight gutters, and high-contrast status tags.
- **Clear elevation model**: only two shadow tiers — rest state and elevated/floating state.
- **Rounded but professional**: 8px default radius for controls, 12px for cards, pills reserved for primary CTAs only.
- **Chinese-optimized typography**: Inter for numerals/Latin, system Chinese fonts for CJK, generous line-height for readability.

## Colors

### Brand
- **Primary** (`{colors.primary}` — `#2563eb`): Primary actions, active nav items, links, key metrics.
- **Primary Hover** (`{colors.primary-hover}` — `#1d4ed8`): Hovered primary buttons and links.
- **Primary Active** (`{colors.primary-active}` — `#1e40af`): Pressed primary buttons.
- **Primary Subtle** (`{colors.primary-subtle}` — `#eff6ff`): Light backgrounds for primary-tinted surfaces.

### Semantic
- **Success** (`{colors.success}` — `#16a34a`): Positive status, completed states, growth indicators.
- **Success Subtle** (`{colors.success-subtle}` — `#f0fdf4`): Success tag backgrounds.
- **Warning** (`{colors.warning}` — `#d97706`): Attention, pending states, medium risk.
- **Warning Subtle** (`{colors.warning-subtle}` — `#fffbeb`): Warning tag backgrounds.
- **Error** (`{colors.error}` — `#dc2626`): Errors, failures, high risk, destructive actions.
- **Error Subtle** (`{colors.error-subtle}` — `#fef2f2`): Error tag backgrounds.
- **Info** (`{colors.info}` — `#0891b2`): Neutral informational highlights.
- **Info Subtle** (`{colors.info-subtle}` — `#ecfeff`): Info tag backgrounds.

### Surfaces (Light)
- **Canvas** (`{colors.canvas}` — `#ffffff`): Primary application background.
- **Canvas Subtle** (`{colors.canvas-subtle}` — `#f8fafc`): Section backgrounds, alternate table rows.
- **Surface** (`{colors.surface}` — `#ffffff`): Cards, modals, dropdowns, input backgrounds.
- **Surface Hover** (`{colors.surface-hover}` — `#f1f5f9`): Hovered table rows, list items, buttons.
- **Surface Active** (`{colors.surface-active}` — `#e2e8f0`): Active/selected rows, pressed secondary buttons.
- **Hairline** (`{colors.hairline}` — `#e2e8f0`): Default borders, dividers, table grid lines.
- **Hairline Strong** (`{colors.hairline-strong}` — `#cbd5e1`): Input borders, focus rings, strong dividers.

### Surfaces (Dark)
- **Canvas Dark** (`{colors.canvas-dark}` — `#0f172a`): Primary dark background.
- **Canvas Dark Subtle** (`{colors.canvas-dark-subtle}` — `#1e293b`): Sidebars, elevated sections.
- **Surface Dark** (`{colors.surface-dark}` — `#1e293b`): Cards, modals, dropdowns on dark.
- **Surface Dark Hover** (`{colors.surface-dark-hover}` — `#334155`): Hovered rows on dark.
- **Surface Dark Active** (`{colors.surface-dark-active}` — `#475569`): Active rows on dark.
- **Hairline Dark** (`{colors.hairline-dark}` — `#334155`): Borders on dark surfaces.
- **Hairline Strong Dark** (`{colors.hairline-strong-dark}` — `#475569`): Strong borders on dark surfaces.

### Text
- **Ink** (`{colors.ink}` — `#0f172a`): Primary text on light canvas.
- **Ink Secondary** (`{colors.ink-secondary}` — `#475569`): Secondary text, descriptions, placeholders.
- **Ink Tertiary** (`{colors.ink-tertiary}` — `#94a3b8`): Disabled, meta, timestamps.
- **On Primary** (`{colors.on-primary}` — `#ffffff`): Text on primary buttons and primary backgrounds.
- **On Dark** (`{colors.on-dark}` — `#f8fafc`): Primary text on dark canvas.
- **On Dark Secondary** (`{colors.on-dark-secondary}` — `#cbd5e1`): Secondary text on dark canvas.
- **On Dark Tertiary** (`{colors.on-dark-tertiary}` — `#64748b`): Tertiary text on dark canvas.

## Typography

### Font Stack
- **Sans UI**: `"Inter", "SF Pro Display", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif`
- **Monospace / Data**: `"ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", monospace`

Chinese characters fall back to PingFang SC (macOS/iOS) and Microsoft YaHei (Windows). Inter handles Latin, numerals, and punctuation. The monospace stack is used for IDs, amounts, percentages, dates, and code snippets.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display-lg}` | 28px | 600 | 1.25 | -0.02em | Page title, dashboard header |
| `{typography.display-md}` | 24px | 600 | 1.3 | -0.01em | Section title, report heading |
| `{typography.display-sm}` | 20px | 600 | 1.35 | -0.01em | Card title, panel header |
| `{typography.heading-lg}` | 18px | 600 | 1.4 | 0 | Subsection title |
| `{typography.heading-md}` | 16px | 600 | 1.5 | 0 | Table section header |
| `{typography.heading-sm}` | 14px | 600 | 1.5 | 0 | Form group label, list header |
| `{typography.body-lg}` | 16px | 400 | 1.75 | 0 | Long-form reading body |
| `{typography.body-md}` | 14px | 400 | 1.6 | 0 | Default UI body, table text |
| `{typography.body-sm}` | 13px | 400 | 1.5 | 0 | Secondary body, metadata |
| `{typography.caption}` | 12px | 400 | 1.5 | 0.01em | Captions, badges, timestamps |
| `{typography.eyebrow}` | 11px | 600 | 1.2 | 0.04em | All-caps labels, status prefixes |
| `{typography.mono-md}` | 13px | 400 | 1.5 | 0 | Numbers, IDs, code snippets |
| `{typography.mono-sm}` | 12px | 400 | 1.5 | 0 | Small numeric data |

### Principles
- Display and heading weights stay at 600; never use hairline weights for Chinese text.
- Body line-height is 1.6–1.75 for Chinese readability.
- Tabular numbers (`font-variant-numeric: tabular-nums`) are enabled for `{typography.mono-md}` and `{typography.mono-sm}`.
- Headings use `-0.01em` to `-0.02em` letter-spacing for tighter, more authoritative lines.

## Layout

### Spacing System

Base unit: 4px.

| Token | Value |
|---|---|
| `{spacing.xxs}` | 2px |
| `{spacing.xs}` | 4px |
| `{spacing.sm}` | 8px |
| `{spacing.md}` | 12px |
| `{spacing.base}` | 16px |
| `{spacing.lg}` | 24px |
| `{spacing.xl}` | 32px |
| `{spacing.xxl}` | 48px |
| `{spacing.section}` | 64px |

### Grid & Container
- Application max-width: 1440px.
- Dashboard content area: fluid, with 24px outer padding on desktop.
- Forms: max-width 720px for single-column layouts.
- Tables: fluid width; horizontal scroll on overflow.
- Sidebar: 240px fixed width on desktop; collapses to icon-only 64px on tablet; hidden drawer on mobile.

### Density
- **Compact mode (default)**: table row height 44px, input height 36px, button height 32px.
- **Comfortable mode**: table row height 52px, input height 40px, button height 36px.
- Card padding: `{spacing.base}` (16px) default; `{spacing.lg}` (24px) for feature cards.

## Elevation

The system uses **only two shadow tiers** plus flat.

| Level | Shadow | Use |
|---|---|---|
| 0 | none | Default surface, cards at rest, body |
| 1 | `0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04)` | Elevated cards, dropdowns, popovers, hover lift |
| 2 | `0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.04)` | Modals, drawers, floating panels, toasts |

Depth on dark surfaces is communicated through surface color steps (`surface-dark` → `surface-dark-hover`) and hairlines, not through heavy shadows.

## Shapes

| Token | Value | Use |
|---|---|---|
| `{rounded.xs}` | 4px | Tags, small chips |
| `{rounded.sm}` | 6px | Input fields, small buttons, status tags |
| `{rounded.md}` | 8px | Buttons, cards, panels (default) |
| `{rounded.lg}` | 12px | Feature cards, modals, drawers |
| `{rounded.xl}` | 16px | Large promotional cards |
| `{rounded.pill}` | 9999px | Primary CTAs only |
| `{rounded.full}` | 50% | Avatars, status dots |

## Components

### Buttons

**`button-primary`** — the dominant CTA.
- Default: background `{colors.primary}`, text `{colors.on-primary}`, `{typography.body-md}` weight 500, height 32px, padding 0 16px, radius `{rounded.pill}`.
- Hover: background `{colors.primary-hover}`.
- Active: background `{colors.primary-active}`, scale 0.98.
- Disabled: opacity 0.5, cursor not-allowed.
- Focus: ring 2px `{colors.primary-subtle}`, outline-offset 2px.

**`button-secondary`** — cancel / alternative actions.
- Default: background `{colors.canvas}`, text `{colors.ink}`, border 1px `{colors.hairline-strong}`, height 32px, padding 0 16px, radius `{rounded.md}`.
- Hover: background `{colors.surface-hover}`.
- Active: background `{colors.surface-active}`.
- Disabled: opacity 0.5.
- Focus: ring 2px `{colors.primary-subtle}`.

**`button-ghost`** — low-emphasis actions.
- Default: transparent background, text `{colors.ink-secondary}`, height 32px, padding 0 12px, radius `{rounded.md}`.
- Hover: background `{colors.surface-hover}`.
- Active: background `{colors.surface-active}`.
- Disabled: opacity 0.5.

**`button-danger`** — destructive actions.
- Default: background `{colors.error}`, text `{colors.on-primary}`, height 32px, padding 0 16px, radius `{rounded.md}`.
- Hover: background `#b91c1c`.
- Active: scale 0.98.
- Disabled: opacity 0.5.

### Inputs

**`text-input`**
- Default: background `{colors.surface}`, text `{colors.ink}`, border 1px `{colors.hairline-strong}`, radius `{rounded.sm}`, height 36px, padding 0 12px, placeholder `{colors.ink-tertiary}`.
- Hover: border `{colors.hairline-strong}` (unchanged), background `{colors.canvas-subtle}`.
- Focus: border `{colors.primary}`, ring 2px `{colors.primary-subtle}`.
- Disabled: background `{colors.canvas-subtle}`, text `{colors.ink-tertiary}`, border `{colors.hairline}`.
- Error: border `{colors.error}`, optional error text `{colors.error}` below.

**`textarea`** — same as text-input but min-height 80px, padding 12px.

**`select`** — same geometry as text-input, with a chevron icon on the right.

### Tables

**`data-table`**
- Header: background `{colors.canvas-subtle}`, text `{typography.heading-sm}`, border-bottom 1px `{colors.hairline}`.
- Row: height 44px, padding 0 16px, default background `{colors.canvas}`.
- Hover row: `{colors.surface-hover}`.
- Selected row: `{colors.surface-active}`.
- Zebra rows: alternate `{colors.canvas-subtle}`.
- Cell text: `{typography.body-md}`.
- Sortable header: hover text `{colors.primary}`, active sort icon `{colors.primary}`.
- Sticky first column on horizontal scroll.

**`table-status-tag`**
- Small tag, radius `{rounded.xs}`, `{typography.caption}`.
- Success: `{colors.success-subtle}` bg + `{colors.success}` text.
- Warning: `{colors.warning-subtle}` bg + `{colors.warning}` text.
- Error: `{colors.error-subtle}` bg + `{colors.error}` text.
- Info: `{colors.info-subtle}` bg + `{colors.info}` text.
- Default: `{colors.canvas-subtle}` bg + `{colors.ink-secondary}` text.

### Cards

**`card-default`**
- Default: background `{colors.surface}`, border 1px `{colors.hairline}`, radius `{rounded.md}`, padding `{spacing.base}`, shadow none.
- Hover: shadow `{elevation.1}`.
- Header: `{typography.display-sm}`, margin-bottom `{spacing.md}`.

**`card-featured`**
- Default: background `{colors.primary-subtle}`, border 1px `{colors.hairline}`, radius `{rounded.lg}`, padding `{spacing.lg}`.
- Use for highlighted metrics or primary callouts.

### Tags & Badges

**`tag-default`**
- Default: background `{colors.canvas-subtle}`, text `{colors.ink-secondary}`, radius `{rounded.xs}`, padding 2px 8px, `{typography.caption}`.

**`tag-status`** — see `table-status-tag`.

### Navigation

**`sidebar-nav`**
- Default: width 240px, background `{colors.canvas-subtle}` (light) or `{colors.canvas-dark-subtle}` (dark).
- Nav item: height 40px, padding 0 16px, radius `{rounded.sm}`, text `{colors.ink-secondary}`.
- Hover: background `{colors.surface-hover}`.
- Active: background `{colors.primary-subtle}`, text `{colors.primary}`, font-weight 500.
- Disabled: opacity 0.5.

**`top-nav`**
- Default: height 56px, background `{colors.canvas}`, border-bottom 1px `{colors.hairline}`.
- Left: product logo + name; right: global search, notifications, user avatar.

### Modals & Drawers

**`modal`**
- Default: max-width 560px (small), 720px (medium), 960px (large); background `{colors.surface}`, radius `{rounded.lg}`, shadow `{elevation.2}`.
- Header: `{typography.display-sm}`, border-bottom 1px `{colors.hairline}`.
- Footer: right-aligned actions, border-top 1px `{colors.hairline}`.
- Backdrop: `rgba(15, 23, 42, 0.5)`.

**`drawer`**
- Default: width 400px (default), 640px (wide); slides from right; same surface and shadow as modal.

### Alerts & Toasts

**`alert-inline`**
- Default: padding 12px 16px, radius `{rounded.md}`, left accent border 4px.
- Success/Warning/Error/Info variants use semantic subtle backgrounds.

**`toast`**
- Default: fixed bottom-right, max-width 360px, background `{colors.surface}`, shadow `{elevation.2}`, radius `{rounded.md}`, padding `{spacing.md}`.

## Do's and Don'ts

### Do
- Use `{colors.primary}` sparingly for the most important action on a page.
- Keep table row height consistent across all tables.
- Use `{typography.mono-md}` for IDs, amounts, percentages, and dates.
- Provide empty states with clear next actions.
- Use skeleton loaders for initial data loads; use spinners for inline actions.
- Maintain 8px alignment for all spacing.
- Define hover, active, disabled, and focus for every interactive component.
- Use pills only for primary CTAs.

### Don't
- Don't use more than one primary button per section.
- Don't use `{rounded.pill}` for secondary or destructive actions.
- Don't place body text on saturated color backgrounds.
- Don't use pure black (`#000000`) for text or backgrounds.
- Don't make modals wider than 960px.
- Don't use decorative gradients for B2B data surfaces.
- Don't create more than two shadow tiers.
- Don't omit disabled / loading / empty states.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| Wide | ≥ 1440px | Full sidebar, multi-column dashboards, tables show all columns |
| Desktop | 1024–1439px | Sidebar expanded, tables may hide secondary columns |
| Tablet | 768–1023px | Sidebar collapses to icon-only, tables horizontal scroll |
| Mobile | < 768px | Sidebar hidden behind hamburger, cards stack vertically, tables cardified |

### Touch Targets
- Minimum 44×44px for all interactive elements.
- Table row tap targets stay 44px high.
- Primary buttons are at least 48px wide.

### Collapsing Strategy
- Sidebar: 240px → 64px icon-only → hidden drawer.
- Tables: hide least important columns; remaining columns horizontal scroll.
- Filters: collapse into a "Filters" button on tablet/mobile.
- Metrics: 4-up → 2-up → 1-up.

## Agent Prompt Guide

Use these prompts when asking an AI to generate UI with this system:

- "Create a dashboard page with a data table, filter bar, and primary CTA using the B2B SaaS design system."
- "Generate a form panel with sections, inputs, and a footer action bar. Use `{colors.primary}` for the submit button."
- "Build a risk summary card with `{colors.error}`, `{colors.warning}`, and `{colors.success}` status tags."
- "Convert this table into a mobile-friendly card list below 768px."
- "Apply dark mode to this dashboard while preserving semantic color meaning."
- "Add hover, active, disabled, and focus states to this button component."

## Iteration Guide

1. Focus on ONE component or ONE page at a time.
2. Reference tokens directly (`{colors.primary}`, `{typography.body-md}`, `{spacing.md}`).
3. Validate color contrast before introducing new semantic colors.
4. When adding a new component, define its light and dark variants and all states.
5. Keep the two canvas modes separated; never mix light cards on dark canvas or vice versa without explicit intent.
6. Run `npx @google/design.md lint DESIGN.md` after edits.

## Known Gaps

- **Loading states**: skeleton and spinner specifications exist but no token-level animation timing is defined.
- **Charts & data visualization**: color tokens for lines, bars, and legends are not yet specified; use semantic colors as a temporary palette.
- **Onboarding / empty states**: copy and illustration guidelines are not included.
- **Right-to-left (RTL)**: layout rules assume LTR; RTL adaptations are not covered.
- **High-contrast / accessibility modes**: no forced-color or Windows high-contrast overrides are defined.
- **Print styles**: no print-optimized styles are included.
- **Icon system**: icon sizing, stroke weight, and naming conventions are not covered; assume a 16px / 20px / 24px scale with 1.5px stroke.
- **Form validation**: error message anatomy and helper-text placement are described but not fully tokenized.
