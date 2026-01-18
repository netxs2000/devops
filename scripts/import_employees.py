"""导入全量员工信息并关联组织架构。

本脚本从 CSV 文件导入员工数据，自动完成以下任务：
1. 为每位员工创建全局唯一的 Identity (User)。
2. 将员工关联到其所属的中心/部门。
3. 自动生成符合规范的拼音邮箱。

执行方式:
    python scripts/import_employees.py
"""
import sys
import os
import logging
import uuid
import csv
import pypinyin
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, User, Organization

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = Path(__file__).parent.parent / 'docs' / 'employees.csv'

def to_pinyin(name):
    """将中文姓名转换为拼音（全拼，无空格）。"""
    return "".join(pypinyin.lazy_pinyin(name))

def get_org_id(center, dept):
    """根据中心和部门名称推断组织 ID。"""
    # 逻辑：优先匹配部门 DEP-，如果部门名等于中心名，使用 CTR-，否则使用 DEP-
    if not dept or dept == center:
        return f"CTR-{center}"
    return f"DEP-{dept}"

def import_employees():
    """从 CSV 导入员工数据。"""
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    
    csv_path = Path(CSV_FILE)
    if not csv_path.exists():
        logger.error(f"CSV 文件未找到: {csv_path}")
        return

    with Session(engine) as session, open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        logger.info('开始从 CSV 导入员工数据...')
        
        count = 0
        for row in reader:
            name = row.get('姓名', '').strip()
            employee_id = row.get('工号', '').strip()
            center = row.get('中心', '').strip()
            dept = row.get('部门', '').strip()
            position = row.get('职位', '').strip()
            csv_email = row.get('邮箱', '').strip()
            
            if not name or not employee_id:
                continue
            
            # 1. 确定邮箱和用户名 (优先使用 CSV)
            if csv_email:
                email = csv_email.lower().strip()
                username = email.split('@')[0]
            else:
                username = to_pinyin(name)
                email = f"{username}@tjhq.com"
            
            # 2. 查找所属组织
            org_id = get_org_id(center, dept)
            org = session.query(Organization).filter_by(org_id=org_id).first()
            if not org:
                # 尝试通过 org_name 匹配
                org = session.query(Organization).filter(Organization.org_name == dept).first()
                if not org:
                    org = session.query(Organization).filter(Organization.org_name == center).first()
            
            final_org_id = org.org_id if org else None
            
            # 3. 创建或更新用户
            user = session.query(User).filter_by(employee_id=employee_id).first()
            
            if not user:
                # 如果工号不存在，尝试通过邮箱找（处理工号变更但邮箱未变的情况）
                user = session.query(User).filter_by(primary_email=email).first()
            
            if not user:
                user = User(
                    global_user_id=uuid.uuid4(),
                    employee_id=employee_id,
                    username=username,
                    full_name=name,
                    primary_email=email,
                    department_id=final_org_id,
                    position=position,
                    is_active=True,
                    is_survivor=True,
                    sync_version=1,
                    is_current=True
                )
                session.add(user)
                logger.info(f"创建新员工: {name} ({employee_id})")
            else:
                # 严格更新现有数据对齐主数据
                user.employee_id = employee_id
                user.full_name = name
                user.primary_email = email
                user.department_id = final_org_id
                user.position = position
                user.is_active = True
                user.is_current = True
                logger.debug(f"更新员工信息: {name} ({employee_id})")
            
            count += 1
            if count % 100 == 0:
                session.flush() # 定期刷新
                logger.info(f"已处理 {count} 条记录...")
        
        session.commit()
        logger.info(f"✅ 员工导入已完成！共处理 {count} 条记录。")

if __name__ == '__main__':
    import_employees()
