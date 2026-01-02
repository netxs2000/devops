"""为 User 模型添加部门和省份字段的数据库迁移脚本

新增字段:
    - department_id: UUID, 外键关联到 mdm_organizations
    - province: String(50), 所属省份/地区代码
"""

def add_department_fields_to_user():
    """在 base_models.py 的 User 类中添加部门相关字段"""
    file_path = 'devops_collector/models/base_models.py'
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    import re
    new_fields = "\n    # 组织与地域属性 (用于数据隔离与权限控制)\n    department_id = Column(UUID(as_uuid=True), ForeignKey('mdm_organizations.global_org_id'))  # 所属部门/组织\n    province = Column(String(50))  # 所属省份代码 (如 'guangdong', 'beijing', 'nationwide')\n    "
    pattern = '(    sync_version = Column\\(BigInteger, default=1\\)\\s*\\n)'
    if re.search(pattern, content):
        modified_content = re.sub(pattern, '\\1' + new_fields + '\n', content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        print(f'[SUCCESS] Added department fields to User model')
        print(f'  - department_id (FK -> mdm_organizations)')
        print(f'  - province (String)')
        return True
    else:
        print('[ERROR] Could not find insertion point (sync_version line)')
        return False
if __name__ == '__main__':
    success = add_department_fields_to_user()
    exit(0 if success else 1)