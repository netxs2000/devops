# 前端开发规范 (Native CSS & JavaScript) - Apple Style Edition

## 一、 核心理念
1. **去框架化工程化**：虽然不使用 React/Vue，但必须通过模块化、服务层分层等手段达到同等的代码复用与维护能力。
2. **Apple Style Premium UI**：视觉效果必须对齐苹果公司（Apple Inc.）设计语言。优先采用浅色系、高通透感、大幅留白的视觉体验。
3. **逻辑与样式解耦**：CSS 只负责视觉，JS 只负责逻辑，两者通过 `js-` 类名和 `dataset` 桥接，严禁混用。
4. **设计令牌驱动**：所有审美标准必须通过 Design Tokens 实现，禁止硬编码视觉参数。

---

## 二、 苹果设计专项规范 (Apple-style HIG for Web)

### 1. 材质与通透感 (Material & Transparency)
*   **玻璃拟态 (Glassmorphism)**：核心卡片和导航组件优先使用玻璃质感。
    *   **规范**：使用 `backdrop-filter: blur(20px) saturate(180%);`。
    *   **背景**：使用半透明白色 `rgba(255, 255, 255, 0.72)`。
*   **连续圆角 (Continuous Curves)**：
    *   **小组件/按钮**：`8px` - `12px`。
    *   **内容卡片**：`16px` - `24px`。
    *   **模态框/认证卡**：`24px` 以上。

### 2. 精准色阶 (Neutral Grayscale)
*   **背景色 (Base)**：使用 `#F5F5F7` (Apple Gray) 作为全局背景，而非纯白。
*   **文字色级**：
    *   **Primary**: `#1D1D1F` (接近黑色的深灰，用于标题)。
    *   **Secondary**: `#86868B` (灰色，用于辅助文字)。
*   **行动项**: 使用 `#0071E3` (Apple Blue) 作为主动作色。

### 3. 空间空间与呼吸感 (Space & Air)
*   **8px 栅格**：所有 Padding 和 Margin 必须是 8 的倍数 (8, 16, 24, 32, 48, 64)。
*   **底部安全区 (Breathing Bottom)**：所有独立内容页面底部必须强制增加 `120px` 的透明占位，确保滚动体验的从容感。
*   **视口缓冲区**：页面顶部内容距离 Header 必须保持至少 `40px` - `60px` 的视觉缓冲区。

---

## 三、 样式规范 (CSS & Visuals)

### 1. 样式管理
*   **严禁内联**：禁止在 HTML 标签中编写超过 2 项属性的内联样式。
*   **样式回收**：凡在 3 处以上重复使用的布局，必须在 `css/main.css` 中提取为 `.u-` 原子类或 `.g-` 全局类。

### 2. Prefix-BEM 命名体系
所有类名遵循：`.前缀-组件名__子元素--修饰符`。
*   **业务域前缀 (Business Prefixes)**：
    *   `sd-` (Service Desk), `adm-` (Administration), `pm-` (Project Management), `qa-` (Quality Assurance), `rpt-` (Report), `sys-` (System)。
*   **功能性前缀 (Functional Prefixes)**：
    *   `u-` (Utility): 原子类，如 `.u-mt-20`。
    *   `g-` (Global): 全局组件/材质，如 `.g-glass-panel`。
    *   `is-/has-` (State): 描述状态，如 `.is-active`, `.is-loading`。

### 3. 排版与动效
*   **字体栈**：优先系统默认字体 `-apple-system, BlinkMacSystemFont`，其次使用 `Inter` 或 `Outfit`。
*   **阴影层级 (Levelized Shadows)**：
    *   **Soft**: `0 4px 6px -1px rgba(0,0,0,0.01)` (基础边界)。
    *   **Deep**: `0 20px 40px rgba(0,0,0,0.04)` (悬浮或弹出层)。
*   **滚动条**：禁止使用系统默认宽度。必须同步 `main.css` 中的极细圆角 Apple 风格滚动条。
*   **动效**：统一使用 `cubic-bezier(0.4, 0, 0.2, 1)` 或弹性 `cubic-bezier(0.175, 0.885, 0.32, 1.275)`。

---

## 四、 脚本规范 (JavaScript)

### 1. 模块架构 (Service-UI Pattern)
*   **ES6 Modules**: 强制使用 `type="module"`。
*   **分层设计**: `*_service.js` (Fetch 数据) <-> `*_handler.js` (DOM/UI 交互)。

### 2. DOM 操作规范
*   **逻辑钩子 (Logic Hooks)**: 使用以 `js-` 开头的类名作为 JS 选择器。
*   **状态驱动**: 通过操作 `dataset` 或 `classList` 来切换 UI，禁止修改 `.style.xxx`。
*   **事件委派**: 动态生成的元素必须在父容器上联合 `e.target.closest()` 监听。

### 3. 安全与性能
*   **XSS 防御**: 渲染动态内容严禁 `innerHTML`，强制使用 `textContent` 或 `<template>`。
*   **异步体感**: 必须提供骨架屏或 `is-loading` 状态。

---

## 五、 全链路命名对齐要求

| 维度 | 规范格式 | 示例 |
| :--- | :--- | :--- |
| **JS 脚本文件名** | `{prefix}_{resource}.js` | `sd_ticket_service.js` |
| **API 路径** | `/api/{prefix}/{resource}` | `/api/sd/tickets` |
| **CSS 类名** | `.prefix-component__element` | `.sd-table__cell` |
| **DOM 逻辑钩子** | `.js-{action}-{resource}` | `.js-delete-ticket` |
| **数据属性** | `data-{key}="{value}"` | `data-ticket-id="123"` |
