"""初始化 GitLab 身份映射 (Identity Mapping) 数据。

本脚本读取 docs/gitlab-user.csv，并将 GitLab 用户 ID 和用户名关联到 MDM 系统中的 User。
通过姓名匹配来实现全链路身份对齐。

执行方式:
    python scripts/init_gitlab_mappings.py
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
logger = logging.getLogger('InitGitLabMapping')

CSV_FILE = 'docs/gitlab-user.csv'

def init_gitlab_mappings():
    """解析 CSV 并创建身份映射。"""
    engine = create_engine(settings.database.uri)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        if not os.path.exists(CSV_FILE):
            logger.error(f"找不到 GitLab 用户 CSV 文件: {CSV_FILE}")
            return

        logger.info('开始同步 GitLab 身份映射数据...')
        
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                gitlab_id = row.get('GITLAB ID', '').strip()
                username = row.get('username', '').strip()
                full_name = row.get('Full name', '').strip()
                
                if not gitlab_id or not username or not full_name:
                    continue

                # 1. 查找 MDM 系统中的 User (按全名匹配)
                user = session.query(User).filter(User.full_name == full_name, User.is_current == True).first()
                if not user:
                    logger.info(f"未匹配: '{full_name}'")
                    continue

                # 2. 创建或更新 IdentityMapping
                mapping = session.query(IdentityMapping).filter_by(
                    source_system='gitlab',
                    external_user_id=gitlab_id
                ).first()

                if not mapping:
                    mapping = IdentityMapping(
                        global_user_id=user.global_user_id,
                        source_system='gitlab',
                        external_user_id=gitlab_id,
                        external_username=username,
                        mapping_status='VERIFIED',
                        confidence_score=1.0
                    )
                    session.add(mapping)
                    logger.info(f"建立关联: {full_name} -> GitLab({username})")
                    count += 1
                else:
                    mapping.global_user_id = user.global_user_id
                    mapping.external_username = username

            session.commit()
            logger.info(f"✅ GitLab 身份映射初始化完成！共建立 {count} 条关联。")

    except Exception as e:
        session.rollback()
        logger.error(f"GitLab 映射初始化失败: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    init_gitlab_mappings()
