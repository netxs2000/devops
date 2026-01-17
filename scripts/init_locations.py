"""初始化地理位置主数据 (mdm_locations)

本脚本用于初始化中国各省、自治区、直辖市及部分特别行政区的地理位置数据，
以便在提交需求、Bug 时进行地域归属标记。

数据来源参考: ISO 3166-2:CN 及常见业务定义。
对应 GitLab Template: .gitlab/issue_templates/Bug.md 中的 `province::xxx` 标签。
"""
import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, Location
from config import Config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_locations():
    """初始化位置数据"""
    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 定义预置数据
    # location_id: 建议使用 UUID 或标准编码，这里使用简码作为唯一标识
    # code: 对应 Issue Template 中的标签后缀 (e.g., province::guangdong -> guangdong)
    locations_data = [
        # --- 特殊位置 ---
        {
            "location_id": "LOC-NATIONWIDE",
            "code": "nationwide",
            "location_name": "全国",
            "short_name": "全国",
            "location_type": "region",
            "region": "全国",
            "parent_id": None
        },
        
        # --- 直辖市 ---
        {"code": "beijing", "name": "北京市", "short": "北京", "region": "华北"},
        {"code": "shanghai", "name": "上海市", "short": "上海", "region": "华东"},
        {"code": "tianjin", "name": "天津市", "short": "天津", "region": "华北"},
        {"code": "chongqing", "name": "重庆市", "short": "重庆", "region": "西南"},

        # --- 省份 ---
        {"code": "anhui", "name": "安徽省", "short": "安徽", "region": "华东"},
        {"code": "fujian", "name": "福建省", "short": "福建", "region": "华东"},
        {"code": "gansu", "name": "甘肃省", "short": "甘肃", "region": "西北"},
        {"code": "guangdong", "name": "广东省", "short": "广东", "region": "华南"},
        {"code": "guizhou", "name": "贵州省", "short": "贵州", "region": "西南"},
        {"code": "hainan", "name": "海南省", "short": "海南", "region": "华南"},
        {"code": "hebei", "name": "河北省", "short": "河北", "region": "华北"},
        {"code": "henan", "name": "河南省", "short": "河南", "region": "华中"},
        {"code": "heilongjiang", "name": "黑龙江省", "short": "黑龙江", "region": "东北"},
        {"code": "hubei", "name": "湖北省", "short": "湖北", "region": "华中"},
        {"code": "hunan", "name": "湖南省", "short": "湖南", "region": "华中"},
        {"code": "jilin", "name": "吉林省", "short": "吉林", "region": "东北"},
        {"code": "jiangsu", "name": "江苏省", "short": "江苏", "region": "华东"},
        {"code": "jiangxi", "name": "江西省", "short": "江西", "region": "华东"},
        {"code": "liaoning", "name": "辽宁省", "short": "辽宁", "region": "东北"},
        {"code": "qinghai", "name": "青海省", "short": "青海", "region": "西北"},
        {"code": "shaanxi", "name": "陕西省", "short": "陕西", "region": "西北"},
        {"code": "shandong", "name": "山东省", "short": "山东", "region": "华东"},
        {"code": "shanxi", "name": "山西省", "short": "山西", "region": "华北"},
        {"code": "sichuan", "name": "四川省", "short": "四川", "region": "西南"},
        {"code": "yunnan", "name": "云南省", "short": "云南", "region": "西南"},
        {"code": "zhejiang", "name": "浙江省", "short": "浙江", "region": "华东"},

        # --- 自治区 ---
        {"code": "guangxi", "name": "广西壮族自治区", "short": "广西", "region": "华南"},
        {"code": "neimenggu", "name": "内蒙古自治区", "short": "内蒙古", "region": "华北"},
        {"code": "ningxia", "name": "宁夏回族自治区", "short": "宁夏", "region": "西北"},
        {"code": "xinjiang", "name": "新疆维吾尔自治区", "short": "新疆", "region": "西北"},
        {"code": "xizang", "name": "西藏自治区", "short": "西藏", "region": "西南"},

        # --- 特别行政区 (可选) ---
        {"code": "hongkong", "name": "香港特别行政区", "short": "香港", "region": "华南"},
        {"code": "macau", "name": "澳门特别行政区", "short": "澳门", "region": "华南"},
        {"code": "taiwan", "name": "台湾省", "short": "台湾", "region": "华东"},
    ]

    try:
        count = 0
        for item in locations_data:
            # 处理数据格式差异
            if 'location_id' in item:
                # 已完整定义的形式 (Nationwide)
                match_code = item['code']
                data_dict = item
            else:
                # 简写形式 (需转换)
                match_code = item['code']
                data_dict = {
                    "location_id": f"LOC-{match_code.upper()}",
                    "code": match_code,
                    "location_name": item['name'],
                    "short_name": item['short'],
                    "location_type": "province",
                    "region": item['region'],
                    "parent_id": "LOC-NATIONWIDE"
                }

            # 检查是否存在
            exists = session.query(Location).filter_by(code=match_code).first()
            if exists:
                logger.info(f"更新已有位置: {data_dict['location_name']}")
                for k, v in data_dict.items():
                    setattr(exists, k, v)
            else:
                logger.info(f"新增位置: {data_dict['location_name']}")
                new_loc = Location(**data_dict)
                session.add(new_loc)
            count += 1

        session.commit()
        logger.info(f"位置主数据初始化完成，共处理 {count} 条记录。")

    except Exception as e:
        session.rollback()
        logger.error(f"初始化失败: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    init_locations()
