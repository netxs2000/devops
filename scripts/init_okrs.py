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

            for row in reader:
                o_title = row['目标标题'].strip()
                o_desc = row['目标描述'].strip()
                org_name = row['组织名称'].strip()
                owner_name = row['负责人姓名'].strip()
                period = row['周期'].strip()
                kr_title = row['关键结果标题'].strip()
                target = float(row['目标值'])
                current = float(row['当前值'])
                unit = row['单位'].strip()

                # 1. 查找组织和负责人
                org = session.query(Organization).filter(Organization.org_name == org_name).first()
                owner = session.query(User).filter(User.full_name == owner_name).first()
                
                if not org or not owner:
                    logger.warning(f"跳过 KR '{kr_title}'：未找到组织 {org_name} 或负责人 {owner_name}")
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
                            owner_id=owner.global_user_id,
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
                progress = round((current / target) * 100, 2) if target > 0 else 0
                
                if not kr:
                    kr = OKRKeyResult(
                        objective_id=obj.id,
                        title=kr_title,
                        target_value=target,
                        current_value=current,
                        unit=unit,
                        owner_id=owner.global_user_id,
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
