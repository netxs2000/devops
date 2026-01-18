"""初始化禅道 (ZenTao) 身份映射 (Identity Mapping) 数据。

本脚本读取 docs/zentao-user.csv，并将禅道账号对齐到 MDM 系统中的 User。
由于禅道 CSV 包含工号，对齐准确度极高。

执行方式:
    python scripts/init_zentao_mappings.py
"""

import csv
import logging
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import Base, User, IdentityMapping

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitZenTaoMapping')

CSV_FILE = 'docs/zentao-user.csv'

def init_zentao_mappings():
    """解析 CSV 并创建身份映射。"""
    engine = create_engine(settings.database.uri)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        if not os.path.exists(CSV_FILE):
            logger.error(f"找不到禅道用户 CSV 文件: {CSV_FILE}")
            return

        logger.info('开始同步禅道身份映射数据...')
        
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                employee_id = row.get('工号', '').strip()
                full_name = row.get('姓名', '').strip()
                email = row.get('邮箱', '').strip()
                account = email.split('@')[0] if email else None # 禅道账号通常是邮箱前缀
                
                if not employee_id and not email:
                    continue

                user = None
                match_method = None
                
                # 1. 优先通过工号匹配 (最高优先级)
                if employee_id:
                    user = session.query(User).filter(
                        User.employee_id == employee_id, 
                        User.is_current == True
                    ).first()
                    if user:
                        match_method = 'EMPLOYEE_ID'
                        # 验证邮箱是否一致
                        if email and user.primary_email and email.lower() != user.primary_email:
                            logger.warning(f"禅道用户 '{full_name}'({employee_id}) 邮箱不一致: "
                                         f"禅道={email}, 主数据={user.primary_email}")
                
                # 2. 其次通过 Email 匹配
                if not user and email:
                    user = session.query(User).filter(
                        User.primary_email == email.lower(), 
                        User.is_current == True
                    ).first()
                    if user:
                        match_method = 'EMAIL'
                        # 验证工号是否一致
                        if employee_id and user.employee_id and employee_id != user.employee_id:
                            logger.warning(f"禅道用户 '{full_name}' 工号不一致: "
                                         f"禅道={employee_id}, 主数据={user.employee_id}")

                if not user:
                    logger.warning(f"无法为禅道用户 '{full_name}' ({employee_id}) 找到对应主数据，跳过。")
                    continue

                # 3. 创建映射记录
                # 禅道中外部系统账号通常标识为邮箱前缀
                external_id = account or email.lower()
                
                mapping = session.query(IdentityMapping).filter_by(
                    source_system='zentao',
                    external_user_id=external_id
                ).first()

                if not mapping:
                    mapping = IdentityMapping(
                        global_user_id=user.global_user_id,
                        source_system='zentao',
                        external_user_id=external_id,
                        external_username=full_name,
                        external_email=email.lower() if email else None,
                        mapping_status='VERIFIED',
                        confidence_score=1.0
                    )
                    session.add(mapping)
                    logger.info(f"建立禅道关联 [{match_method}]: {user.full_name}({user.employee_id}) -> {external_id}")
                    count += 1
                else:
                    mapping.global_user_id = user.global_user_id
                    mapping.mapping_status = 'VERIFIED'
                    mapping.confidence_score = 1.0

            session.commit()
            logger.info(f"禅道身份映射初始化完成! 共建立/更新 {count} 条关联。")

    except Exception as e:
        session.rollback()
        logger.error(f"禅道映射初始化失败: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    init_zentao_mappings()
