"""初始化 GitLab 身份映射 (Identity Mapping) 数据。

本脚本读取 docs/gitlab-user.csv，将 GitLab 用户严格按员工主数据对齐。

对齐策略 (Initial Link):
    1. Email 精确匹配 (最高优先级) - 置信度 1.0
    2. 姓名唯一匹配 (降级策略) - 置信度 0.8, 仅在无重名时使用
    3. 无法匹配则跳过，不创建临时用户

执行方式:
    python scripts/init_gitlab_mappings.py
"""

import csv
import logging
import os
import sys
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import Base, User, IdentityMapping

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitGitLabMapping')

CSV_FILE = 'docs/gitlab-user.csv'


def init_gitlab_mappings():
    """解析 CSV 并创建身份映射，严格按员工主数据 Email 对齐。"""
    engine = create_engine(settings.database.uri)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # 统计信息
    stats = defaultdict(int)
    
    try:
        if not os.path.exists(CSV_FILE):
            logger.error(f"找不到 GitLab 用户 CSV 文件: {CSV_FILE}")
            return

        logger.info('=' * 60)
        logger.info('开始 GitLab 身份映射初始化 (Email 优先策略)')
        logger.info('=' * 60)
        
        # 预加载所有员工主数据，按 Email 和姓名建立索引
        all_users = session.query(User).filter(User.is_current == True).all()
        email_index = {u.primary_email.lower(): u for u in all_users if u.primary_email}
        name_index = defaultdict(list)
        for u in all_users:
            if u.full_name:
                name_index[u.full_name].append(u)
        
        logger.info(f"已加载 {len(email_index)} 条员工邮箱索引")
        logger.info(f"已加载 {len(name_index)} 个不同姓名")
        
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                gitlab_id = row.get('GitLab用户ID', '').strip() or row.get('GITLAB ID', '').strip()
                username = row.get('用户名', '').strip() or row.get('username', '').strip()
                full_name = row.get('全名', '').strip() or row.get('Full name', '').strip()
                email = row.get('Email', '').strip().lower()
                
                if not gitlab_id or not username:
                    stats['skipped_invalid'] += 1
                    continue
                
                stats['total'] += 1
                user = None
                match_method = None
                
                # ========================================
                # 策略 1: Email 精确匹配 (最高优先级)
                # ========================================
                if email and email in email_index:
                    user = email_index[email]
                    match_method = 'EMAIL'
                    stats['matched_by_email'] += 1
                
                # ========================================
                # 策略 2: 姓名唯一匹配 (降级策略)
                # ========================================
                if not user and full_name:
                    candidates = name_index.get(full_name, [])
                    if len(candidates) == 1:
                        user = candidates[0]
                        match_method = 'NAME'
                        stats['matched_by_name'] += 1
                        logger.warning(
                            f"[降级] GitLab用户 '{full_name}' "
                            f"Email({email}) 不在主数据中, "
                            f"通过姓名唯一匹配到 {user.primary_email}"
                        )
                    elif len(candidates) > 1:
                        stats['skipped_duplicate_name'] += 1
                        logger.error(
                            f"[跳过] GitLab用户 '{full_name}' ({email}) "
                            f"存在 {len(candidates)} 个重名员工，无法确定映射"
                        )
                        continue
                
                # ========================================
                # 策略 3: 无法匹配，跳过
                # ========================================
                if not user:
                    stats['skipped_no_match'] += 1
                    logger.info(f"[跳过] GitLab用户 '{full_name}' ({email}) 无法匹配主数据")
                    continue
                
                # ========================================
                # 创建或更新 IdentityMapping
                # ========================================
                mapping = session.query(IdentityMapping).filter_by(
                    source_system='gitlab',
                    external_user_id=str(gitlab_id)
                ).first()

                confidence = 1.0 if match_method == 'EMAIL' else 0.8
                
                if not mapping:
                    mapping = IdentityMapping(
                        global_user_id=user.global_user_id,
                        source_system='gitlab',
                        external_user_id=str(gitlab_id),
                        external_username=username,
                        external_email=email if email else None,
                        mapping_status='VERIFIED',
                        confidence_score=confidence
                    )
                    session.add(mapping)
                    stats['created'] += 1
                    logger.info(
                        f"[新建] {user.full_name}({user.employee_id}) -> "
                        f"GitLab:{username} [{match_method}]"
                    )
                else:
                    # 更新现有映射
                    if mapping.global_user_id != user.global_user_id:
                        logger.warning(
                            f"[更新] GitLab用户 {username} 重新关联: "
                            f"{mapping.global_user_id} -> {user.global_user_id}"
                        )
                    mapping.global_user_id = user.global_user_id
                    mapping.external_username = username
                    mapping.external_email = email if email else mapping.external_email
                    mapping.mapping_status = 'VERIFIED'
                    mapping.confidence_score = confidence
                    stats['updated'] += 1

            session.commit()
            
            # 输出统计报告
            logger.info('=' * 60)
            logger.info('GitLab 身份映射初始化完成!')
            logger.info('=' * 60)
            logger.info(f"总处理记录: {stats['total']}")
            logger.info(f"  - Email匹配: {stats['matched_by_email']}")
            logger.info(f"  - 姓名匹配: {stats['matched_by_name']}")
            logger.info(f"  - 新建映射: {stats['created']}")
            logger.info(f"  - 更新映射: {stats['updated']}")
            logger.info(f"跳过记录:")
            logger.info(f"  - 无法匹配: {stats['skipped_no_match']}")
            logger.info(f"  - 重名冲突: {stats['skipped_duplicate_name']}")
            logger.info(f"  - 无效数据: {stats['skipped_invalid']}")

    except Exception as e:
        session.rollback()
        logger.error(f"GitLab 映射初始化失败: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    init_gitlab_mappings()
