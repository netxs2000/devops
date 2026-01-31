# Service Desk E2E 测试指南

本目录包含 Service Desk 模块的端到端 (E2E) 测试，使用 Playwright 框架实现。

## 目录结构

```
tests/e2e/service_desk/
├── conftest.py                  # 公共 Fixtures (服务器、认证、数据)
├── pytest.ini                   # E2E 专用 pytest 配置
├── __init__.py
├── pages/                       # Page Object 模式
│   ├── __init__.py
│   ├── base_page.py             # Page Object 基类
│   └── service_desk_page.py     # Service Desk 页面对象
├── test_sd_support_center.py    # Support Center (RD 视图) 测试
├── test_sd_login.py             # 登录与权限测试
└── test_sd_api_endpoints.py     # API 端点验证测试
```

## 快速开始

### 1. 安装依赖

```bash
# 使用 Makefile (推荐)
make e2e-install

# 或手动安装
pip install -e .[e2e]
playwright install chromium
```

### 2. 配置测试环境

创建 `.env.e2e` 文件或设置环境变量：

```bash
# 测试用户凭据 (需在数据库中预先创建)
E2E_TEST_USER_EMAIL=e2e_test@example.com
E2E_TEST_USER_PASSWORD=e2e_test_password

# RD 用户凭据 (用于工单处理测试)
E2E_RD_USER_EMAIL=rd_test@example.com
E2E_RD_USER_PASSWORD=rd_test_password

# 外部服务器模式 (可选，用于测试已运行的服务)
E2E_EXTERNAL_SERVER=0
E2E_BASE_URL=http://127.0.0.1:8000
```

### 3. 运行测试

```bash
# 运行所有 E2E 测试 (无头模式)
make e2e-test

# 可视化模式 (调试用)
make e2e-test-headed

# 带追踪模式 (失败时保留追踪)
make e2e-test-trace

# 仅运行冒烟测试
make e2e-smoke

# 查看失败追踪
make e2e-show-trace
```

## 测试覆盖范围

### test_sd_support_center.py - Support Center 测试

| 测试用例 | 描述 | 状态 |
|----------|------|------|
| `test_navigate_to_support_center_should_show_ticket_list` | 导航到 Support Center 显示工单列表 | ✅ |
| `test_ticket_list_should_load_tickets_from_api` | 工单列表从 API 加载数据 | ✅ |
| `test_sync_button_should_refresh_ticket_list` | 同步按钮刷新列表 | ✅ |
| `test_convert_ticket_to_defect_should_open_bug_form` | 工单转缺陷 | ⏸️ 需预置数据 |
| `test_convert_ticket_to_requirement_should_open_req_form` | 工单转需求 | ⏸️ 需预置数据 |
| `test_reject_ticket_should_close_and_remove_from_list` | 驳回工单 | ⏸️ 需预置数据 |
| `test_ai_rca_should_open_analysis_modal` | AI RCA 分析 | ⏸️ 需预置数据 |

### test_sd_login.py - 登录测试

| 测试用例 | 描述 | 状态 |
|----------|------|------|
| `test_unauthenticated_user_should_see_login_modal` | 未登录显示登录框 | ✅ |
| `test_login_modal_should_have_required_fields` | 登录框包含必要字段 | ✅ |
| `test_empty_login_should_show_error` | 空表单提交显示错误 | ✅ |
| `test_invalid_credentials_should_show_error` | 错误凭据显示错误 | ✅ |
| `test_successful_login_should_hide_modal_and_show_sidebar` | 成功登录后隐藏模态框 | ⏸️ 需有效凭据 |

### test_sd_api_endpoints.py - API 测试

| 测试用例 | 描述 | 状态 |
|----------|------|------|
| `test_health_endpoint_should_return_200` | 健康检查端点 | ✅ |
| `test_tickets_endpoint_without_auth_should_return_401` | 未认证返回 401 | ✅ |
| `test_business_projects_without_auth_should_return_401` | 未认证返回 401 | ✅ |
| `test_tickets_endpoint_with_auth_should_return_200` | 认证后返回 200 | ⏸️ 需有效凭据 |

## Page Object 模式

### BasePage

提供所有页面共用的方法：
- `goto(path)` - 导航到指定路径
- `click_sidebar_link(text)` - 点击侧边栏链接
- `wait_for_toast(message)` - 等待 Toast 提示
- `take_screenshot(name)` - 截取页面截图

### ServiceDeskPage

封装 Service Desk 特定操作：
- `navigate_to_support_center()` - 导航到 Support Center
- `get_ticket_count()` - 获取工单数量
- `convert_to_defect(iid)` - 将工单转为缺陷
- `reject_ticket(iid, reason)` - 驳回工单
- `assert_ticket_exists(iid)` - 断言工单存在

## 数据准备

E2E 测试需要预先准备测试数据：

### 1. 测试用户

```sql
-- 在测试数据库中创建 E2E 测试用户
INSERT INTO users (global_user_id, primary_email, username, password_hash, is_active)
VALUES (
    gen_random_uuid(),
    'e2e_test@example.com',
    'e2e_test',
    '$2b$12$...',  -- bcrypt hash of 'e2e_test_password'
    true
);
```

### 2. 测试工单

```python
# 使用 seed_pending_ticket fixture 或手动创建
from devops_collector.models.service_desk import ServiceDeskTicket

ticket = ServiceDeskTicket(
    gitlab_project_id=100,
    gitlab_issue_iid=9999,
    title="E2E Test Ticket",
    status="opened",
)
```

## 调试技巧

### 1. 使用可视化模式

```bash
pytest tests/e2e/service_desk/ -v --headed
```

### 2. 暂停测试进行交互

```python
page.pause()  # 在测试中添加此行
```

### 3. 查看失败追踪

```bash
# 运行测试时保留追踪
pytest tests/e2e/ --tracing=retain-on-failure

# 查看追踪
playwright show-trace test-results/trace.zip
```

### 4. 截取调试截图

```python
self.page.screenshot(path="debug.png", full_page=True)
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: E2E Tests

on:
  pull_request:
    paths:
      - 'devops_portal/**'
      - 'tests/e2e/**'

jobs:
  e2e:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Dependencies
        run: |
          pip install -e .[e2e]
          playwright install chromium --with-deps
      
      - name: Start Application
        run: |
          docker-compose up -d
          sleep 30
      
      - name: Run E2E Tests
        run: pytest tests/e2e/service_desk/ -v
        env:
          E2E_EXTERNAL_SERVER: "1"
          E2E_BASE_URL: "http://localhost:8000"
      
      - name: Upload Traces
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-traces
          path: test-results/
```

## 常见问题

### Q: 测试无法连接到服务器

确保服务器已启动：
```bash
make up
# 或
E2E_EXTERNAL_SERVER=1 pytest tests/e2e/
```

### Q: 登录测试失败

检查测试用户是否已创建：
```bash
# 查看数据库中的用户
docker-compose exec db psql -U devops -c "SELECT * FROM users WHERE primary_email='e2e_test@example.com';"
```

### Q: 元素定位失败

1. 使用 `--headed` 模式查看实际页面
2. 检查选择器是否正确
3. 添加适当的等待：`page.wait_for_selector(...)`

## 扩展测试

### 添加新测试用例

1. 在 `pages/` 中添加新的 Page Object (如需要)
2. 创建新的测试文件 `test_sd_*.py`
3. 使用现有 fixtures (`authenticated_page`, `app_server` 等)
4. 遵循命名规范：`test_{scenario}_should_{expected_behavior}`

### 添加新的 Fixture

在 `conftest.py` 中添加：
```python
@pytest.fixture
def my_new_fixture():
    # 设置
    yield resource
    # 清理
```
