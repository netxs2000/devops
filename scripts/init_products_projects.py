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
from devops_collector.models import Base, Organization, Product, ProjectMaster, ProjectProductRelation, User

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitProductsProjects')

# 产品清单 (产品名称, 所属中心名称, 产品经理, 开发负责人, 测试负责人, 发布负责人)
PRODUCTS_DATA = [
    ('预算一体化-江苏', '财政研发中心', '李亚程', '王冬梅', '张芳', '张芳'),
    ('预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '苑颖', '苑颖'),
    ('预算一体化-浙江', '财政研发中心', '王晴欣', '王晴欣', '侯路曼', '侯路曼'),
    ('财政绩效', '智慧云政务研发中心', '孙大勇', '孙大勇', '张崇稳', '张崇稳'),
    ('单位核算', '智慧云政务研发中心', '郭魁', '郭魁', '朱丹阳', '朱丹阳'),
    ('轻松报', '智慧云政务研发中心', '刘伟', '刘伟', '王润森', '王润森'),
    ('涉企分析', '智慧云政务研发中心', '胡昭鹏', '黄宇颖', '庞晓玉', '庞晓玉'),
    ('项目枢纽', '政务研发中心', '王磊', '曹坤', '李水珍', '李水珍'),
    ('预算一体化-海南', '政务研发中心', '张义胜', '张发', '何兵康', '何兵康'),
    ('政务', '政务研发中心', '徐营', '刘伟红', '张雪', '张雪'),
    ('非税', '互联网与协同业务拓展中心', '李平', '李平', '刘文', '刘文'),
    ('协同', '互联网与协同业务拓展中心', '皎海军', '张宇勇', None, None),
    ('大数据', '大数据及AI业务拓展中心', '马世杰', '马世杰', '李灿', '李灿'),
    ('行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('创新业务', '创新业务拓展中心', '王洁', '王志华', '刘冬香', '刘冬香'),
]

# 项目清单 (项目代号, 项目名称, 所属产品名称, 部门, 产品负责人, 开发负责人, 测试负责人, 发布负责人)
PROJECTS_RAW_DATA = [
    # 预算一体化-江苏
    ('BIM-JS', '基础信息管理-江苏', '预算一体化-江苏', '财政研发中心', '李亚程', '王冬梅', '张芳', '张芳'),
    ('BDG-JS', '指标调整调剂-江苏', '预算一体化-江苏', '财政研发中心', '李亚程', '孟凡龙', '张芳', '张芳'),
    ('PDM-JS', '项目库管理-江苏', '预算一体化-江苏', '财政研发中心', '李亚程', '孟凡龙', '张芳', '张芳'),
    ('BDM-JS', '预算编制-江苏', '预算一体化-江苏', '财政研发中心', '李亚程', '孙鑫', '张芳', '张芳'),
    ('COMMON-JS', '框架管理-江苏', '预算一体化-江苏', '财政研发中心', '李亚程', '孟凡龙', '张芳', '张芳'),
    ('PORTAL-JS', '门户管理-江苏', '预算一体化-江苏', '财政研发中心', '王斌', '孟凡龙', '张芳', '张芳'),
    ('GZXMGLXT-JS', '国债项目管理系统-江苏', '预算一体化-江苏', '财政研发中心', '王斌', '孟凡龙', '张芳', '张芳'),
    ('GBDM-JS', '政府预算-江苏', '预算一体化-江苏', '财政研发中心', '王斌', '王华龙', '张芳', '张芳'),
    
    # 预算一体化-通用
    ('FASP', '中台服务', '预算一体化-通用', '财政研发中心', '郑文浩', '汪辉', '王胜', '王胜'),
    ('COMMON', '框架管理', '预算一体化-通用', '财政研发中心', '郑文浩', '丘德和', '王莹', '王莹'),
    ('ESMS', '预算执行监督系统', '预算一体化-通用', '财政研发中心', '王晴欣', '王胜', '王莹', '王莹'),
    ('BIM', '基础信息管理', '预算一体化-通用', '财政研发中心', '王晴欣', '康建平', '苑颖', '苑颖'),
    ('PORTAL', '门户管理', '预算一体化-通用', '财政研发中心', '郑文浩', '王晴欣', '苑颖', '苑颖'),
    ('PDM', '项目库管理', '预算一体化-通用', '财政研发中心', '王晴欣', '高久林', '苑颖', '苑颖'),
    ('BDG', '预算调整和调剂', '预算一体化-通用', '财政研发中心', '王晴欣', '陈占涛', '苑颖', '苑颖'),
    ('BDM', '预算编制', '预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '苑颖', '苑颖'),
    ('PAY', '国库集中支付', '预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '王莹', '王莹'),
    ('GBDM', '政府预算', '预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '苑颖', '苑颖'),
    ('DATACOMMON', '采集组件', '预算一体化-通用', '财政研发中心', '王晴欣', '郑文浩', '苑颖', '苑颖'),
    ('SALARY', '工资系统', '预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '李慧', '李慧'),
    ('REALPAY', '实拨管理', '预算一体化-通用', '财政研发中心', '王晴欣', '段琰', '李慧', '李慧'),
    ('DITS', '财政运行监测', '预算一体化-通用', '财政研发中心', '谢长涛', '谢长涛', '苑颖', '苑颖'),
    ('INSPECT', '动态监控', '预算一体化-通用', '财政研发中心', '谢延辉', '谢延辉', '苑颖', '苑颖'),
    ('BAMS', '银行账户', '预算一体化-通用', '财政研发中心', '王晴欣', '成腾', '王莹', '王莹'),
    ('ACCT', '总会计核算', '预算一体化-通用', '财政研发中心', '王晴欣', '陈广泽', '李慧', '李慧'),
    ('GL', '预算指标账', '预算一体化-通用', '财政研发中心', '王晴欣', '张震', '李慧', '李慧'),
    ('gabm', '国资预算', '预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '苑颖', '苑颖'),
    ('SPEACCT', '专户管理', '预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '李慧', '李慧'),
    ('RQREPORT', '打印和会计报表', '预算一体化-通用', '财政研发中心', '王晴欣', '吴奇岭', '王莹', '王莹'),
    ('ndpm', '国债项目系统', '预算一体化-通用', '财政研发中心', '王晴欣', '陈占涛', '王莹', '王莹'),
    ('MONITOR', '中台监控', '预算一体化-通用', '财政研发中心', '张凯', '张凯', '王莹', '王莹'),
    ('DFMS', '直达资金管理', '预算一体化-通用', '财政研发中心', '王晴欣', '陈占涛', '王莹', '王莹'),
    ('CARD', '公务卡系统', '预算一体化-通用', '财政研发中心', '王晴欣', '李建华', '王莹', '王莹'),
    ('EXCASH', '国库现金管理系统', '预算一体化-通用', '财政研发中心', '王晴欣', '段琰', '王莹', '王莹'),
    ('IFMISAI', '预算管理一体化AI应用', '预算一体化-通用', '财政研发中心', '刘洪昌', '赵志伟', '苑颖', '苑颖'),
    ('RDMS', '资料收发管理系统', '预算一体化-通用', '财政研发中心', '吴奇岭', '陈晖', '苑颖', '苑颖'),
    ('PLM', '政策库管理', '预算一体化-通用', '财政研发中心', '黄涛', '谢长涛', '苑颖', '苑颖'),
    ('HPRS', '项目追踪系统', '预算一体化-通用', '财政研发中心', '王晴欣', '苑颖', '苑颖', '苑颖'),
    
    # 预算一体化-浙江 / 海南 / 创新 / 大数据 / 非税
    ('PAY-ZJ', '国库集中支付-浙江', '预算一体化-浙江', '财政研发中心', '王晴欣', '王晴欣', '侯路曼', '侯路曼'),
    ('CARD-ZJ', '公务卡系统-浙江', '预算一体化-浙江', '财政研发中心', '王晴欣', '王晴欣', '侯路曼', '侯路曼'),
    ('BDG-ZJ', '预算调整和调剂-浙江', '预算一体化-浙江', '财政研发中心', '崔宝华', '雍宜华', '王爽', '王爽'),
    ('OBS', '预决算公开与分析查询', '创新业务', '创新业务拓展中心', '王洁', '王志华', '刘冬香', '刘冬香'),
    ('SI', '社会保险基金预算管理系统', '创新业务', '创新业务拓展中心', '罗晓云', '张朝辉', '孙鹏', '孙鹏'),
    ('BDBS', '通用业务管理平台', '大数据', '大数据及AI业务拓展中心', '马世杰', '甘海权', '李灿', '李灿'),
    ('BDP', '大数据平台', '大数据', '大数据及AI业务拓展中心', '马世杰', '马世杰', '李灿', '李灿'),
    ('HQREPORT', '大数据通用报表系统', '大数据', '大数据及AI业务拓展中心', '张利宾', '张利宾', '李灿', '李灿'),
    ('FS-SRS_JGL', '非税收入收缴管理系统', '非税', '互联网与协同业务拓展中心', '李平', '李平', '刘文', '刘文'),
    ('CYJF', '财云缴费', '非税', '互联网与协同业务拓展中心', '郎玉兴', '郎玉兴', '孙阳', '孙阳'),
    ('FS-CZOA', '财政管理信息系统', '非税', '互联网与协同业务拓展中心', '郎玉兴', '舒鹏', '舒鹏', '舒鹏'),
    ('FS-CZPJGLPT', '财政票据管理平台', '非税', '互联网与协同业务拓展中心', '郎玉兴', '郎玉兴', '孙阳', '孙阳'),
    ('TC', '易创快速开发平台', '协同', '互联网与协同业务拓展中心', '皎海军', '张宇勇', '0', '0'),

    # 行业业务
    ('HY-BUSI', '微服务-业务产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('TRAFFIC', '普通省道和农村公路“以奖代补”考核数据支撑系统', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('LMVS', '链农社', '行业业务', '行业业务拓展中心', '于德河', '孙路路', '孙路路', '孙路路'),
    ('HY-QK-CHART', '微服务-乾坤图表服务产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-QK-CK', '微服务-乾坤仓库产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-ZSK', '微服务-知识库产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-QK-TABLE', '微服务-乾坤报表服务产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-ACCESS', '微服务-数据接入产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('TECH', '科技监管系统', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-XQC', '业务范围中心-物资仓库', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-WJFW', '微服务-文件服务产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-JSTX', '微服务-即时通讯产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),
    ('HY-INS', '微服务-监控产品', '行业业务', '行业业务拓展中心', '杜崇明', '杜崇明', '刘莫沉', '刘莫沉'),

    # 预算一体化-海南 / 政务
    ('BPDM', '项目枢纽平台', '项目枢纽', '政务研发中心', '王磊', '曹坤', '李水珍', '李水珍'),
    ('GFA-DEM-HN', '部门决算-海南', '预算一体化-海南', '政务研发中心', '张义胜', '张发', None, None),
    ('GFA-GOM-HN', '财政总决算-海南', '预算一体化-海南', '政务研发中心', '王磊', '高哲', '何兵康', '何兵康'),
    ('INEXREPORT-HN', '旬月报系统-海南', '预算一体化-海南', '政务研发中心', '王磊', '高哲', '何兵康', '何兵康'),
    ('PERFORMANCE-HN', '绩效-海南', '预算一体化-海南', '政务研发中心', '袁鑫', '袁鑫', '李水珍', '李水珍'),
    ('REPORT-HN', '综合查询-海南', '预算一体化-海南', '政务研发中心', '李水珍', '焦丽真', '焦丽真', '焦丽真'),
    ('PDM-HN', '项目库-海南', '预算一体化-海南', '政务研发中心', '李水珍', '焦丽真', '焦丽真', '焦丽真'),
    ('BIM-HN', '基础信息-海南', '预算一体化-海南', '政务研发中心', '李水珍', '焦丽真', '焦丽真', '焦丽真'),
    ('BDM-HN', '预算编制-海南', '预算一体化-海南', '政务研发中心', '李水珍', '焦丽真', '焦丽真', '焦丽真'),
    ('EDUP', '部属高校预算绩效', '政务', '政务研发中心', '徐营', '刘伟红', '张雪', '张雪'),
    ('DFCZFXPJ', '地方财政分析评价系统', '政务', '政务研发中心', '王磊', '胡晓敏', '胡晓敏', '胡晓敏'),
    ('SALARY-JZXT', '军队转业干部信息管理系统', '政务', '政务研发中心', '袁鑫', '胡晓敏', '胡晓敏', '胡晓敏'),
    ('YSJL-CZB', '预算管理交流平台', '政务', '政务研发中心', '李鹏', '王妍', '王妍', '王妍'),
    ('CLLBDG', '财务项目管理（三级项目管理）', '政务', '政务研发中心', '王磊', '何兵康', '何兵康', '何兵康'),
    ('BUSCOMMON-ZW', '政务框架', '政务', '政务研发中心', '石硕', '石硕', '张莉君', '张莉君'),
    ('CASH-CZB', '财政部现金管理系统', '政务', '政务研发中心', '李鹏', '胡晓敏', '胡晓敏', '胡晓敏'),
    ('INSPECT-CZB', '财政国库动态监控', '政务', '政务研发中心', '李鹏', '胡晓敏', '胡晓敏', '胡晓敏'),

    # 智慧云政务中心
    ('PMKPI', '预算财政绩效', '财政绩效', '智慧云政务研发中心', '孙大勇', '孙大勇', '张崇稳', '张崇稳'),
    ('GLA', '单位会计核算', '单位核算', '智慧云政务研发中心', '郭魁', '郭魁', '朱丹阳', '朱丹阳'),
    ('GLA-XJ', '单位会计核算-新疆', '单位核算', '智慧云政务研发中心', '郭魁', '郭魁', '朱丹阳', '朱丹阳'),
    ('G-GLA', '单位核算（G版）', '轻松报', '智慧云政务研发中心', '郭魁', '郭魁', '朱丹阳', '朱丹阳'),
    ('ORS', '网上报销2.0', '轻松报', '智慧云政务研发中心', '刘伟', '刘伟', '王润森', '王润森'),
    ('INVOICE', '电子智票', '轻松报', '智慧云政务研发中心', '庞晓亮', '庞晓亮', '王润森', '王润森'),
    ('BGTPM', '项目管理', '轻松报', '智慧云政务研发中心', '庞晓亮', '庞晓亮', '王润森', '王润森'),
    ('CPAS', '合同管理', '轻松报', '智慧云政务研发中心', '高明', '高明', '王润森', '王润森'),
    ('OFFCAR', '公务用车', '轻松报', '智慧云政务研发中心', '高明', '高明', '王润森', '王润森'),
    ('ORSAPP', '网上报销小程序', '轻松报', '智慧云政务研发中心', '高明', '高明', '王润森', '王润森'),
    ('ASSET', '资产管理', '轻松报', '智慧云政务研发中心', '刘彤', '刘彤', '朱丹阳', '朱丹阳'),
    ('GPA', '采购管理', '轻松报', '智慧云政务研发中心', '郭魁', '郭魁', '朱丹阳', '朱丹阳'),
    ('BPPF-PJBT', '部门项目预算绩效管理系统', '涉企分析', '智慧云政务研发中心', '胡昭鹏', '黄宇颖', '庞晓玉', '庞晓玉'),
    ('GFR-HN', '财务报告-海南', '预算一体化-海南', '智慧云政务研发中心', '柴文鹏', '柴文鹏', '庞晓玉', '庞晓玉'),
]

def get_org_id(session: Session, center_name: str) -> str:
    """根据中心名称查找对应的 Organization ID。"""
    org = session.query(Organization).filter_by(org_name=center_name).first()
    if org:
        return org.org_id
    # 如果找不到，尝试拼音模式（兜底）
    return f"CTR-{center_name}"

def init_products(session: Session) -> Dict[str, str]:
    """初始化产品主数据。"""
    logger.info('正在初始化产品主数据...')
    name_to_id = {}
    
    # 建立姓名到用户 ID 的缓存
    user_cache = {u.full_name: u.global_user_id for u in session.query(User).filter_by(is_current=True).all()}

    for row in PRODUCTS_DATA:
        name, center = row[0], row[1]
        pm_name = row[2] if len(row) > 2 else None
        dev_name = row[3] if len(row) > 3 else None
        qa_name = row[4] if len(row) > 4 else None
        rel_name = row[5] if len(row) > 5 else None

        org_id = get_org_id(session, center)
        # 生成唯一产品 ID (PRD + 姓名缩写/拼音处理，这里简单模拟)
        prod_id = f"PRD-{uuid.uuid5(uuid.NAMESPACE_DNS, name).hex[:8].upper()}"
        
        product = session.query(Product).filter_by(product_name=name).first()
        if not product:
            product = Product(
                product_id=prod_id,

                product_name=name,
                product_description=f"{name} 业务产品线",
                owner_team_id=org_id,
                lifecycle_status='Active',
                version_schema='Semantic'
            )
            session.add(product)
        else:
            product.owner_team_id = org_id
        
        # 绑定负责人
        if pm_name: product.product_manager_id = user_cache.get(pm_name)
        if dev_name: product.dev_lead_id = user_cache.get(dev_name)
        if qa_name: product.qa_lead_id = user_cache.get(qa_name)
        if rel_name: product.release_lead_id = user_cache.get(rel_name)
        
        session.flush()
        name_to_id[name] = product.product_id
        
    session.commit()
    return name_to_id

def init_projects(session: Session, prod_name_to_id: Dict[str, str]):
    """初始化项目主数据并关联产品。"""
    logger.info('正在初始化项目主数据及关联关系...')
    
    # 建立姓名到用户 ID 的缓存
    user_cache = {u.full_name: u.global_user_id for u in session.query(User).filter_by(is_current=True).all()}
    
    for row in PROJECTS_RAW_DATA:
        code, name, prod_name, center = row[0], row[1], row[2], row[3]
        product_owner_name = row[4] if len(row) > 4 else None
        dev_lead_name = row[5] if len(row) > 5 else None
        qa_lead_name = row[6] if len(row) > 6 else None
        release_lead_name = row[7] if len(row) > 7 else None

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
        
        # 绑定负责人
        if product_owner_name: project.product_owner_id = user_cache.get(product_owner_name)
        if dev_lead_name: project.dev_lead_id = user_cache.get(dev_lead_name)
        if qa_lead_name: project.qa_lead_id = user_cache.get(qa_lead_name)
        if release_lead_name: project.release_lead_id = user_cache.get(release_lead_name)

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
