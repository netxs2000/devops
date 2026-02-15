"""初始化系统 OKR 数据。

重构说明：已移除所有硬编码 OKR_DATA，改为从 docs/okrs.csv 动态加载。
"""
import logging
import os
import sys
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import Base, User, Organization, OKRObjective, OKRKeyResult
from scripts.utils import build_user_indexes, resolve_user

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitOKR')

CSV_FILE = os.path.join('docs', 'okrs.csv')

def init_okrs():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        if not os.path.exists(CSV_FILE):
            logger.warning(f"跳过 OKR 初始化：未找到 {CSV_FILE}")
            return

        logger.info(f'开始从 {CSV_FILE} 同步 OKR 数据...')
        
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            # 记录已处理的 Objective，避免重复创建
            processed_objectives = {}
            
            # 预加载用户索引 (邮箱 + 姓名)
            email_idx, name_idx = build_user_indexes(session)
            # 同时建立 user_id -> User 对象索引 (用于后续取 global_user_id)
            all_users_map = {u.global_user_id: u for u in session.query(User).filter_by(is_current=True).all()}

            for row in reader:
                o_title = row['目标标题'].strip()
                o_desc = row['目标描述'].strip()
                org_name = row['组织名称'].strip()
                owner_val = row.get('负责人', row.get('负责人邮箱', '')).strip()
                period = row['周期'].strip()
                kr_title = row['关键结果标题'].strip()
                target = float(row['目标值'])
                current = float(row['当前值'])
                unit = row['单位'].strip()

                # 1. 查找组织和负责人
                org = session.query(Organization).filter(Organization.org_name == org_name).first()
                owner_id = resolve_user(owner_val, email_idx, name_idx, '负责人')
                
                if not org or not owner_id:
                    logger.warning(f"跳过 KR '{kr_title}'：未找到组织 {org_name} 或负责人 {owner_val}")
                    continue
                
                # 2. 获取或创建 Objective
                obj_key = (o_title, period, org.org_id)
                if obj_key not in processed_objectives:
                    obj = session.query(OKRObjective).filter_by(title=o_title, period=period, org_id=org.org_id).first()
                    if not obj:
                        obj = OKRObjective(
                            objective_id=f"OBJ-{period}-{hash(o_title) % 10000}",
                            title=o_title,
                            description=o_desc,
                            period=period,
                            owner_id=owner_id,
                            org_id=org.org_id,
                            status='ACTIVE'
                        )
                        session.add(obj)
                        session.flush()
                    processed_objectives[obj_key] = obj
                else:
                    obj = processed_objectives[obj_key]

                # 3. 创建/更新 Key Results
                kr = session.query(OKRKeyResult).filter_by(objective_id=obj.id, title=kr_title).first()
                # 进度对齐模型定义 (0.0 - 1.0)
                progress = round(current / target, 4) if target > 0 else 0.0
                
                if not kr:
                    kr = OKRKeyResult(
                        objective_id=obj.id,
                        title=kr_title,
                        target_value=target,
                        current_value=current,
                        unit=unit,
                        owner_id=owner_id,
                        progress=progress
                    )
                    session.add(kr)
                else:
                    kr.current_value = current
                    kr.progress = progress

        session.commit()
        logger.info('✅ OKR 数据初始化完成！')
        
    except Exception as e:
        session.rollback()
        logger.error(f"OKR 初始化失败: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    init_okrs()
