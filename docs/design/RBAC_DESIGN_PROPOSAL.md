# RBAC 权限管理系统设计方案

> 版本: 2.1  
> 日期: 2026-01-18  
> 状态: 已实现 (Implemented)

---

## 一、现状分析

当前系统已全面切换至 RBAC 2.0 架构，核心表结构如下：

| 组件 | 表名 | 说明 |
|------|------|------|
| 用户表 | `mdm_identities` | 复用 MDM 身份表，作为权限主体 |
| 角色表 | `sys_role` | 支持 `data_scope`, `parent_id` 继承 |
| 菜单/权限表 | `sys_menu` | 统一权限标识与前端路由定义 |
| 用户-角色关联 | `sys_user_roles` | 多对多关联 |
| 角色-菜单关联 | `sys_role_menu` | 细粒度功能权限控制 |
| 角色-部门关联 | `sys_role_dept` | 实现自定义数据权限范围 |

### 1.2 迁移成果

1. **架构统一**：成功清理了旧版 `rbac_roles`、`rbac_permissions` 及相关关联表，消除数据重复与逻辑冲突。
2. **规范化**：权限标识规范化为 `业务:模块:操作` 格式 (如 `system:user:list`)。
3. **功能增强**：全面支持了行级权限过滤 (RLS) 和角色继承。
4. **性能优化**：通过 JWT 注入权限标识，减少了高频 API 鉴权时的数据库压力。

---

## 二、目标架构设计

### 2.1 核心设计原则

1. **五表体系**：标准化的 5 张核心表 + 2 张扩展表
2. **角色继承 (RBAC1)**：通过 `parent_id` 实现角色层级
3. **行级权限 (RLS)**：通过 `data_scope` + `sys_role_dept` 实现数据范围控制
4. **权限标识规范**：统一使用 `业务:模块:操作` 格式

### 2.2 表结构设计

#### 2.2.1 核心五表

```
┌────────────────┐       ┌────────────────┐
│  mdm_identities│       │    sys_role    │
│   (用户表)      │◄──────┤    (角色表)     │
│  department_id │  M:N  │  data_scope    │
└───────┬────────┘       │  parent_id     │
        │                └───────┬────────┘
        │                        │
        ▼                        ▼
┌────────────────┐       ┌────────────────┐
│ sys_user_roles │       │  sys_role_menu │
│  (用户-角色)    │       │  (角色-菜单)    │
└────────────────┘       └───────┬────────┘
                                 │
                                 ▼
                         ┌────────────────┐
                         │    sys_menu    │
                         │  (菜单/权限)    │
                         │    parent_id   │
                         │     perms      │
                         └────────────────┘
```

#### 2.2.2 扩展表

```
┌────────────────┐       ┌────────────────┐
│mdm_organizations│       │  sys_role_dept │
│   (组织架构)    │◄──────┤ (角色数据范围)  │
│  parent_org_id │  M:N  │   role_id      │
└────────────────┘       │   dept_id      │
                         └────────────────┘
```

### 2.3 详细表设计

#### (1) sys_menu - 菜单/权限表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| menu_name | String(50) | 菜单名称 |
| parent_id | Integer | 父菜单ID (0=顶级) |
| order_num | Integer | 显示顺序 |
| path | String(200) | 前端路由地址 |
| component | String(255) | 组件路径 |
| query | String(255) | 路由参数 |
| is_frame | Boolean | 是否外链 |
| is_cache | Boolean | 是否缓存 |
| menu_type | Char(1) | M=目录, C=菜单, F=按钮 |
| visible | Boolean | 是否可见 |
| status | Boolean | 是否启用 |
| **perms** | String(100) | **权限标识** (如 `system:user:list`) |
| icon | String(100) | 图标 |
| remark | String(500) | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### (2) sys_role - 角色表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| role_name | String(30) | 角色名称 |
| role_key | String(100) | 角色标识 (如 `SYSTEM_ADMIN`) |
| role_sort | Integer | 显示顺序 |
| **data_scope** | Integer | **数据范围** (见下表) |
| **parent_id** | Integer | **父角色ID** (RBAC1 继承) |
| status | Boolean | 是否启用 |
| del_flag | Boolean | 删除标志 |
| remark | String(500) | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**data_scope 取值**:

| 值 | 含义 | 说明 |
|---|------|------|
| 1 | 全部数据权限 | 无过滤，适用于超管 |
| 2 | 自定义数据权限 | 通过 `sys_role_dept` 指定可见部门 |
| 3 | 本部门数据权限 | 仅看用户所属部门 |
| 4 | 本部门及以下 | 用户部门 + 所有下级部门递归 |
| 5 | 仅本人数据 | 只能看 `create_by` = 本人的记录 |

#### (3) sys_role_menu - 角色菜单关联表

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | Integer | 角色ID (联合主键) |
| menu_id | Integer | 菜单ID (联合主键) |

#### (4) sys_role_dept - 角色部门关联表 (自定义数据权限)

| 字段 | 类型 | 说明 |
|------|------|------|
| role_id | Integer | 角色ID (联合主键) |
| dept_id | String(100) | 部门ID (联合主键) |

#### (5) sys_user_roles - 用户角色关联表

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | UUID | 用户ID (联合主键) |
| role_id | Integer | 角色ID (联合主键) |

---

## 三、权限标识规范

### 3.1 格式定义

```
{业务域}:{模块}:{操作}
```

**示例**:
- `system:user:list` - 系统管理 > 用户管理 > 列表查询
- `system:user:add` - 系统管理 > 用户管理 > 新增
- `system:user:edit` - 系统管理 > 用户管理 > 修改
- `system:user:delete` - 系统管理 > 用户管理 > 删除
- `system:user:export` - 系统管理 > 用户管理 > 导出

### 3.2 业务域划分

| 前缀 | 业务域 | 说明 |
|------|--------|------|
| system | 系统管理 | 用户、角色、菜单、部门管理 |
| delivery | 交付协作 | 迭代、发布、里程碑 |
| analytics | 效能分析 | 效能看板、指标查询 |
| finops | 财务效能 | 成本、合同、预算 |
| product | 产品管理 | 产品定义、项目映射 |
| quality | 质量管理 | 测试用例、缺陷跟踪 |
| okr | 目标管理 | OKR 定义与追踪 |

### 3.3 操作类型

| 操作 | 说明 |
|------|------|
| list / query | 列表查询 |
| add / create | 新增 |
| edit / update | 修改 |
| delete / remove | 删除 |
| export | 导出 |
| import | 导入 |
| approve | 审批 |
| assign | 分配 |

---

## 四、行级权限 (RLS) 实现方案

### 4.1 核心逻辑

```python
def apply_row_level_security(db: Session, query: Query, model_class: Any, current_user: User) -> Query:
    """行级数据权限过滤器。
    
    根据用户角色的 data_scope 配置，自动过滤数据行。
    """
    # 1. 获取用户所有角色中的最大数据范围 (数值越小权限越大)
    data_scope = get_user_effective_data_scope(db, current_user)
    
    if data_scope == 1:  # 全部数据
        return query
    
    if data_scope == 2:  # 自定义数据权限
        allowed_dept_ids = get_custom_dept_ids(db, current_user)
        return query.filter(model_class.dept_id.in_(allowed_dept_ids))
    
    if data_scope == 3:  # 本部门
        return query.filter(model_class.dept_id == current_user.department_id)
    
    if data_scope == 4:  # 本部门及以下
        scope_ids = get_dept_tree_ids(db, current_user.department_id)
        return query.filter(model_class.dept_id.in_(scope_ids))
    
    if data_scope == 5:  # 仅本人
        return query.filter(model_class.create_by == current_user.global_user_id)
    
    return query
```

### 4.2 业务表锚点字段

需要在核心业务表中添加以下字段作为 RLS 过滤锚点：

| 表名 | 锚点字段 | 说明 |
|------|----------|------|
| mdm_projects | org_id | 项目所属部门 |
| mdm_product | owner_team_id | 产品负责团队 |
| mdm_incidents | owner_id, project_id | 事故责任人/项目 |
| mdm_services | org_id | 服务所属组织 |
| gitlab_projects | organization_id | GitLab 项目归属 |

### 4.3 FastAPI 依赖注入

```python
from devops_portal.dependencies import RoleRequired, PermissionRequired, DataScopeFilter

@router.get("/projects")
async def list_projects(
    current_user: User = Depends(PermissionRequired(['product:project:list'])),
    db: Session = Depends(get_db)
):
    query = db.query(ProjectMaster)
    query = apply_row_level_security(db, query, ProjectMaster, current_user)
    return query.all()
```

---

## 五、迁移方案

### 5.1 迁移执行总结

1. **表结构同步**：通过 Alembic 迁移脚本完成了数据库 Schema 的原地升级，旧表已彻底移除。
2. **数据持久化**：使用 `init_rbac.py` 重新初始化了所有标准角色和菜单权限数据。
3. **代码兼容**：所有后台 API 路由已从旧版 Role 依赖切换为 `PermissionRequired`。

### 5.2 阶段二：权限初始化

**sys_menu 初始化数据示例**:

```python
MENU_DATA = [
    # 目录
    {'id': 1, 'menu_name': '系统管理', 'parent_id': 0, 'menu_type': 'M', 'path': 'system', 'icon': 'setting'},
    
    # 菜单
    {'id': 100, 'menu_name': '用户管理', 'parent_id': 1, 'menu_type': 'C', 'path': 'user', 'component': 'system/user/index', 'perms': 'system:user:list'},
    {'id': 101, 'menu_name': '角色管理', 'parent_id': 1, 'menu_type': 'C', 'path': 'role', 'component': 'system/role/index', 'perms': 'system:role:list'},
    {'id': 102, 'menu_name': '菜单管理', 'parent_id': 1, 'menu_type': 'C', 'path': 'menu', 'component': 'system/menu/index', 'perms': 'system:menu:list'},
    
    # 按钮
    {'id': 1001, 'menu_name': '用户新增', 'parent_id': 100, 'menu_type': 'F', 'perms': 'system:user:add'},
    {'id': 1002, 'menu_name': '用户修改', 'parent_id': 100, 'menu_type': 'F', 'perms': 'system:user:edit'},
    {'id': 1003, 'menu_name': '用户删除', 'parent_id': 100, 'menu_type': 'F', 'perms': 'system:user:delete'},
    {'id': 1004, 'menu_name': '用户导出', 'parent_id': 100, 'menu_type': 'F', 'perms': 'system:user:export'},
]
```

**sys_role 初始化数据示例**:

```python
ROLE_DATA = [
    {'id': 1, 'role_name': '超级管理员', 'role_key': 'SYSTEM_ADMIN', 'data_scope': 1, 'parent_id': 0},
    {'id': 2, 'role_name': '研发工程师', 'role_key': 'DEVELOPER', 'data_scope': 4, 'parent_id': 0},
    {'id': 3, 'role_name': '产品经理', 'role_key': 'PRODUCT_MANAGER', 'data_scope': 4, 'parent_id': 0},
    {'id': 4, 'role_name': '财务主管', 'role_key': 'FINANCE_OFFICER', 'data_scope': 1, 'parent_id': 0},
    {'id': 5, 'role_name': '管理层', 'role_key': 'EXECUTIVE_MANAGER', 'data_scope': 1, 'parent_id': 0},
    {'id': 6, 'role_name': '测试工程师', 'role_key': 'QA_ENGINEER', 'data_scope': 4, 'parent_id': 2},
    {'id': 7, 'role_name': '交付工程师', 'role_key': 'DELIVERY_ENGINEER', 'data_scope': 4, 'parent_id': 2},
]
```

### 5.3 阶段三：代码重构

1. **更新 `security.py`**：实现完整的 `apply_row_level_security`
2. **更新 `dependencies.py`**：新增 `PermissionRequired` 装饰器
3. **更新 `auth_service.py`**：JWT 中注入用户权限列表 (从 `sys_role_menu` 聚合)
4. **更新前端 `auth_utils.js`**：对齐新的权限校验逻辑

---

## 六、JWT Token 结构

### 6.1 登录时生成的 Token Payload

```json
{
  "sub": "admin@tjhq.com",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "admin",
  "full_name": "系统管理员",
  "department_id": "DEPT-001",
  "roles": ["SYSTEM_ADMIN"],
  "permissions": [
    "system:user:list",
    "system:user:add",
    "system:role:list",
    "product:project:list",
    "*"
  ],
  "data_scope": 1,
  "exp": 1737187200
}
```

### 6.2 权限聚合逻辑

```python
def aggregate_user_permissions(db: Session, user: User) -> List[str]:
    """聚合用户所有角色的权限标识。"""
    permissions = set()
    
    for role in user.roles:
        # 角色继承：递归获取父角色权限
        role_chain = get_role_hierarchy(db, role)
        for r in role_chain:
            for menu in r.menus:
                if menu.perms:
                    permissions.add(menu.perms)
    
    return list(permissions)
```

---

## 七、前端权限控制

### 7.1 路由守卫

```javascript
// router/permission.js
const whiteList = ['/login', '/register'];

router.beforeEach(async (to, from, next) => {
    if (Auth.isLoggedIn()) {
        if (to.path === '/login') {
            next('/');
        } else {
            // 动态路由加载 (根据用户权限过滤菜单)
            const accessRoutes = await store.dispatch('generateRoutes', Auth.getPayload().permissions);
            router.addRoutes(accessRoutes);
            next();
        }
    } else {
        if (whiteList.includes(to.path)) {
            next();
        } else {
            next('/login');
        }
    }
});
```

### 7.2 按钮级权限指令

```javascript
// directives/permission.js
Vue.directive('permission', {
    inserted(el, binding) {
        const requiredPerm = binding.value;
        if (!Auth.hasPermission(requiredPerm)) {
            el.parentNode && el.parentNode.removeChild(el);
        }
    }
});

// 使用示例
<button v-permission="'system:user:add'">新增用户</button>
```

---

## 八、实施计划

| 阶段 | 任务 | 状态 |
|------|------|------|
| P0 | 审核确认本设计方案 | ✅ 已完成 |
| P1 | 更新 `init_rbac.py` 使用新版表结构 | ✅ 已完成 |
| P2 | 初始化 `sys_menu` 菜单权限数据 | ✅ 已完成 |
| P3 | 重构 `security.py` 实现 RLS | ✅ 已完成 |
| P4 | 更新 `auth_service.py` JWT 权限注入 | ✅ 已完成 |
| P5 | 前端对接 & 测试 | ✅ 已完成 |
| P6 | 清理废弃表 & 迁移验证 | ✅ 已完成 |

**项目结论**: RBAC 2.0 已上线并成为系统标准权限框架。

---

## 九、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据迁移丢失 | 现有角色关联失效 | 迁移前备份，提供回滚脚本 |
| JWT 体积过大 | 降低请求性能 | 权限压缩，仅存角色 |
| 权限配置复杂 | 运维成本高 | 提供可视化管理界面 |

---

## 十、已确认事项

| 决策项 | 确认结果 |
|--------|----------|
| 角色继承深度 | **最多 3 级** |
| 超管权限 | **使用通配符 `*`** |
| 默认 data_scope | **5 (仅本人)** |
| 菜单初始化 | **见下方详细规划** |

---

## 十一、菜单初始化详细规划

### 11.1 一级菜单结构

| ID | 菜单名称 | 英文标识 | 可见角色 |
|----|----------|----------|----------|
| 1 | 平台管理 | Administration | SYSTEM_ADMIN |
| 2 | 支持与战略 | Strategy & Support | 所有人 |
| 3 | 洞察与治理 | Governance & Insights | DEPT_MANAGER, SYSTEM_ADMIN |
| 4 | 质量保障 | Quality Assurance | QA_ENGINEER, DEPT_MANAGER |
| 5 | 项目执行 | Project Execution | DEVELOPER, DEPT_MANAGER |
| 6 | 基础服务 | Foundation Services | 所有人 |

### 11.2 二级菜单详细设计

#### (1) 平台管理 (Administration) - 仅管理员

| ID | 菜单名称 | 路径 | 权限标识 |
|----|----------|------|----------|
| 100 | 用户管理 | /admin/users | system:user:list |
| 101 | 角色管理 | /admin/roles | system:role:list |
| 102 | 菜单管理 | /admin/menus | system:menu:list |
| 103 | 部门管理 | /admin/depts | system:dept:list |
| 104 | 注册审核 | /admin/registrations | system:registration:list |
| 105 | 产品系统管理 | /admin/products | system:product:list |
| 106 | 项目映射配置 | /admin/project-mappings | system:project:mapping |
| 107 | 员工身份目录 | /admin/employees | system:employee:list |

#### (2) 支持与战略 (Strategy & Support) - 所有人

| ID | 菜单名称 | 路径 | 权限标识 |
|----|----------|------|----------|
| 200 | OKR 目标 | /strategy/okr | okr:objective:list |
| 201 | 路线图 | /strategy/roadmap | strategy:roadmap:view |
| 202 | 服务台 | /support/service-desk | support:ticket:list |

#### (3) 洞察与治理 (Governance & Insights) - 部门经理+管理员

| ID | 菜单名称 | 路径 | 权限标识 |
|----|----------|------|----------|
| 300 | 效能看板 | /insights/dashboard | analytics:dashboard:view |
| 301 | DORA 指标 | /insights/dora | analytics:dora:view |
| 302 | 成本分析 | /insights/costs | finops:cost:view |
| 303 | 合规审计 | /governance/compliance | governance:compliance:view |

#### (4) 质量保障 (Quality Assurance) - 测试人员+部门经理

| ID | 菜单名称 | 路径 | 权限标识 |
|----|----------|------|----------|
| 400 | 需求管理 | /qa/requirements | quality:requirement:list |
| 401 | 测试用例 | /qa/test-cases | quality:testcase:list |
| 402 | 测试执行 | /qa/executions | quality:execution:list |
| 403 | 缺陷跟踪 | /qa/bugs | quality:bug:list |

#### (5) 项目执行 (Project Execution) - 开发人员+部门经理

| ID | 菜单名称 | 路径 | 权限标识 |
|----|----------|------|----------|
| 500 | 迭代计划 | /project/sprints | delivery:sprint:list |
| 501 | 任务看板 | /project/kanban | delivery:task:list |
| 502 | 代码仓库 | /project/repos | delivery:repo:list |
| 503 | 流水线 | /project/pipelines | delivery:pipeline:list |
| 504 | 发布管理 | /project/releases | delivery:release:list |

#### (6) 基础服务 (Foundation Services) - 所有人

| ID | 菜单名称 | 路径 | 权限标识 |
|----|----------|------|----------|
| 600 | 个人中心 | /profile | user:profile:view |
| 601 | 消息通知 | /notifications | user:notification:list |
| 602 | 帮助文档 | /help | user:help:view |

### 11.3 按钮级权限 (示例)

以"用户管理"为例：

| ID | 按钮名称 | 权限标识 |
|----|----------|----------|
| 1001 | 用户查询 | system:user:query |
| 1002 | 用户新增 | system:user:add |
| 1003 | 用户修改 | system:user:edit |
| 1004 | 用户删除 | system:user:delete |
| 1005 | 用户导出 | system:user:export |
| 1006 | 重置密码 | system:user:resetPwd |

### 11.4 角色与菜单映射矩阵

| 角色 | 平台管理 | 支持战略 | 洞察治理 | 质量保障 | 项目执行 | 基础服务 |
|------|:--------:|:--------:|:--------:|:--------:|:--------:|:--------:|
| SYSTEM_ADMIN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DEPT_MANAGER | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DEVELOPER | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| QA_ENGINEER | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| PRODUCT_MANAGER | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FINANCE_OFFICER | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| VIEWER | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |

---

**状态: 已确认，开始执行编码工作。**
