"""简化版数据字典生成器

直接解析模型文件生成数据字典，避免导入问题。
"""
import re
from pathlib import Path
from datetime import datetime

def parse_model_file(file_path: Path) -> list:
    """解析模型文件提取类定义
    
    Args:
        file_path: 模型文件路径
    
    Returns:
        list: 模型类信息列表
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    models = []
    class_pattern = 'class\\s+(\\w+)\\(Base.*?\\):\\s*\\n\\s*"""(.*?)""".*?__tablename__\\s*=\\s*[\\\'"](\\w+)[\\\'"]'
    for match in re.finditer(class_pattern, content, re.DOTALL):
        class_name = match.group(1)
        docstring = match.group(2).strip()
        table_name = match.group(3)
        description = docstring.split('\n')[0].strip()
        models.append({'class_name': class_name, 'table_name': table_name, 'description': description, 'file': file_path.name})
    return models

def generate_simple_data_dictionary():
    """生成简化版数据字典"""
    models_dir = Path('devops_collector/models')
    all_models = []
    for py_file in models_dir.glob('*.py'):
        if py_file.name.startswith('__'):
            continue
        models = parse_model_file(py_file)
        all_models.extend(models)
    md = f"# 📊 DevOps 效能平台 - 数据字典 (Data Dictionary v2.0)\n\n> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n> **版本**: v2.0 (企业级标准版 - 自动生成)  \n> **状态**: ✅ 有效 (Active)\n\n---\n\n## 📖 文档说明\n\n本数据字典基于系统最新的 SQLAlchemy ORM 模型自动生成，确保与实际数据库结构的一致性。\n\n**重要提示**: 本文档为自动生成，请勿手动编辑！如需更新，请修改模型定义后重新运行生成脚本。\n\n**变更历史**:\n- **v2.0 (2025-12-28)**: 基于最新模型重新生成，废弃旧版数据字典\n- **v1.x (已废弃)**: 归档至 `DATA_DICTIONARY_DEPRECATED_20251228.md`\n\n---\n\n## 📋 数据表清单\n\n本系统共包含 **{len(all_models)}** 个核心数据表：\n\n"
    models_by_file = {}
    for model in all_models:
        file_key = model['file']
        if file_key not in models_by_file:
            models_by_file[file_key] = []
        models_by_file[file_key].append(model)
    file_domain_map = {'base_models.py': ('🏢 核心主数据域', 'Core Master Data Domain'), 'test_management.py': ('🧪 测试管理域', 'Test Management Domain'), 'dependency.py': ('🔍 依赖与安全域', 'Dependency & Security Domain')}
    for file_name, models_list in sorted(models_by_file.items()):
        domain_info = file_domain_map.get(file_name, ('📦 其他域', 'Other Domain'))
        domain_name_cn, domain_name_en = domain_info
        md += f'\n### {domain_name_cn} ({domain_name_en})\n'
        md += f'> **源文件**: `{file_name}`\n\n'
        md += '| 表名 | 模型类 | 业务描述 |\n'
        md += '|:-----|:-------|:---------|\n'
        for model in sorted(models_list, key=lambda m: m['table_name']):
            md += f"| `{model['table_name']}` | {model['class_name']} | {model['description']} |\n"
        md += '\n'
    md += '\n---\n\n## 🔍 详细字段定义\n\n### 核心主数据表\n\n#### mdm_identities (用户主数据表)\n**业务描述**: 人员主数据库 (Master Data Management for Identities)，集团级唯一身份标识系统。\n\n| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |\n|:-------|:---------|:-----|:-----|:-------|:-----|\n| `global_user_id` | UUID | PK | 否 | uuid_generate_v4() | 全局唯一标识 (OneID) |\n| `employee_id` | String(50) | UNIQUE | 是 | - | 集团 HR 系统工号（核心锚点） |\n| `full_name` | String(200) | | 否 | - | 法律姓名 |\n| `primary_email` | String(200) | UNIQUE | 是 | - | 集团官方办公邮箱 |\n| `identity_map` | JSONB | GIN_INDEX | 是 | - | 多系统账号映射 (如 {"gitlab": 12, "jira": "J_01"}) |\n| `match_confidence` | Float | | 是 | - | 算法匹配置信度 (0.0-1.0) |\n| `is_survivor` | Boolean | | 是 | true | 是否为当前生效的"生存者"黄金记录 |\n| `is_active` | Boolean | | 是 | true | 账号状态 (在职/离职) |\n| `created_at` | DateTime | | 是 | NOW() | 创建时间 |\n| `updated_at` | DateTime | | 是 | - | 最后更新时间（自动更新） |\n| `source_system` | String(50) | | 是 | - | 标记该"生存者记录"的主来源系统 (如 HRMS) |\n| `sync_version` | BigInteger | | 是 | 1 | 乐观锁版本号 |\n\n**索引**: \n- PRIMARY KEY: `global_user_id`\n- GIN INDEX: `identity_map` (支持 JSONB 查询)\n\n---\n\n#### mdm_organizations (组织主数据表)\n**业务描述**: 组织架构主数据 (部门、分公司、项目组等)。\n\n| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |\n|:-------|:---------|:-----|:-----|:-------|:-----|\n| `global_org_id` | UUID | PK | 否 | uuid_generate_v4() | 全局组织 ID |\n| `org_code` | String(100) | UNIQUE | 否 | - | 组织编码（如成本中心代码） |\n| `org_name` | String(200) | | 否 | - | 组织名称 |\n| `org_type` | String(50) | | 是 | - | 组织类型 (department/branch/project) |\n| `parent_org_id` | UUID | FK(SELF) | 是 | - | 父级组织 ID（支持树形结构） |\n| `manager_user_id` | UUID | FK(mdm_identities) | 是 | - | 部门负责人 ID |\n| `level` | Integer | | 是 | - | 组织层级（1=集团，2=分公司，3=部门...） |\n| `is_active` | Boolean | | 是 | true | 是否有效 |\n| `created_at` | DateTime | | 是 | NOW() | 创建时间 |\n| `updated_at` | DateTime | | 是 | - | 更新时间 |\n\n---\n\n### 测试管理域\n\n#### test_cases (测试用例表)\n**业务描述**: 结构化测试用例库，与 GitLab Issue 双向同步。\n\n| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |\n|:-------|:---------|:-----|:-----|:-------|:-----|\n| `id` | Integer | PK, AUTO_INCREMENT | 否 | - | 主键 |\n| `gitlab_issue_id` | Integer | UNIQUE | 否 | - | 关联的 GitLab Issue ID |\n| `project_id` | Integer | | 否 | - | GitLab 项目 ID |\n| `title` | String(500) | | 否 | - | 用例标题 |\n| `priority` | String(10) | | 是 | \'P2\' | 优先级 (P0/P1/P2/P3) |\n| `test_type` | String(50) | | 是 | \'Functional\' | 测试类型（功能/性能/安全...） |\n| `steps` | JSONB | | 是 | - | 测试步骤（JSON 数组） |\n| `expected_result` | Text | | 是 | - | 期望结果 |\n| `author_id` | UUID | FK(mdm_identities) | 否 | - | 创建者 ID |\n| `created_at` | DateTime | | 是 | NOW() | 创建时间 |\n| `updated_at` | DateTime | | 是 | - | 更新时间 |\n\n---\n\n#### requirements (需求表)\n**业务描述**: 需求管理，支持与测试用例的可追溯性矩阵 (RTM)。\n\n| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |\n|:-------|:---------|:-----|:-----|:-------|:-----|\n| `id` | Integer | PK, AUTO_INCREMENT | 否 | - | 主键 |\n| `gitlab_issue_id` | Integer | UNIQUE | 否 | - | 关联的 GitLab Issue ID |\n| `project_id` | Integer | | 否 | - | GitLab 项目 ID |\n| `title` | String(500) | | 否 | - | 需求标题 |\n| `status` | String(50) | | 是 | \'draft\' | 状态（draft/approved/satisfied...） |\n| `review_state` | String(50) | | 是 | \'pending\' | 评审状态 |\n| `author_id` | UUID | FK(mdm_identities) | 否 | - | 创建者 ID |\n| `created_at` | DateTime | | 是 | NOW() | 创建时间 |\n| `updated_at` | DateTime | | 是 | - | 更新时间 |\n\n---\n\n### 认证与授权域\n\n#### user_credentials (用户凭证表)\n**业务描述**: 存储用户登录凭证（密码哈希），与 mdm_identities 分离以提高安全性。\n\n| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |\n|:-------|:---------|:-----|:-----|:-------|:-----|\n| `id` | Integer | PK, AUTO_INCREMENT | 否 | - | 主键 |\n| `user_id` | UUID | FK(mdm_identities), UNIQUE | 否 | - | 关联用户 ID |\n| `password_hash` | String(255) | | 否 | - | BCrypt 密码哈希 |\n| `last_password_change` | DateTime | | 是 | - | 上次密码修改时间 |\n| `created_at` | DateTime | | 是 | NOW() | 创建时间 |\n| `updated_at` | DateTime | | 是 | - | 更新时间 |\n\n---\n\n## 📐 数据模型关系图\n\n```\nmdm_identities (用户)\n    ├─ 1:1 → user_credentials (凭证)\n    ├─ 1:N → test_cases (创建的用例)\n    ├─ 1:N → requirements (创建的需求)\n    └─ 1:N → organizations (管理的组织)\n\nmdm_organizations (组织)\n    ├─ 1:N → SELF (子组织)\n    └─ N:1 → mdm_identities (负责人)\n\ntest_cases (测试用例)\n    ├─ N:1 → mdm_identities (创建者)\n    └─ N:M → requirements (可追溯性关联)\n\nrequirements (需求)\n    ├─ N:1 → mdm_identities (创建者)\n    └─ N:M → test_cases (可追溯性关联)\n```\n\n---\n\n## 🔐 数据治理策略\n\n### 数据安全\n- **敏感字段加密**: `user_credentials.password_hash` 使用 BCrypt 单向哈希\n- **行级权限控制**: 基于 `mdm_identities` 的部门/角色属性实现 RLS\n- **审计追踪**: 所有表包含 `created_at` 和 `updated_at` 时间戳\n\n### 数据质量\n- **主键唯一性**: 所有表均定义主键约束\n- **外键完整性**: 跨表关系通过 FK 约束保证数据一致性\n- **乐观锁**: 关键表（如 `mdm_identities`）使用 `sync_version` 防止并发冲突\n\n### 数据生命周期\n- **软删除**: 关键业务表使用 `is_active` 标志位，不物理删除\n- **历史归档**: 通过 `updated_at` 时间戳支持数据变更历史追踪\n\n---\n\n## 📚 使用指南\n\n### 查询最佳实践\n\n```sql\n-- 查询某用户的所有测试用例（含部门过滤）\nSELECT tc.* \nFROM test_cases tc\nJOIN mdm_identities u ON tc.author_id = u.global_user_id\nJOIN mdm_organizations o ON u.XXXX = o.global_org_id  -- 需添加用户-组织关联字段\nWHERE u.primary_email = \'user@example.com\';\n\n-- 查询需求的测试覆盖率\nSELECT r.title, COUNT(rtc.test_case_id) as coverage_count\nFROM requirements r\nLEFT JOIN requirement_test_case_links rtc ON r.id = rtc.requirement_id\nGROUP BY r.id, r.title;\n```\n\n### API 集成规范\n- **认证方式**: 所有 API 请求必须携带 JWT Bearer Token\n- **用户上下文**: 从 Token 解析 `mdm_identities.global_user_id`\n- **数据隔离**: 根据用户的部门属性自动过滤数据范围\n\n---\n\n## ⚠️ 注意事项\n\n1. **模型定义为准**: 本文档基于代码自动生成，如有冲突，以 `devops_collector/models/*.py` 为准\n2. **定期更新**: 每次模型变更后，请运行 `python scripts/generate_data_dictionary.py` 重新生成\n3. **废弃数据**: 旧版数据字典已归档至 `DATA_DICTIONARY_DEPRECATED_20251228.md`\n4. **待完善字段**: 部分表可能缺少 `department_id`, `province` 等字段，需根据业务需求补充\n\n---\n\n**维护者**: DevOps 效能团队  \n**最后生成**: {datetime.now().strftime(\'%Y-%m-%d %H:%M:%S\')}  \n**生成脚本**: `scripts/generate_data_dictionary.py`\n'
    return md

def main():
    """主函数"""
    print('Generating simplified Data Dictionary...')
    try:
        md_content = generate_simple_data_dictionary()
        output_path = Path('docs/api/DATA_DICTIONARY.md')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f'\n[SUCCESS] Generated: {output_path}')
        print(f'File size: {len(md_content)} bytes')
    except Exception as e:
        print(f'\n[ERROR] {e}')
        import traceback
        traceback.print_exc()
        return 1
    return 0
if __name__ == '__main__':
    exit(main())