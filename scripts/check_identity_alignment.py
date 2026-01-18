"""身份对齐检查脚本 (Identity Alignment Checker)

本脚本检查 GitLab 和禅道用户数据是否与员工主数据严格对齐。
包括：工号、邮箱的一致性校验。

执行方式:
    python scripts/check_identity_alignment.py
"""

import csv
import io
import os
import sys
from pathlib import Path
from collections import defaultdict

# 设置控制台输出为 UTF-8 (解决 Windows GBK 编码问题)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置文件路径
DOCS_DIR = Path(__file__).parent.parent / 'docs'
EMPLOYEES_CSV = DOCS_DIR / 'employees.csv'
GITLAB_CSV = DOCS_DIR / 'gitlab-user.csv'
ZENTAO_CSV = DOCS_DIR / 'zentao-user.csv'


def load_employees():
    """加载员工主数据，返回按邮箱和工号索引的字典。"""
    employees_by_email = {}
    employees_by_id = {}
    
    if not EMPLOYEES_CSV.exists():
        print(f"❌ 员工主数据文件不存在: {EMPLOYEES_CSV}")
        return employees_by_email, employees_by_id
    
    with open(EMPLOYEES_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            emp_id = row.get('工号', '').strip()
            name = row.get('姓名', '').strip()
            email = row.get('邮箱', '').strip().lower()
            
            if email:
                employees_by_email[email] = {
                    'employee_id': emp_id,
                    'name': name,
                    'email': email
                }
            if emp_id:
                employees_by_id[emp_id] = {
                    'employee_id': emp_id,
                    'name': name,
                    'email': email
                }
    
    return employees_by_email, employees_by_id


def check_gitlab_alignment(employees_by_email, employees_by_id):
    """检查 GitLab 用户邮箱是否与员工主数据对齐。"""
    print("\n========== GitLab 身份对齐检查 ==========")
    
    if not GITLAB_CSV.exists():
        print(f"⚠️ GitLab 用户文件不存在: {GITLAB_CSV}")
        return
    
    issues = []
    matched = 0
    unmatched = 0
    
    with open(GITLAB_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gitlab_id = row.get('GitLab用户ID', '').strip()
            username = row.get('用户名', '').strip()
            full_name = row.get('全名', '').strip()
            email = row.get('Email', '').strip().lower()
            
            if not gitlab_id or not email:
                continue
            
            # 检查邮箱是否在员工主数据中
            if email in employees_by_email:
                emp = employees_by_email[email]
                if emp['name'] != full_name:
                    issues.append({
                        'type': '姓名不一致',
                        'gitlab_id': gitlab_id,
                        'username': username,
                        'gitlab_name': full_name,
                        'mdm_name': emp['name'],
                        'email': email
                    })
                else:
                    matched += 1
            else:
                # 尝试通过用户名推断邮箱
                possible_emails = [
                    f"{username}@tjhq.com",
                    f"{username}@szlongtu.com",
                    f"{username}@mofit.com.cn"
                ]
                found = False
                for pe in possible_emails:
                    if pe in employees_by_email:
                        issues.append({
                            'type': '邮箱不匹配',
                            'gitlab_id': gitlab_id,
                            'username': username,
                            'gitlab_name': full_name,
                            'gitlab_email': email,
                            'suggested_email': pe
                        })
                        found = True
                        break
                
                if not found:
                    unmatched += 1
                    issues.append({
                        'type': '未匹配主数据',
                        'gitlab_id': gitlab_id,
                        'username': username,
                        'gitlab_name': full_name,
                        'gitlab_email': email
                    })
    
    # 输出结果
    print(f"✅ 匹配成功: {matched} 条")
    print(f"⚠️ 问题记录: {len(issues)} 条")
    print(f"❌ 未匹配: {unmatched} 条")
    
    if issues:
        print("\n问题详情:")
        for idx, issue in enumerate(issues[:20], 1):  # 只显示前20条
            if issue['type'] == '邮箱不匹配':
                print(f"  {idx}. [{issue['type']}] {issue['gitlab_name']} ({issue['username']})")
                print(f"      GitLab邮箱: {issue['gitlab_email']}")
                print(f"      建议邮箱: {issue['suggested_email']}")
            elif issue['type'] == '姓名不一致':
                print(f"  {idx}. [{issue['type']}] GitLab: {issue['gitlab_name']} vs MDM: {issue['mdm_name']}")
            else:
                print(f"  {idx}. [{issue['type']}] {issue['gitlab_name']} ({issue['gitlab_email']})")
        
        if len(issues) > 20:
            print(f"  ... 还有 {len(issues) - 20} 条问题")
    
    return issues


def check_zentao_alignment(employees_by_email, employees_by_id):
    """检查禅道用户工号/邮箱是否与员工主数据对齐。"""
    print("\n========== 禅道身份对齐检查 ==========")
    
    if not ZENTAO_CSV.exists():
        print(f"⚠️ 禅道用户文件不存在: {ZENTAO_CSV}")
        return
    
    issues = []
    matched = 0
    
    with open(ZENTAO_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            emp_id = row.get('工号', '').strip()
            name = row.get('姓名', '').strip()
            email = row.get('邮箱', '').strip().lower()
            
            if not emp_id and not email:
                continue
            
            # 优先按工号匹配
            if emp_id and emp_id in employees_by_id:
                mdm = employees_by_id[emp_id]
                # 检查邮箱是否一致
                if email and mdm['email'] and email != mdm['email']:
                    issues.append({
                        'type': '邮箱不一致',
                        'employee_id': emp_id,
                        'name': name,
                        'zentao_email': email,
                        'mdm_email': mdm['email']
                    })
                elif mdm['name'] != name:
                    issues.append({
                        'type': '姓名不一致',
                        'employee_id': emp_id,
                        'zentao_name': name,
                        'mdm_name': mdm['name']
                    })
                else:
                    matched += 1
            elif email and email in employees_by_email:
                mdm = employees_by_email[email]
                if mdm['employee_id'] and emp_id and mdm['employee_id'] != emp_id:
                    issues.append({
                        'type': '工号不一致',
                        'name': name,
                        'zentao_id': emp_id,
                        'mdm_id': mdm['employee_id'],
                        'email': email
                    })
                else:
                    matched += 1
            else:
                issues.append({
                    'type': '未匹配主数据',
                    'employee_id': emp_id,
                    'name': name,
                    'email': email
                })
    
    # 输出结果
    print(f"✅ 匹配成功: {matched} 条")
    print(f"⚠️ 问题记录: {len(issues)} 条")
    
    if issues:
        print("\n问题详情:")
        for idx, issue in enumerate(issues[:20], 1):
            if issue['type'] == '邮箱不一致':
                print(f"  {idx}. [{issue['type']}] {issue['name']} ({issue['employee_id']})")
                print(f"      禅道邮箱: {issue['zentao_email']}")
                print(f"      主数据邮箱: {issue['mdm_email']}")
            elif issue['type'] == '工号不一致':
                print(f"  {idx}. [{issue['type']}] {issue['name']}")
                print(f"      禅道工号: {issue['zentao_id']} vs 主数据工号: {issue['mdm_id']}")
            elif issue['type'] == '姓名不一致':
                print(f"  {idx}. [{issue['type']}] 禅道: {issue['zentao_name']} vs 主数据: {issue['mdm_name']}")
            else:
                print(f"  {idx}. [{issue['type']}] {issue['name']} ({issue['employee_id']})")
        
        if len(issues) > 20:
            print(f"  ... 还有 {len(issues) - 20} 条问题")
    
    return issues


def main():
    """主函数：执行身份对齐检查。"""
    print("=" * 50)
    print("身份对齐检查工具 (Identity Alignment Checker)")
    print("=" * 50)
    
    # 加载员工主数据
    print("\n正在加载员工主数据...")
    employees_by_email, employees_by_id = load_employees()
    print(f"  已加载 {len(employees_by_email)} 条邮箱索引")
    print(f"  已加载 {len(employees_by_id)} 条工号索引")
    
    # 检查 GitLab 对齐
    gitlab_issues = check_gitlab_alignment(employees_by_email, employees_by_id)
    
    # 检查禅道对齐
    zentao_issues = check_zentao_alignment(employees_by_email, employees_by_id)
    
    # 总结
    print("\n" + "=" * 50)
    print("检查完成!")
    total_issues = len(gitlab_issues or []) + len(zentao_issues or [])
    if total_issues == 0:
        print("✅ 所有身份数据已严格对齐员工主数据!")
    else:
        print(f"⚠️ 共发现 {total_issues} 条需要处理的问题")
    print("=" * 50)


if __name__ == '__main__':
    main()
