"""员工角色自动分配与业务实体关联脚本。

本脚本读取 docs/employees.csv，根据员工的职位关键词：
1. 自动分配 RBAC 角色 (研发、产品、测试、交付、管理等)。
2. 将部门负责人关联到 mdm_organizations、mdm_product 和 mdm_projects。
3. 建立初步的人员-产品线逻辑关联。

执行方式:
    python scripts/link_users_to_entities.py
"""

import csv
import logging
import os
import sys
from typing import List, Optional

import pypinyin
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import (
    Base, User, SysRole, Organization, Product, ProjectMaster, UserRole
)

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LinkUsers')

from pathlib import Path
CSV_FILE = Path(__file__).parent.parent / 'docs' / 'employees.csv'

# 职位 -> 角色代码 映射规则
POSITION_ROLE_MAP = {
    '总经理': 'EXECUTIVE_MANAGER',
    '副总经理': 'EXECUTIVE_MANAGER',
    '中心总经理': 'EXECUTIVE_MANAGER',
    '中心副总经理': 'EXECUTIVE_MANAGER',
    '产品经理': 'PRODUCT_MANAGER',
    '产品总监': 'PRODUCT_MANAGER',
    '产品工程师': 'PRODUCT_MANAGER',
    '测试工程师': 'QA_ENGINEER',
    '测试经理': 'QA_ENGINEER',
    '集成工程师': 'QA_ENGINEER',
    '质量': 'QA_ENGINEER',
    '项目总监': 'DELIVERY_ENGINEER',
    '项目经理': 'DELIVERY_ENGINEER',
    '实施工程师': 'DELIVERY_ENGINEER',
    '交付': 'DELIVERY_ENGINEER',
    '财务': 'FINANCE_OFFICER',
    '开发工程师': 'DEVELOPER',
    '技术总监': 'DEVELOPER',
    '架构': 'DEVELOPER',
    '开发经理': 'DEVELOPER',
    '技术经理': 'DEVELOPER',
    'BI工程师': 'DEVELOPER',
    '中台框架': 'DEVELOPER',
}

def to_pinyin(name: str) -> str:
    """将中文姓名转换为拼音。"""
    return "".join(pypinyin.lazy_pinyin(name))

def get_role_by_position(position: str) -> str:
    """根据职位描述推断角色代码。"""
    for keyword, role_code in POSITION_ROLE_MAP.items():
        if keyword in position:
            return role_code
    return 'DEVELOPER' # 默认兜底角色

def link_users_to_entities():
    """主执行函数：同步角色与关联关系。"""
    engine = create_engine(settings.database.uri)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # 预加载角色
    all_roles = {r.role_key: r for r in session.query(SysRole).all()}
    
    try:
        if not os.path.exists(CSV_FILE):
            logger.error(f"找不到 CSV 文件: {CSV_FILE}")
            return

        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                name = row.get('姓名', '').strip()
                position = row.get('职位', '').strip()
                dept_name = row.get('部门', '').strip()
                center_name = row.get('中心', '').strip()

                if not name:
                    continue

                # 1. 查找用户
                username = to_pinyin(name)
                email = f"{username}@tjhq.com"
                user = session.query(User).filter_by(primary_email=email, is_current=True).first()

                if not user:
                    # 尝试通过姓名模糊查找
                    user = session.query(User).filter(User.full_name == name, User.is_current == True).first()
                
                if not user:
                    logger.warning(f"跳过用户 {name}：在数据库中未找到。")
                    continue

                # 2. 角色分配
                role_code = get_role_by_position(position)
                target_role = all_roles.get(role_code)
                if target_role:
                    # 检查是否已有关联
                    existing = session.query(UserRole).filter_by(user_id=user.global_user_id, role_id=target_role.id).first()
                    if not existing:
                        user_role = UserRole(user_id=user.global_user_id, role_id=target_role.id)
                        session.add(user_role)
                
                # 3. 负责人关联 (经理/总监级别)
                is_manager = '经理' in position or '总监' in position or '总经理' in position
                if is_manager:
                    # 关联到组织
                    org = session.query(Organization).filter(Organization.org_name == dept_name).first()
                    if not org:
                        org = session.query(Organization).filter(Organization.org_name == center_name).first()
                    
                    if org:
                        org.manager_user_id = user.global_user_id
                        logger.info(f"已设置 {name} 为组织 {org.org_name} 的负责人")

                        # 关联到该组织下的所有产品
                        products = session.query(Product).filter_by(owner_team_id=org.org_id).all()
                        for prod in products:
                            prod.product_manager_id = user.global_user_id
                            logger.debug(f"已设置 {name} 为产品 {prod.product_name} 的产品经理")

                        # 关联到该组织下的所有项目
                        projects = session.query(ProjectMaster).filter_by(org_id=org.org_id).all()
                        for proj in projects:
                            # 只有当项目还没有具体负责人时才自动填充（避免覆盖更精细的初始化）
                            if not proj.pm_user_id:
                                proj.pm_user_id = user.global_user_id

                count += 1
                if count % 50 == 0:
                    session.flush()

            session.commit()
            logger.info(f"✅ 成功处理 {count} 位员工的角色与关联关系同步。")

    except Exception as e:
        session.rollback()
        logger.error(f"同步失败: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    link_users_to_entities()
