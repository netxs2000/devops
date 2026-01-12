"""初始化产品主数据、项目主数据及其关联关系。

本脚本根据用户提供的“产品-部门”映射和“项目-产品”映射图，自动完成以下任务：
1. 创建/更新全量产品 (mdm_product)。
2. 创建/更新全量项目 (mdm_projects)。
3. 建立项目与产品的 1:1 或 N:1 关联关系 (mdm_rel_project_product)。

执行方式:
    python scripts/init_products_projects.py
"""

import logging
import os
import sys
import uuid
from typing import List, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import Base, Organization, Product, ProjectMaster, ProjectProductRelation

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitProductsProjects')

# 产品清单 (产品名称, 所属中心名称)
PRODUCTS_DATA = [
    ('预算一体化-江苏', '财政研发中心'),
    ('预算一体化-通用', '财政研发中心'),
    ('预算一体化-浙江', '财政研发中心'),
    ('创新业务产品', '创新业务拓展中心'),
    ('大数据产品', '大数据及AI业务拓展中心'),
    ('非税', '互联网与协同业务拓展中心'),
    ('协同', '互联网与协同业务拓展中心'),
    ('交通业务', '行业业务拓展中心'),
    ('项目枢纽', '政务研发中心'),
    ('预算一体化-海南', '政务研发中心'),
    ('政务产品', '政务研发中心'),
    ('财政绩效', '智慧云政务研发中心'),
    ('单位核算', '智慧云政务研发中心'),
    ('轻松报', '智慧云政务研发中心'),
    ('涉企分析', '智慧云政务研发中心'),
]

# 项目清单 (项目代号, 项目名称, 所属产品/产线名称, 所属中心名称)
PROJECTS_RAW_DATA = [
    # 预算一体化-江苏
    ('BIM-JS', '基础信息管理-江苏', '预算一体化-江苏', '财政研发中心'),
    ('BDG-JS', '指标调整切换-江苏', '预算一体化-江苏', '财政研发中心'),
    ('PDM-JS', '项目库管理-江苏', '预算一体化-江苏', '财政研发中心'),
    ('BDM-JS', '预算编制-江苏', '预算一体化-江苏', '财政研发中心'),
    ('COMMON-JS', '框架管理-江苏', '预算一体化-江苏', '财政研发中心'),
    ('PORTAL-JS', '门户管理-江苏', '预算一体化-江苏', '财政研发中心'),
    ('GZXMGLXT-JS', '国债项目管理系统-江苏', '预算一体化-江苏', '财政研发中心'),
    ('GBDM-JS', '政府预算-江苏', '预算一体化-江苏', '财政研发中心'),
    
    # 预算一体化-通用
    ('FASP', '中台服务', '预算一体化-通用', '财政研发中心'),
    ('COMMON', '框架管理', '预算一体化-通用', '财政研发中心'),
    ('ESMS', '预算执行监督系统', '预算一体化-通用', '财政研发中心'),
    ('BIM', '基础信息管理', '预算一体化-通用', '财政研发中心'),
    ('PORTAL', '门户管理', '预算一体化-通用', '财政研发中心'),
    ('PDM', '项目库管理', '预算一体化-通用', '财政研发中心'),
    ('BDG', '预算调整和调剂', '预算一体化-通用', '财政研发中心'),
    ('BDM', '预算编制', '预算一体化-通用', '财政研发中心'),
    ('PAY', '国库集中支付', '预算一体化-通用', '财政研发中心'),
    ('GBDM', '政府预算', '预算一体化-通用', '财政研发中心'),
    ('DATACOMMON', '采集组件', '预算一体化-通用', '财政研发中心'),
    ('SALARY', '工资系统', '预算一体化-通用', '财政研发中心'),
    ('REALPAY', '实缴管理', '预算一体化-通用', '财政研发中心'),
    ('DITS', '财政运行监测', '预算一体化-通用', '财政研发中心'),
    ('INSPECT', '动态监控', '预算一体化-通用', '财政研发中心'),
    ('BAMS', '银行账户', '预算一体化-通用', '财政研发中心'),
    ('ACCT', '总会计核算', '预算一体化-通用', '财政研发中心'),
    ('GL', '预算指标账', '预算一体化-通用', '财政研发中心'),
    ('gabn', '国资预算', '预算一体化-通用', '财政研发中心'),
    ('SPEACCT', '专户管理', '预算一体化-通用', '财政研发中心'),
    ('RQREPORT', '打印和会计报表', '预算一体化-通用', '财政研发中心'),
    ('ndpm', '国债项目系统', '预算一体化-通用', '财政研发中心'),
    ('MONITOR', '中台监控', '预算一体化-通用', '财政研发中心'),
    ('DFMS', '直达资金管理', '预算一体化-通用', '财政研发中心'),
    ('CARD', '公务卡系统', '预算一体化-通用', '财政研发中心'),
    ('EXCASH', '国库现金管理系统', '预算一体化-通用', '财政研发中心'),
    ('IFMISAI', '预算管理一体化AI应用', '预算一体化-通用', '财政研发中心'),
    ('RDMS', '资料收发管理系统', '预算一体化-通用', '财政研发中心'),
    ('PLM', '政策库管理', '预算一体化-通用', '财政研发中心'),
    ('HPRS', '项目追踪系统', '预算一体化-通用', '财政研发中心'),
    
    # 预算一体化-浙江 / 海南
    ('PAY-ZJ', '国库集中支付-浙江', '预算一体化-浙江', '财政研发中心'),
    ('CARD-ZJ', '公务卡系统-浙江', '预算一体化-浙江', '财政研发中心'),
    ('BDG-ZJ', '预算调整和调剂-浙江', '预算一体化-浙江', '财政研发中心'),
    ('GFA-DEM-HN', '部门决算-海南', '预算一体化-海南', '政务研发中心'),
    ('GFA-GOM-HN', '财政总决算-海南', '预算一体化-海南', '政务研发中心'),
    ('INEXREPORT-HN', '旬月报系统-海南', '预算一体化-海南', '政务研发中心'),
    ('PERFORMANCE-HN', '绩效-海南', '预算一体化-海南', '政务研发中心'),
    ('REPORT-HN', '综合查询-海南', '预算一体化-海南', '政务研发中心'),
    ('PDM-HN', '项目库-海南', '预算一体化-海南', '政务研发中心'),
    ('BIM-HN', '基础信息-海南', '预算一体化-海南', '政务研发中心'),
    ('BDM-HN', '预算编制-海南', '预算一体化-海南', '政务研发中心'),

    # 创新业务 / 大数据 / 非税
    ('OBS', '预决算公开与分析查询', '创新业务产品', '创新业务拓展中心'),
    ('SI', '社会保险基金预算管理系统', '创新业务产品', '创新业务拓展中心'),
    ('BDBS', '通用业务管理平台', '大数据产品', '大数据及AI业务拓展中心'),
    ('BDP', '大数据平台', '大数据产品', '大数据及AI业务拓展中心'),
    ('HQREPORT', '大数据通用报表系统', '大数据产品', '大数据及AI业务拓展中心'),
    ('FS-SRS_JGL', '非税收入收缴管理系统', '非税', '互联网与协同业务拓展中心'),
    ('CYJF', '财云缴费', '非税', '互联网与协同业务拓展中心'),
    ('FS-CZOZ', '财政管理信息系统', '非税', '互联网与协同业务拓展中心'),
    ('FS-CZPJGLPT', '财政票据管理平台', '非税', '互联网与协同业务拓展中心'),
    ('TC', '易创快速开发平台', '协同', '互联网与协同业务拓展中心'),

    # 行业业务
    ('HY-BUSI', '微服务-业务产品', '交通业务', '行业业务拓展中心'),
    ('TRAFFIC', '普通省道和农村公路“以奖代补”考核数据支撑系统', '交通业务', '行业业务拓展中心'),
    ('LMVS', '链农社', '交通业务', '行业业务拓展中心'),
    ('HY-QK-CHART', '微服务-乾坤图表服务产品', '交通业务', '行业业务拓展中心'),
    ('HY-QK-CK', '微服务-乾坤仓库产品', '交通业务', '行业业务拓展中心'),
    ('HY-ZSK', '微服务-知识库产品', '交通业务', '行业业务拓展中心'),
    ('HY-QK-TABLE', '微服务-乾坤报表服务产品', '交通业务', '行业业务拓展中心'),
    ('HY-ACCESS', '微服务-数据接入产品', '交通业务', '行业业务拓展中心'),
    ('TECH', '科技监管系统', '交通业务', '行业业务拓展中心'),
    ('HY-XQC', '业务范围中心-物资仓库', '交通业务', '行业业务拓展中心'),
    ('HY-WJFW', '微服务-文件服务产品', '交通业务', '行业业务拓展中心'),
    ('HY-JSTX', '微服务-即时通讯产品', '交通业务', '行业业务拓展中心'),
    ('HY-INS', '微服务-监控产品', '交通业务', '行业业务拓展中心'),

    # 政务产品 / 其它
    ('BPDM', '项目枢纽平台', '项目枢纽', '政务研发中心'),
    ('EDUP', '部属高校预算绩效', '政务产品', '政务研发中心'),
    ('DFCZFXPJ', '地方财政分析评价系统', '政务产品', '政务研发中心'),
    ('SALARY-JZXT', '军队转业干部信息管理系统', '政务产品', '政务研发中心'),
    ('YSJL-CZB', '预算管理交流平台', '政务产品', '政务研发中心'),
    ('CLLBDG', '财务项目管理（三级项目管理）', '政务产品', '政务研发中心'),
    ('BUSCOMMON-ZW', '政务框架', '政务产品', '政务研发中心'),
    ('CASH-CZB', '财政部现金管理系统', '政务产品', '政务研发中心'),
    ('INSPECT-CZB', '财政国库动态监控', '政务产品', '政务研发中心'),
    
    # 智慧云政务中心
    ('PMKPI', '预算财政绩效', '财政绩效', '智慧云政务研发中心'),
    ('GLA', '单位会计核算', '单位核算', '智慧云政务研发中心'),
    ('GLA-XJ', '单位会计核算-新疆', '单位核算', '智慧云政务研发中心'),
    ('G-GLA', '单位核算（G版）', '轻松报', '智慧云政务研发中心'),
    ('QSB', '轻松报', '轻松报', '智慧云政务研发中心'), # 新增
    ('ORS', '网上报销2.0', '轻松报', '智慧云政务研发中心'),
    ('INVOICE', '电子智票', '轻松报', '智慧云政务研发中心'),
    ('BGTPM', '项目管理', '轻松报', '智慧云政务研发中心'),
    ('CPAS', '合同管理', '轻松报', '智慧云政务研发中心'),
    ('OFFCAR', '公务用车', '轻松报', '智慧云政务研发中心'),
    ('ORSAPP', '网上报销小程序', '轻松报', '智慧云政务研发中心'),
    ('ASSET', '资产管理', '轻松报', '智慧云政务研发中心'),
    ('GPA', '采购管理', '轻松报', '智慧云政务研发中心'),
    ('BPPF-PJBT', '部门项目预算绩效管理系统', '涉企分析', '智慧云政务研发中心'),
]

def get_org_id(session: Session, center_name: str) -> str:
    """根据中心名称查找对应的 Organization ID。"""
    org = session.query(Organization).filter_by(org_name=center_name, is_current=True).first()
    if org:
        return org.org_id
    # 如果找不到，尝试拼音模式（兜底）
    return f"CTR-{center_name}"

def init_products(session: Session) -> Dict[str, str]:
    """初始化产品主数据。"""
    logger.info('正在初始化产品主数据...')
    name_to_id = {}
    for name, center in PRODUCTS_DATA:
        org_id = get_org_id(session, center)
        # 生成唯一产品 ID (PRD + 姓名缩写/拼音处理，这里简单模拟)
        prod_id = f"PRD-{uuid.uuid5(uuid.NAMESPACE_DNS, name).hex[:8].upper()}"
        
        product = session.query(Product).filter_by(product_name=name).first()
        if not product:
            product = Product(
                product_id=prod_id,
                product_code=prod_id.replace('PRD-', 'P'),
                product_name=name,
                product_description=f"{name} 业务产品线",
                owner_team_id=org_id,
                lifecycle_status='Active',
                version_schema='Semantic'
            )
            session.add(product)
        else:
            product.owner_team_id = org_id
        
        session.flush()
        name_to_id[name] = product.product_id
        
    session.commit()
    return name_to_id

def init_projects(session: Session, prod_name_to_id: Dict[str, str]):
    """初始化项目主数据并关联产品。"""
    logger.info('正在初始化项目主数据及关联关系...')
    
    for code, name, prod_name, center in PROJECTS_RAW_DATA:
        org_id = get_org_id(session, center)
        proj_id = f"PROJ-{code}"
        
        # 1. 创建/更新项目
        project = session.query(ProjectMaster).filter_by(project_id=proj_id).first()
        if not project:
            project = ProjectMaster(
                project_id=proj_id,
                project_name=name,
                project_type='SOFTWARE',
                status='ACTIVE',
                org_id=org_id,
                external_id=code,
                is_active=True,
                is_current=True,
                sync_version=1
            )
            session.add(project)
        else:
            project.project_name = name
            project.org_id = org_id
        
        session.flush()

        # 2. 建立产品关联
        target_prod_id = prod_name_to_id.get(prod_name)
        if target_prod_id:
            rel = session.query(ProjectProductRelation).filter_by(
                project_id=proj_id, product_id=target_prod_id
            ).first()
            if not rel:
                rel = ProjectProductRelation(
                    project_id=proj_id,
                    product_id=target_prod_id,
                    org_id=org_id,
                    relation_type='PRIMARY',
                    allocation_ratio=1.0
                )
                session.add(rel)
        else:
            logger.warning(f"未能为项目 {name} 找到对应的产品线: {prod_name}")

    session.commit()

def main():
    """初始化流程主入口。"""
    logger.info('开始初始化产品与项目数据...')
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        prod_map = init_products(session)
        init_projects(session, prod_map)
        logger.info('✅ 产品与项目初始化已成功完成！')
    except Exception as e:
        session.rollback()
        logger.error(f'初始化失败: {e}')
        raise
    finally:
        session.close()

if __name__ == '__main__':
    main()
