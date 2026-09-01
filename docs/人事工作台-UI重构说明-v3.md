# 人事工作台 · UI 重构说明 v3（墨蓝 × 青碧）

> 配套设计文档：`docs/人事AI工作台-设计方案-v2.0-本机绿色版.md`
> 视觉验证截图：`docs/ui_shots/`（桌面 1366×800 + 移动 390×844）

---

## 1. 设计目标 & 取舍

| 目标 | 落地 |
|---|---|
| 适合年轻人 + HR 角色定位 | 深墨蓝（沉稳专业）+ 青碧 Teal（年轻、人本、HR 亲和）双色调，告别政务蓝/老气灰 |
| 配色高端、界面大气简洁 | 单品牌色（Teal #0E9384），其余全 slate 中性色，无渐变/玻璃拟态/大圆角等花哨元素 |
| 多端多浏览器兼容 | 全部用现代浏览器普遍支持的 CSS 特性（变量/flex/grid），不用 :has()、oklch、container queries |
| 去除 AI 味 | 不堆 emoji，不写「AI 智能助手」类话术；副标改 `HR Workbench` 收口；侧边栏底部强调「本机数据 · 离线可用」 |

---

## 2. 设计 Token（CSS 变量）

| 类别 | 变量 | 值 | 用途 |
|---|---|---|---|
| 品牌主 | `--brand-600` | `#0E9384` | 按钮、激活竖条、链接 |
| 品牌深 | `--brand-700` | `#0B7A6D` | 按钮 hover、focus |
| 品牌浅 | `--brand-50` | `#EDF7F5` | 角色徽标底、辅助底色 |
| 墨蓝 | `--navy-900/800/700` | `#0F172A / #16203A / #1E2A47` | 侧边栏深色渐变 |
| 中性 | `--ink-900/700/500/400/300` | slate 系 | 文字主/正文/次要/弱/边线 |
| 表面 | `--bg` / `--surface` | `#F5F6F8` / `#FFFFFF` | 内容区背景 / 卡片 |
| 边线 | `--line` / `--line-soft` | `#E6E8EC` / `#EEF0F4` | 卡片边框 / 表格分隔线 |
| 语义 | `--danger-*` / `--warning-*` / `--success-*` | 各 700/600/100/50 四档 | 徽章、提示条、状态色 |
| 圆角 | `--r-lg/md/sm` | 12/8/6 px | 卡片/控件/徽章 |
| 阴影 | `--shadow-card/pop/nav` | 细微→浮层 | 静态卡 / 浮层 / 侧栏 |

字体栈优先系统字体：`-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "HarmonyOS Sans SC", "Segoe UI", system-ui`，保证 Win/Mac/iOS/Android 浏览器/微信公众号内置浏览器都能拿到合适的字重与字距，不依赖 CDN 下载字体。

---

## 3. 布局框架

```
┌─ 深色侧边栏 236px (sticky) ─┬─ 顶部栏 (sticky) ──────────────────────┐
│  [品牌 mark] 人事工作台      │ [汉堡] 页面标题             [专员版][时间] │
│  HR Workbench                │ ───────────────────────────────────────  │
│  ─────────                   │                                          │
│  ▍分组（letter-spacing 2px）│   24/28px 内边距                          │
│   · 导航项 (16px SVG icon)   │   ── 卡片网格 (auto-fit 190px) ──         │
│  ─────────                   │   ── 面板 (圆角 12, 1px 边框) ──         │
│  · 本机数据 · 离线可用       │   ── 表格 (表头 12px 灰，行 hover) ──   │
└──────────────────────────────┴──────────────────────────────────────────┘
```

- **桌面（≥1024px）**：侧栏 236px 固定，sticky。
- **平板/窄屏（<1024px）**：侧栏变抽屉（transform + transition），汉堡按钮出现在顶部栏左侧。
- **手机（<768px）**：内容单列、汉堡按钮、统计卡 2 列、表格在面板内横向滑动；角色 chip 与时钟在小屏隐藏以省空间。

---

## 4. 组件规范

| 组件 | 规范要点 |
|---|---|
| **品牌 mark** | 34×34 圆角 10px 青碧渐变方块 + 内嵌「四宫格 + 对勾」线性 SVG，象征「人员档案 / 合同 / 入转调离 / 校验」闭环 |
| **导航项** | 9×10 padding，悬停半透白底，激活态 = 左 3px 竖条 + 渐变青碧底 + 白字 + 图标 100% 不透明 |
| **统计卡** | 白底 + 1px 边框 + 柔和阴影，hover 上移 1px + 加深阴影，数字用 tabular-nums 等宽 |
| **面板** | 圆角 12px + 1px 边框，标题前 3px 品牌色竖条；面板自带 `overflow-x: auto` 解决窄屏表格溢出 |
| **按钮** | 三档：默认 / primary（品牌色 + 1px 投影） / danger（红色淡底）；focus-visible 显示 2px 品牌色环（键盘可达性） |
| **徽章** | 圆角 999 + 浅色底 + 语义色文字 + 1px 同色描边，与卡片、表格、提示条统一 |
| **提示条** | `.warn-note`（黄色，左无描边，前缀 ※） / `.danger-note`（红色，左 3px 竖条） / `.alert.success`（绿色） |
| **Toast** | 深墨蓝胶囊 + 浮层阴影，1.6s 自动消失 |
| **图标** | 全部内联 SVG（Feather 风格 stroke=1.5~1.7），离线可用；统一 17×17、currentColor 继承 |

---

## 5. 多端多浏览器兼容性

### 5.1 浏览器与设备覆盖

| 平台 | 浏览器 | 状态 |
|---|---|---|
| Windows 10/11 | Chrome / Edge / Firefox / 360 / QQ | ✅ 完整 |
| macOS | Safari / Chrome | ✅ 完整（系统字体 PingFang SC 命中） |
| iPhone/iPad | Safari / 微信内置 | ✅ 完整（响应式 + 系统字体） |
| Android | Chrome / 微信内置 | ✅ 完整（响应式 + 系统字体） |

### 5.2 不使用的特性（避坑）

- ❌ `:has()`、`:focus-within` 子选择器（Safari < 15.4 不支持）
- ❌ `oklch()` 色彩（Safari < 15.4 不支持）
- ❌ `container queries`（桌面/移动兼容性差）
- ❌ CSS `@layer`（旧 Edge 不支持）
- ❌ `backdrop-filter` 毛玻璃（性能 + 兼容性双重风险）
- ❌ 任何 CDN 字体、CDN 图标库（断网失效）
- ❌ emoji 作 UI 图标（系统渲染不一致，去 AI 味）

### 5.3 资源离线

- 所有 JS/CSS 放 `web/static/` 本地 vendor
- 图标全部内联 SVG，零网络依赖
- 字体走系统字体栈，无需 Web Font 加载

### 5.4 响应式断点

```css
@media (max-width: 1024px) { /* 平板：侧栏变抽屉 */ }
@media (max-width:  768px) { /* 手机：内容单列、表格横滑 */ }
@media (max-width:  420px) { /* 小屏手机：统计卡单列 */ }
@media print              { /* 报表打印：隐藏侧栏与顶部 */ }
@media (forced-colors: active) { /* Windows 高对比度模式 */ }
```

### 5.5 可访问性

- 焦点环：`:focus-visible` 2px 品牌色外环（键盘可达性）
- 颜色对比：所有正文文字 ≥ AA（4.5:1）
- `aria-hidden="true"` 装饰性 SVG 图标
- 主题色：`<meta name="theme-color">` 配合移动浏览器顶栏

---

## 6. 文件改动清单

| 文件 | 改动 |
|---|---|
| `web/static/css/app.css` | **重写**：全新设计系统（墨蓝 × 青碧），保持 22 个页面所有类名兼容 |
| `web/templates/layout.html` | **重写**：深色侧边栏 + 分组导航 + 内联 SVG 图标 + 移动端抽屉 + 顶部栏角色/时钟 |
| `web/templates/login.html` | **重写**：深色渐变背景 + 居中卡片 + 品牌区 + 高端登录表单 |
| `web/static/js/app.js` | 新增 `toggleSidebar` / `closeSidebar` + 点击导航自动收起抽屉 |
| `web/templates/contract_import.html` | 旧 CSS 变量 `--border` → 新 `--line` |
| `web/templates/replies.html` | 旧 `--danger-soft/--danger` → 新 `--danger-50/--danger-700` |
| `docs/ui_shots/` | 新增视觉验证截图（桌面 5 张 + 移动 2 张） |
| `build/ui_shots.js` | 新增视觉回归脚本（playwright-core + 本机 Chrome） |

---

## 7. 视觉验证

```bash
# 在工程根目录执行（需已装 playwright-core + 本机 Chrome）
NODE_PATH="$HOME/.workbuddy/binaries/node/workspace/node_modules" \
"$HOME/.workbuddy/binaries/node/versions/22.22.2/node.exe" \
build/ui_shots.js
```

截图输出到 `docs/ui_shots/`，覆盖：dashboard、employees、contract、resume、login（桌面 1366×800）+ dashboard 收起/抽屉展开（移动 390×844）。

---

## 8. 后续可选增强（非本期范围）

- **暗色模式**：CSS 变量化已完成，复制一份 `:root.dark` token 即可切换
- **数据图表占位**：当前 ECharts 尚未接入，主题色 `--brand-600` 已在 CSS 留好
- **角色切换**：顶部「专员版」chip 可在 M7 经理驾驶舱上线时扩展为下拉切换「专员 / 经理」
- **无障碍审计**：可补 axe-core 自动扫描，对比度/键盘流程需通过 WCAG 2.1 AA
