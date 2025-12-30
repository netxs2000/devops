# GitLab Webhook 配置指南 (测试管理中台同步)

为了实现 GitLab 与您的测试管理中台之间的实时数据同步（如在 GitLab 界面打标签后，系统中台能立刻感知），您需要配置 Webhook。

## 1. 准备工作

*   **暴露服务**: 确保您的 `Test Hub` 服务可以被 GitLab 访问。
    *   如果 GitLab 在公网，您可以使用 `ngrok` 或类似工具将 `localhost:8000` 映射出去。
    *   如果 GitLab 在内网，确保防火墙允许 GitLab 服务器访问您的运行地址。

## 2. GitLab 配置步骤

1.  登录您的 GitLab，进入对应的 **Project (项目)**。
2.  在左侧边栏，选择 **Settings (设置)** -> **Webhooks**。
3.  点击 **Add new webhook**（或直接在页面底部的表单中填写）。
4.  **URL**: 输入您的 Webhook 接收地址。
    *   示例: `http://<your-server-ip>:8000/webhook`
5.  **Trigger (触发器)**:
    *   勾选 **Issues events** (议题事件)。
6.  **SSL verification**: 
    *   如果您的服务没有配置 HTTPS，请**取消勾选** "Enable SSL verification"。
7.  **Secret Token**: (可选) 可以在代码中增加验证逻辑，当前原型暂未校验，可留空。
8.  点击 **Add webhook**。

## 3. 验证同步

1.  在 GitLab 项目中找一个标签为 `type::test` 的 Issue。
2.  修改其实施状态（如手动添加 `test-result::passed` 标签并指派给某人）。
3.  检查您运行 `devops_portal` 的终端。
    *   您应当能看到类似以下的日志输出：
    ```text
    INFO: Webhook Received: Test Case #123 was update
    INFO: Test Case #123 passed and archived.
    ```

## 4. 自动同步的进阶应用

配置成功后，您的中台系统可以基于 Webhook 扩展以下功能：
*   **钉钉/企业微信提醒**: 当重要用例执行失败时，自动推送到群组。
*   **状态同步**: 自动更新您自研系统中缓存的测试进度，无需用户手动刷新页面。
*   **报表自动生成**: 每次 Webhook 触发后自动重新计算测试通过率饼图。
