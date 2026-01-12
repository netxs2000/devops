"""初始化系统演示用 OKR 数据。

本脚本为不同层级的部门和负责人创建 OKR (Objectives and Key Results)：
1. 公司/体系级：侧重效能透明度与成本控制。
2. 中心级（以财政研发中心为例）：侧重产品稳定交付与卓越工程习惯。
3. 团队级：侧重具体的工程指标提升。

执行方式:
    python scripts/init_okrs.py
"""

import logging
import os
import sys
from typing import List, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import Base, User, Organization, OKRObjective, OKRKeyResult

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitOKR')

# OKR 数据定义 (目标标题, 目标描述, 组织名称, 负责人姓名, 周期, 关键结果列表)
OKR_DATA = [
    (
        "提升研发全链路成本透明度与投入产出比",
        "通过 MDM 平台实现人力、资源、合同成本的自动化挂接，支撑经营决策。",
        "研发体系", "贾志涛", "2024-Q1",
        [
            ("核心产品研发成本自动核算覆盖率", 100, 60, "%"),
            ("产品间人效投入对比偏差度降至", 10, 25, "%"),
        ]
    ),
    (
        "打造预算一体化产品卓越工程实践与稳定交付",
        "确保江苏、通用、浙江等核心版本的平滑迭代与高质量交付。",
        "财政研发中心", "贾志涛", "2024-Q1",
        [
            ("核心业务模块接口测试自动化率提升至", 80, 45, "%"),
            ("生产环境 MTTR (平均故障恢复时间) 缩短", 30, 0, "%"),
            ("完成 3 个省份版本的功能平移与验收", 3, 1, "个"),
        ]
    ),
    (
        "中台框架部技术基座升级与提效",
        "通过组件化和服务化，降低业务部门对接成本。",
        "中台框架部", "刘天阳", "2024-Q1",
        [
            ("中台通用 UI 组件二次开发成本降低", 20, 5, "%"),
            ("支撑 10+ 业务模块完成框架 3.0 迁移", 10, 4, "个"),
        ]
    ),
    (
        "构建数智化产品核心竞争力",
        "提升大数据与 AI 产品的业务价值体现。",
        "大数据及AI业务拓展中心", "张兵", "2024-Q1",
        [
            ("完成数智化通用报表 2.0 版本发布", 1, 0, "个"),
            ("核心模型识别准确率提升至", 95, 88, "%"),
        ]
    ),
]

def init_okrs():
    """解析定义并初始化 OKR 记录。"""
    engine = create_engine(settings.database.uri)
    
    # 强制清理并重建 OKR 相关表，以应用新的字段定义
    logger.info('正在刷新 OKR 表结构...')
    OKRKeyResult.__table__.drop(engine, checkfirst=True)
    OKRObjective.__table__.drop(engine, checkfirst=True)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        logger.info('开始同步演示 OKR 数据...')
        
        for o_title, o_desc, org_name, owner_name, period, krs in OKR_DATA:
            # 1. 查找组织和负责人
            org = session.query(Organization).filter(Organization.org_name == org_name).first()
            owner = session.query(User).filter(User.full_name == owner_name).first()
            
            if not org or not owner:
                logger.warning(f"跳过 OKR '{o_title}'：未找到组织 {org_name} 或负责人 {owner_name}")
                continue
            
            # 2. 创建/更新 Objective
            obj = session.query(OKRObjective).filter_by(title=o_title, period=period).first()
            if not obj:
                obj = OKRObjective(
                    objective_id=f"OBJ-{org_name[:2]}-{period[-2:]}-{owner_name[:2]}",
                    title=o_title,
                    description=o_desc,
                    period=period,
                    owner_id=owner.global_user_id,
                    org_id=org.org_id,
                    status='ACTIVE'
                )
                session.add(obj)
                session.flush() # 获取 obj.id
            
            # 3. 创建/更新 Key Results
            for kr_title, target, current, unit in krs:
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
            
            # 更新 Objective 总进度 (简单加权平均)
            total_progress = sum([k.progress for k in obj.key_results]) / len(obj.key_results) if obj.key_results else 0
            obj.progress = round(total_progress, 2)

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
