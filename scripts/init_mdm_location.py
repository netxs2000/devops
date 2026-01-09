"""创建 MDM_LOCATION 表并初始化省份主数据。

本脚本执行以下操作:
1. 创建 mdm_location 表（地理位置主数据）
2. 初始化中国省级行政区划数据（含经济大区分类）
3. 创建用户地理位置映射（兼容历史 province 字段数据）

执行方式:
    python scripts/init_mdm_location.py
"""
import sys
import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, Location

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROVINCE_DATA = [
    ('110000', '北京市', '北京', '华北'),
    ('120000', '天津市', '天津', '华北'),
    ('130000', '河北省', '河北', '华北'),
    ('140000', '山西省', '山西', '华北'),
    ('150000', '内蒙古自治区', '内蒙古', '华北'),
    ('210000', '辽宁省', '辽宁', '东北'),
    ('220000', '吉林省', '吉林', '东北'),
    ('230000', '黑龙江省', '黑龙江', '东北'),
    ('310000', '上海市', '上海', '华东'),
    ('320000', '江苏省', '江苏', '华东'),
    ('330000', '浙江省', '浙江', '华东'),
    ('340000', '安徽省', '安徽', '华东'),
    ('350000', '福建省', '福建', '华东'),
    ('360000', '江西省', '江西', '华东'),
    ('370000', '山东省', '山东', '华东'),
    ('410000', '河南省', '河南', '华中'),
    ('420000', '湖北省', '湖北', '华中'),
    ('430000', '湖南省', '湖南', '华中'),
    ('440000', '广东省', '广东', '华南'),
    ('450000', '广西壮族自治区', '广西', '华南'),
    ('460000', '海南省', '海南', '华南'),
    ('500000', '重庆市', '重庆', '西南'),
    ('510000', '四川省', '四川', '西南'),
    ('520000', '贵州省', '贵州', '西南'),
    ('530000', '云南省', '云南', '西南'),
    ('540000', '西藏自治区', '西藏', '西南'),
    ('610000', '陕西省', '陕西', '西北'),
    ('620000', '甘肃省', '甘肃', '西北'),
    ('630000', '青海省', '青海', '西北'),
    ('640000', '宁夏回族自治区', '宁夏', '西北'),
    ('650000', '新疆维吾尔自治区', '新疆', '西北'),
    ('710000', '台湾省', '台湾', '特别行政区'),
    ('810000', '香港特别行政区', '香港', '特别行政区'),
    ('820000', '澳门特别行政区', '澳门', '特别行政区'),
    ('000000', '全国', '全国', '全国')
]

PROVINCE_MAPPING = {
    'nationwide': '000000', '全国': '000000',
    'beijing': '110000', '北京': '110000',
    'tianjin': '120000', '天津': '120000',
    'hebei': '130000', '河北': '130000',
    'shanxi': '140000', '山西': '140000',
    'neimenggu': '150000', '内蒙古': '150000',
    'liaoning': '210000', '辽宁': '210000',
    'jilin': '220000', '吉林': '220000',
    'heilongjiang': '230000', '黑龙江': '230000',
    'shanghai': '310000', '上海': '310000',
    'jiangsu': '320000', '江苏': '320000',
    'zhejiang': '330000', '浙江': '330000',
    'anhui': '340000', '安徽': '340000',
    'fujian': '350000', '福建': '350000',
    'jiangxi': '360000', '江西': '360000',
    'shandong': '370000', '山东': '370000',
    'henan': '410000', '河南': '410000',
    'hubei': '420000', '湖北': '420000',
    'hunan': '430000', '湖南': '430000',
    'guangdong': '440000', '广东': '440000',
    'guangxi': '450000', '广西': '450000',
    'hainan': '460000', '海南': '460000',
    'chongqing': '500000', '重庆': '500000',
    'sichuan': '510000', '四川': '510000',
    'guizhou': '520000', '贵州': '520000',
    'yunnan': '530000', '云南': '530000',
    'xizang': '540000', '西藏': '540000',
    'shaanxi': '610000', '陕西': '610000',
    'gansu': '620000', '甘肃': '620000',
    'qinghai': '630000', '青海': '630000',
    'ningxia': '640000', '宁夏': '640000',
    'xinjiang': '650000', '新疆': '650000'
}

def init_mdm_location():
    """初始化 MDM_LOCATION 表和省份主数据。"""
    try:
        engine = create_engine(settings.database.uri)
        logger.info('Creating mdm_location table...')
        Base.metadata.create_all(engine, tables=[Location.__table__])
        
        with Session(engine) as session:
            existing_count = session.query(Location).count()
            if existing_count > 0:
                logger.warning(f'mdm_location table already has {existing_count} records. Skipping initialization.')
                return
            
            logger.info(f'Inserting {len(PROVINCE_DATA)} province records...')
            for location_id, location_name, short_name, region in PROVINCE_DATA:
                location = Location(
                    location_id=location_id.strip(),
                    location_name=location_name,
                    short_name=short_name,
                    location_type='province',
                    parent_id=None,
                    region=region,
                    is_active=True,
                    manager_user_id=None
                )
                session.add(location)
            session.commit()
            logger.info(f'✅ Successfully initialized {len(PROVINCE_DATA)} province records in mdm_location')
            
            logger.info('\n📊 区域分布统计:')
            regions = session.execute(text('SELECT region, COUNT(*) as count FROM mdm_locations GROUP BY region ORDER BY count DESC')).fetchall()
            for row in regions:
                logger.info(f'  - {row[0]}: {row[1]} 个省份')
        
        logger.info('\n✅ MDM_LOCATION table initialization completed!')
    except Exception as e:
        logger.error(f'❌ Failed to initialize mdm_location: {e}')
        raise

def migrate_user_province_to_location():
    """迁移现有 User 表的 province 字段到 location_id。"""
    try:
        engine = create_engine(settings.database.uri)
        with Session(engine) as session:
            result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='mdm_identities' AND column_name='province'"))
            if not result.fetchone():
                logger.info('Province field does not exist in mdm_identities, skipping migration')
                return
                
            result = session.execute(text("SELECT global_user_id, province FROM mdm_identities WHERE province IS NOT NULL AND province != ''"))
            updated_count = 0
            skipped_count = 0
            for row in result:
                user_id, province_value = row
                location_id = PROVINCE_MAPPING.get(province_value.lower())
                if not location_id:
                    logger.warning(f"Unknown province value '{province_value}' for user {user_id}, skipping")
                    skipped_count += 1
                    continue
                session.execute(text('UPDATE mdm_identities SET location_id = :location_id WHERE global_user_id = :user_id'), {'location_id': location_id, 'user_id': user_id})
                updated_count += 1
            session.commit()
            logger.info(f'\n✅ Migration completed: Updated: {updated_count}, Skipped: {skipped_count}')
    except Exception as e:
        logger.error(f'❌ Failed to migrate province to location_id: {e}')
        raise

if __name__ == '__main__':
    logger.info('=' * 60)
    logger.info('MDM_LOCATION 表初始化脚本')
    logger.info('=' * 60)
    init_mdm_location()
    logger.info('\n' + '=' * 60)
    logger.info('开始迁移历史province数据...')
    logger.info('=' * 60)
    migrate_user_province_to_location()
    logger.info('\n🎉 All tasks completed successfully!')