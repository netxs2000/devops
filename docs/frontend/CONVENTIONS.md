# 前端开发规范 (Native CSS & JavaScript)

## 一、 核心理念
1. **去框架化工程化**：虽然不使用 React/Vue，但必须通过模块化、服务层分层等手段达到同等的代码复用与维护能力。
2. **Premium UI 优先**：视觉效果必须达到顶尖水准，通过 CSS 设计令牌（Tokens）和微动效建立品牌感。
3. **逻辑与样式解耦**：CSS 只负责视觉，JS 只负责逻辑，两者通过 `js-` 类名和 `dataset` 桥接，严禁混用。

---

## 二、 样式规范 (CSS & Visuals)

### 1. 样式管理
*   **严禁内联**：禁止在 HTML 标签中编写超过 2 项属性的内联样式。
*   **强制提炼**：凡在 3 处以上重复使用的布局或样式，必须在 `css/main.css` 中提取为通用工具类（Utility Cases）。
*   **组件化**：新增独立功能模块应先在单独的 HTML 文件中开发验证（Sandbox 模式），再按需加载。

### 2. Prefix-BEM 命名体系
所有类名遵循：`.前缀-组件名__子元素--修饰符`。
*   **业务域前缀 (Business Prefixes)**：
    *   `sd-` (Service Desk), `adm-` (Administration), `pm-` (Project Management), `qa-` (Quality Assurance), `rpt-` (Report), `sys-` (System)。
*   **功能性前缀 (Functional Prefixes)**：
    *   `u-` (Utility): 原子类，如 `.u-mt-20`。
    *   `g-` (Global): 全局组件，如 `.g-card-shadow`。
    *   `is-/has-` (State): 描述状态，如 `.is-active`, `.is-loading`。

### 3. 设计令牌 (Design Tokens) 系统
*   **严禁裸色**：禁止使用十六进制颜色或固定像素值。必须三层架构调用：
    *   **基础层 (Global)**: `--g-primary-500: #3b82f6;`
    *   **语义层 (Semantic)**: `--status-success: var(--g-green-500);`
    *   **组件层 (Component)**: `--sd-btn-bg: var(--status-success);`
*   **暗黑适配**：所有颜色变量必须考虑 `[data-theme="dark"]` 适配。

### 4. 视觉排版与质感
*   **阴影层级**：避免纯黑阴影，优先使用带色倾向的柔和投影或 `backdrop-filter` 玻璃滤镜。
*   **字号阶梯**：从 `Display (32px)` 到 `Tiny (11px)` 严格遵循 1.25x 比例，正文统一使用 `14px` 或 `15px`。
*   **微交互**：所有可点击元素必须具备 `transition: 0.2s cubic-bezier(...)` 过渡动画。

---

## 三、 脚本规范 (JavaScript)

### 1. 模块架构 (Service-UI Pattern)
*   **ES6 Modules**: 强制使用 `type="module"`，逻辑通过 `import/export` 拆分。
*   **API 服务层 (Service Layer)**: 对应业务编写 `*_service.js`（如 `sd_ticket_service.js`），封装所有 `fetch` 请求。
*   **UI 处理器 (Handler Layer)**: 编写 `*_handler.js`，负责监听 DOM 事件并调用 Service 层，严禁在 Handler 中手写 `fetch` 细节。

### 2. DOM 操作规范
*   **逻辑钩子 (Logic Hooks)**: 使用以 `js-` 开头的类名作为 JS 选择器。
    *   *Bad*: `document.querySelector('.sd-btn')`
    *   *Good*: `document.querySelector('.js-ticket-submit')`
*   **状态驱动**: 通过操作 `dataset` 或 `classList` 来切换 UI，禁止修改 `.style.xxx`。
    *   *示例*: `el.dataset.state = 'loading'` (CSS 中用 `[data-state="loading"]` 定义样式)。
*   **事件委派 (Event Delegation)**: 动态生成的列表、表格项，严禁单独绑定事件，必须在父容器上联合 `e.target.closest('.js-xxx')` 统一监听。

### 3. 安全与性能
*   **XSS 防御**: 渲染动态内容时，严禁使用 `innerHTML` 拼接字符串。
    *   优先使用 `document.createElement` 或克隆 `<template>` 节点。
    *   文本填充强制使用 `.textContent`。
*   **异步体感**: 请求长耗时操作必须配套骨架屏（Skeleton Screen）或 `is-loading` 状态。
*   **函数管控**: 搜索输入、窗口 Resize 等高频触发逻辑，必须使用 `debounce`（防抖）或 `throttle`（节流）。

---

## 四、 全链路命名称对齐要求

| 维度 | 规范格式 | 示例 |
| :--- | :--- | :--- |
| **JS 脚本文件名** | `{prefix}_{resource}.js` | `sd_ticket_service.js` |
| **API 路径** | `/api/{prefix}/{resource}` | `/api/sd/tickets` |
| **CSS 类名** | `.prefix-component__element` | `.sd-table__cell` |
| **DOM 逻辑钩子** | `.js-{action}-{resource}` | `.js-delete-ticket` |
| **数据属性** | `data-{key}="{value}"` | `data-ticket-id="123"` |
