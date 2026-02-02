"""初始化产品主数据 (MDM_PRODUCT)。

本脚本根据用户提供的产品目录图，自动完成以下任务：
1. 录入全量产品信息（代号、名称、产品线）。
2. 建立产品与所属部门（中心）的关联。

执行方式:
    python scripts/init_products.py
"""
import sys
import os
import logging
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, Product, Organization, User

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 用户姓名 -> 拼音映射 (同步自 init_organizations.py)
USER_NAME_MAP = {
    '王斌': 'wangbin', '刘洪昌': 'liuhongchang', '李水珍': 'lishuizhen',
    '赵孝涛': 'zhaoxiaotao', '张聚锁': 'zhangjusuo', '高明': 'gaoming',
    '蔡道斌': 'caidaobin', '周景伟': 'zhoujingwei', '皎海军': 'jiaohaijun',
    '马世杰': 'mashijie', '杜崇明': 'duchongming', '王海峰': 'wanghaifeng'
}

# 产品原始数据 (产品代号, 产品名称, 归属中心名称, 负责人姓名)
PRODUCT_RAW_DATA = [
    ('PL001', '预算一体化-江苏', '财政研发中心', '王斌'),
    ('PL002', '预算一体化-通用', '财政研发中心', '刘洪昌'),
    ('PL003', '预算一体化-浙江', '财政研发中心', '刘洪昌'),
    ('PL004', '预算一体化-海南', '政务研发中心', '李水珍'),
    ('PL005', '财政绩效', '智慧云政务研发中心', '赵孝涛'),
    ('PL006', '单位核算', '智慧云政务研发中心', '张聚锁'),
    ('PL007', '轻松报', '智慧云政务研发中心', '高明'),
    ('PL008', '涉企分析', '智慧云政务研发中心', '蔡道斌'),
    ('PL009', '项目枢纽', '政务研发中心', '李水珍'),
    ('PL010', '政务', '政务研发中心', '李水珍'),
    ('PL011', '非税', '互联网与协同业务拓展中心', '周景伟'),
    ('PL012', '协同', '互联网与协同业务拓展中心', '皎海军'),
    ('PL013', '大数据', '大数据及AI业务拓展中心', '马世杰'),
    ('PL014', '行业业务', '行业业务拓展中心', '杜崇明'),
    ('PL015', '创新业务', '创新业务拓展中心', '王海峰'),
]

def get_or_create_user(session, name):
    """获取或创建负责人占位账号。"""
    pinyin = USER_NAME_MAP.get(name)
    if not pinyin:
        logger.warning(f"未找到姓名 {name} 的拼音定义，跳过负责人创建。")
        return None
    
    email = f"{pinyin}@tjhq.com"
    user = session.query(User).filter_by(primary_email=email).first()
    if not user:
        user = User(
            global_user_id=uuid.uuid4(),
            username=pinyin,
            full_name=name,
            primary_email=email,
            is_active=True,
            is_survivor=True,
            sync_version=1,
            is_current=True
        )
        session.add(user)
        session.flush()
        logger.info(f"已创建负责人用户: {name} ({email})")
    return user

def init_products():
    """解析数据并初始化产品主数据。"""
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        logger.info('开始初始化全量产品目录...')
        
        for p_id, p_name, owner_name, manager_name in PRODUCT_RAW_DATA:
            # 1. 匹配所属部门 ID
            owner_id = f"CTR-{owner_name}"
            org = session.query(Organization).filter_by(org_id=owner_id).first()
            if not org:
                logger.warning(f"产品 {p_name} 的归属部门 {owner_name} 不存在。")
                owner_id = None
            
            # 2. 获取负责人
            mgr_user = get_or_create_user(session, manager_name)
            
            # 3. 创建/更新产品
            existing = session.query(Product).filter_by(product_id=p_id).first()
            if not existing:
                product = Product(
                    product_id=p_id,

                    product_name=p_name,
                    product_description=f"华青 {p_name} 核心产品",
                    category='Core Product',
                    version_schema='SemVer',
                    lifecycle_status='Active',
                    owner_team_id=owner_id,
                    product_manager_id=mgr_user.global_user_id if mgr_user else None
                )
                session.add(product)
                logger.info(f"已创建产品: {p_name} ({p_id})")
            else:
                existing.product_name = p_name
                existing.owner_team_id = owner_id
                if mgr_user:
                    existing.product_manager_id = mgr_user.global_user_id
                logger.info(f"已更新产品: {p_name}")
        
        session.commit()
        logger.info('✅ 产品目录初始化完成！')

if __name__ == '__main__':
    init_products()
