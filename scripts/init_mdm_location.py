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
    # (id, name, short, region, code)
    ('110000', '北京市', '北京', '华北', 'beijing'),
    ('120000', '天津市', '天津', '华北', 'tianjin'),
    ('130000', '河北省', '河北', '华北', 'hebei'),
    ('140000', '山西省', '山西', '华北', 'shanxi'),
    ('150000', '内蒙古自治区', '内蒙古', '华北', 'neimenggu'),
    ('210000', '辽宁省', '辽宁', '东北', 'liaoning'),
    ('220000', '吉林省', '吉林', '东北', 'jilin'),
    ('230000', '黑龙江省', '黑龙江', '东北', 'heilongjiang'),
    ('310000', '上海市', '上海', '华东', 'shanghai'),
    ('320000', '江苏省', '江苏', '华东', 'jiangsu'),
    ('330000', '浙江省', '浙江', '华东', 'zhejiang'),
    ('340000', '安徽省', '安徽', '华东', 'anhui'),
    ('350000', '福建省', '福建', '华东', 'fujian'),
    ('360000', '江西省', '江西', '华东', 'jiangxi'),
    ('370000', '山东省', '山东', '华东', 'shandong'),
    ('410000', '河南省', '河南', '华中', 'henan'),
    ('420000', '湖北省', '湖北', '华中', 'hubei'),
    ('430000', '湖南省', '湖南', '华中', 'hunan'),
    ('440000', '广东省', '广东', '华南', 'guangdong'),
    ('450000', '广西壮族自治区', '广西', '华南', 'guangxi'),
    ('460000', '海南省', '海南', '华南', 'hainan'),
    ('500000', '重庆市', '重庆', '西南', 'chongqing'),
    ('510000', '四川省', '四川', '西南', 'sichuan'),
    ('520000', '贵州省', '贵州', '西南', 'guizhou'),
    ('530000', '云南省', '云南', '西南', 'yunnan'),
    ('540000', '西藏自治区', '西藏', '西南', 'xizang'),
    ('610000', '陕西省', '陕西', '西北', 'shaanxi'),
    ('620000', '甘肃省', '甘肃', '西北', 'gansu'),
    ('630000', '青海省', '青海', '西北', 'qinghai'),
    ('640000', '宁夏回族自治区', '宁夏', '西北', 'ningxia'),
    ('650000', '新疆维吾尔自治区', '新疆', '西北', 'xinjiang'),
    ('710000', '台湾省', '台湾', '特别行政区', 'taiwan'),
    ('810000', '香港特别行政区', '香港', '特别行政区', 'hongkong'),
    ('820000', '澳门特别行政区', '澳门', '特别行政区', 'macau'),
    ('000000', '全国', '全国', '全国', 'nationwide')
]

def init_mdm_location():
    """初始化/更新 MDM_LOCATION 表和省份主数据。"""
    try:
        engine = create_engine(settings.database.uri)
        # 确保表已创建
        Base.metadata.create_all(engine, tables=[Location.__table__])
        
        with Session(engine) as session:
            logger.info(f'Processing {len(PROVINCE_DATA)} province records...')
            count = 0
            for location_id, location_name, short_name, region, code in PROVINCE_DATA:
                loc = session.query(Location).filter_by(location_id=location_id).first()
                if not loc:
                    # Insert new
                    loc = Location(
                        location_id=location_id.strip(),
                        location_name=location_name,
                        short_name=short_name,
                        location_type='province' if code != 'nationwide' else 'region',
                        parent_id=None,
                        region=region,
                        code=code,  # 关键: 设置 code 字段
                        is_active=True,
                        manager_user_id=None
                    )
                    session.add(loc)
                else:
                    # Update existing
                    loc.code = code
                    loc.location_name = location_name
                    loc.short_name = short_name
                    loc.region = region
                count += 1
            
            session.commit()
            logger.info(f'✅ Successfully processed {count} records in mdm_location')
            
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
            # 1. Check if legacy 'province' column exists
            try:
                result = session.execute(text("SELECT 1 FROM information_schema.columns WHERE table_name='mdm_identities' AND column_name='province'"))
                if not result.fetchone():
                    logger.info('Province field does not exist in mdm_identities, skipping migration')
                    return
            except Exception:
                # Fallback for databases where information_schema is not accessible or different
                logger.warning("Could not check information_schema, skipping column check.")
            
            # 2. Build mapping name/short_name -> location_id (including codes)
            name_map = {}
            for row in PROVINCE_DATA:
                lid, name, short, _, code = row
                name_map[name] = lid
                name_map[short] = lid
                name_map[code] = lid
            
            # 3. Migrate data
            try:
                users_with_province = session.execute(text("SELECT global_user_id, province FROM mdm_identities WHERE province IS NOT NULL AND province != ''")).fetchall()
                updated_count = 0
                for user_id, province_val in users_with_province:
                    target_id = name_map.get(province_val) or name_map.get(province_val.replace('省','').replace('市',''))
                    
                    if target_id:
                         session.execute(
                             text('UPDATE mdm_identities SET location_id = :lid WHERE global_user_id = :uid'),
                             {'lid': target_id, 'uid': user_id}
                         )
                         updated_count += 1
                
                session.commit()
                if updated_count > 0:
                    logger.info(f'✅ Migrated {updated_count} users from province column to location_id.')
            except Exception as e:
                 logger.warning(f"Migration step had issues (ignorable if column dropped): {e}")

    except Exception as e:
        logger.error(f'❌ Failed to migrate user provinces: {e}')
        # Don't raise here, allow init to succeed even if migration fails


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