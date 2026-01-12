"""初始化 RBAC 权限系统脚本。

本脚本用于自动化初始化 DevOps 平台的权限控制系统，包括：
1. 定义原子权限点 (Permissions)，涵盖系统、迭代、用户、分析、财务和产品维度。
2. 定义标准角色 (Roles)，如系统管理员、研发工程师、产品经理、财务主管及管理层。
3. 建立角色与权限的关联关系。
4. 创建初始超级管理员账号。

执行方式:
    python scripts/init_rbac.py
"""

import logging
import os
import sys
import uuid
from typing import List, Dict, Any

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import Base, User, Role, Permission, RolePermission, UserCredential, UserRole

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitRBAC')

# 密码加密配置
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def init_permissions(session: Session) -> List[Dict[str, str]]:
    """初始化系统原子权限点。

    Args:
        session: SQLAlchemy 数据库会话。

    Returns:
        定义好的权限数据列表。
    """
    permissions_data = [
        # 系统管理
        {'code': 'SYSTEM:ADMIN', 'category': 'SYSTEM', 'desc': '系统超级管理权限，无视规则'},
        
        # 交付协作 (Iteration/Release)
        {'code': 'ITERATION:VIEW', 'category': 'DELIVERY', 'desc': '查看迭代任务与进度'},
        {'code': 'ITERATION:MANAGE', 'category': 'DELIVERY', 'desc': '创建、编辑与规划迭代'},
        {'code': 'RELEASE:EXECUTE', 'category': 'DELIVERY', 'desc': '执行版本发布与流水线触发'},
        
        # 用户与权限 (User/Auth)
        {'code': 'USER:VIEW', 'category': 'IDENTITY', 'desc': '查看用户档案与团队归属'},
        {'code': 'USER:MANAGE', 'category': 'IDENTITY', 'desc': '管理用户、角色分配与权限授权'},
        
        # 效能与度量 (Analytics)
        {'code': 'ANALYTICS:VIEW_ALL', 'category': 'ANALYTICS', 'desc': '查看全公司维度的效能看板'},
        {'code': 'ANALYTICS:VIEW_DEPT', 'category': 'ANALYTICS', 'desc': '仅能查看所属部门的效能看板'},
        
        # 财务与效能 (FinOps)
        {'code': 'FINOPS:VIEW_COST', 'category': 'FINOPS', 'desc': '查看云资源与人力成本'},
        {'code': 'FINOPS:MANAGE_CONTRACT', 'category': 'FINOPS', 'desc': '管理收入、支出合同与付款节点'},
        
        # 产品与 OKR (Business)
        {'code': 'PRODUCT:VIEW', 'category': 'BUSINESS', 'desc': '查看产品主数据与关联项目'},
        {'code': 'PRODUCT:MANAGE', 'category': 'BUSINESS', 'desc': '维护产品定义、架构图与映射关系'},
        {'code': 'OKR:VIEW', 'category': 'BUSINESS', 'desc': '查看组织的 OKR 目标与对齐图谱'},
        {'code': 'OKR:MANAGE', 'category': 'BUSINESS', 'desc': '制定建议或更新关键结果进度'},
    ]

    logger.info('正在初始化原子权限点...')
    for p_data in permissions_data:
        perm = session.query(Permission).filter_by(code=p_data['code']).first()
        if not perm:
            perm = Permission(
                code=p_data['code'],
                category=p_data['category'],
                description=p_data['desc']
            )
            session.add(perm)
    session.commit()
    return permissions_data


def init_roles(session: Session):
    """初始化标准角色及其对应的权限映射。

    Args:
        session: SQLAlchemy 数据库会话。
    """
    logger.info('正在初始化标准角色及其权限映射...')

    role_definitions = [
        {
            'code': 'SYSTEM_ADMIN',
            'name': '系统管理员',
            'desc': '拥有系统所有权限的超级账号',
            'perms': ['*'] # 特殊处理，下文会通过全选实现
        },
        {
            'code': 'DEVELOPER',
            'name': '研发工程师',
            'desc': '日常开发人员，关注迭代交付与个人/团队效能',
            'perms': ['ITERATION:VIEW', 'ITERATION:MANAGE', 'RELEASE:EXECUTE', 'USER:VIEW', 'PRODUCT:VIEW', 'ANALYTICS:VIEW_DEPT']
        },
        {
            'code': 'PRODUCT_MANAGER',
            'name': '产品经理',
            'desc': '负责规划交付节奏，对产品定义与业务价值目标负责',
            'perms': ['ITERATION:VIEW', 'ITERATION:MANAGE', 'PRODUCT:VIEW', 'PRODUCT:MANAGE', 'OKR:VIEW', 'OKR:MANAGE']
        },
        {
            'code': 'FINANCE_OFFICER',
            'name': '财务主管',
            'desc': '关注研发投入成本、合同回款与财务合规',
            'perms': ['FINOPS:VIEW_COST', 'FINOPS:MANAGE_CONTRACT', 'ANALYTICS:VIEW_ALL', 'PRODUCT:VIEW']
        },
        {
            'code': 'EXECUTIVE_MANAGER',
            'name': '管理层',
            'desc': '关注全公司效能、经营目标对齐及成本利润率',
            'perms': ['ANALYTICS:VIEW_ALL', 'OKR:VIEW', 'PRODUCT:VIEW', 'FINOPS:VIEW_COST']
        },
        {
            'code': 'QA_ENGINEER',
            'name': '测试工程师',
            'desc': '负责质量保障，关注 Bug 趋势、测试覆盖率及发布质量盖章',
            'perms': ['ITERATION:VIEW', 'RELEASE:EXECUTE', 'PRODUCT:VIEW', 'ANALYTICS:VIEW_DEPT']
        },
        {
            'code': 'DELIVERY_ENGINEER',
            'name': '交付工程师',
            'desc': '负责项目交付与发布，关注流水线状态及上线稳定性',
            'perms': ['ITERATION:VIEW', 'ITERATION:MANAGE', 'RELEASE:EXECUTE', 'ANALYTICS:VIEW_DEPT']
        }
    ]

    for r_def in role_definitions:
        role = session.query(Role).filter_by(code=r_def['code']).first()
        if not role:
            role = Role(name=r_def['name'], code=r_def['code'], description=r_def['desc'])
            session.add(role)
            session.flush() # 获取 role.id
        else:
            role.name = r_def['name']
            role.description = r_def['desc']
            # 清理旧权限，准备重新映射
            session.query(RolePermission).filter_by(role_id=role.id).delete()

        # 映射权限
        if '*' in r_def['perms']:
            target_perms = session.query(Permission).all()
        else:
            target_perms = session.query(Permission).filter(Permission.code.in_(r_def['perms'])).all()

        for p in target_perms:
            rp = RolePermission(role_id=role.id, permission_code=p.code)
            session.add(rp)
    
    session.commit()


def create_super_admin(session: Session):
    """创建或更新初始超级管理员账户。

    Args:
        session: SQLAlchemy 数据库会话。
    """
    admin_email = 'admin@tjhq.com'  # 对齐组织域名
    default_password = 'admin_password_123!'
    
    logger.info(f'正在检查超级管理员账号 ({admin_email})...')
    user = session.query(User).filter_by(primary_email=admin_email, is_current=True).first()
    
    if not user:
        logger.info('正在创建新的超级管理员用户...')
        user = User(
            global_user_id=uuid.uuid4(),
            username='admin',
            full_name='系统管理员',
            primary_email=admin_email,
            is_active=True,
            is_survivor=True,
            sync_version=1,
            is_current=True,
            is_deleted=False
        )
        session.add(user)
        session.flush()
        
        pw_hash = pwd_context.hash(default_password)
        cred = UserCredential(user_id=user.global_user_id, password_hash=pw_hash)
        session.add(cred)
    
    # 确保关联到管理员角色
    admin_role = session.query(Role).filter_by(code='SYSTEM_ADMIN').first()
    if admin_role:
        existing_ur = session.query(UserRole).filter_by(user_id=user.global_user_id, role_id=admin_role.id).first()
        if not existing_ur:
            user_role = UserRole(user_id=user.global_user_id, role_id=admin_role.id)
            session.add(user_role)
    
    session.commit()
    logger.info(f'超级管理员账号已就绪。登录邮箱: {admin_email}, 初始密码: {default_password}')


def main():
    """RBAC 初始化脚本主入口。"""
    logger.info('开始执行 RBAC 初始化流程...')
    
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        init_permissions(session)
        init_roles(session)
        create_super_admin(session)
        logger.info('✅ RBAC 初始化已成功完成！')
    except Exception as e:
        session.rollback()
        logger.error(f'RBAC 脚本执行失败: {e}')
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()