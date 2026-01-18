"""初始化组织架构及负责人数据 (MDM_ORGANIZATIONS & MDM_IDENTITIES)。

本脚本根据用户提供的组织架构图，自动完成以下任务：
1. 创建/更新全量负责人占位账号。
2. 构建“体系-中心-部门”三级组织映射。
3. 建立组织与负责人的关联关系。

执行方式:
    python scripts/init_organizations.py
"""
import sys
import os
import logging
import uuid
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, Organization, User

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 用户数据定义 (姓名: 拼音)
USER_NAME_MAP = {
    '贾志涛': 'jiazhitao', '邓铭': 'dengming', '刘天阳': 'liutianyang', '黄涛': 'huangtao',
    '王斌': 'wangbin', '欧炫': 'ouxuan', '余正燚': 'yuzhengyi', '苑颖': 'yuanying',
    '王海峰': 'wanghaifeng', '张兵': 'zhangbing', '马世杰': 'mashijie', '孙治': 'sunzhi',
    '杨光': 'yangguang', '周光硕': 'zhouguangshuo', '宫涛': 'gongtao', '赵孝涛': 'zhaoxiaotao',
    '任巧贤': 'renqiaoxian', '胡命羽': 'humingyu', '海延军': 'haiyanjun', '蔺艳丽': 'linyanli',
    '董隆斌': 'donglongbin', '许慎': 'xushen', '周玉平': 'zhouyuping', '简宝峦': 'jianbaoluan',
    '袁旭光': 'yuanxuguang', '高欣': 'gaoxin', '田伟': 'tianwei', '王扬': 'wangyang',
    '常和金': 'changhejin', '王勇': 'wangyong', '葛小军': 'gexiaojun',
    '耿亮': 'gengliang', '汪新': 'wangxin', '周忠义': 'zhouzhongyi', '周晓佳': 'zhouxiaojia',
    '张海军': 'zhanghaijun', '王爱伟': 'wangaiwei', '李华军': 'lihuajun', '桂明': 'guiming',
    '阎进': 'yanjin', '秦彬彬': 'qinbinbin', '骆伟琼': 'luoweiqiong', '李启飞': 'liqifei',
    '孙立': 'sunli', '周景伟': 'zhoujingwei', '皎海军': 'jiaohaijun', '张崇稳': 'zhangchongwen',
    '高青山': 'gaoqingshan', '仇晓华': 'qiuxiaohua', '王京辉': 'wangjinghui', '吴欣生': 'wuxinsheng',
    '王俊江': 'wangjunjiang', '王哲': 'wangzhe', '叶道武': 'yedaowu', '朱晓辉': 'zhuxiaohui',
    '王旭东': 'wangxudong', '何山': 'heshan', '赵勇惠': 'zhaoyonghui', '陶昕': 'taoxin',
    '刘洪昌': 'liuhongchang', '李水珍': 'lishuizhen', '张聚锁': 'zhangjusuo', '高明': 'gaoming',
    '蔡道斌': 'caidaobin', '杜崇明': 'duchongming',
    '李亚程': 'liuyacheng', '王冬梅': 'wangdongmei', '张芳': 'zhangfang', '孟凡龙': 'mengfanlong',
    '潘其龙': 'panqilong', '孙鑫': 'sunxin', '郑文浩': 'zhengwenhao', '汪辉': 'wanghui',
    '王胜': 'wangsheng', '王莹': 'wangying', '丘德和': 'qiudehe', '康建平': 'kangjianping',
    '高久林': 'gaojiulin', '陈占涛': 'chenzhantao', '吴奇岭': 'wuqiling', '段琰': 'duanyan',
    '谢长涛': 'xiechangtao', '谢延辉': 'xieyanhui', '成腾': 'chengteng', '陈广泽': 'chenguangze',
    '张震': 'zhangzhen', '彭然': 'pengran', '张凯': 'zhangkai', '李建华': 'lijianhua',
    '赵志伟': 'zhaozhiwei', '苗颖': 'miaoying', '李慧': 'lihui', '侯路曼': 'houluman',
    '崔宝华': 'cuibaohua', '雍宜华': 'yongyihua', '王洁': 'wangjie', '王志华': 'wangzhihua',
    '刘冬香': 'liudongxiang', '罗晓云': 'luoxiaoyun', '张朝辉': 'zhangchaohui', '孙鹏': 'sunpeng',
    '甘海权': 'ganhaiquan', '李灿': 'lican', '张利宾': 'zhanglibin', '李平': 'liping',
    '刘文': 'liuwen', '郎玉兴': 'langyuxing', '孙阳': 'sunyang', '舒鹏': 'shupeng',
    '张宇勇': 'zhangyuyong', '刘莫沉': 'liumochen', '于德河': 'yudehe', '孙路路': 'sunlulu',
    '王磊': 'wanglei', '曹坤': 'caokun', '张义胜': 'zhangyisheng', '张发': 'zhangfa',
    '高哲': 'gaozhe', '何兵康': 'hebingkang', '袁鑫': 'yuanxin', '焦丽真': 'jiaolizhen',
    '徐营': 'xuying', '刘伟红': 'liuweihong', '张雪': 'zhangxue', '胡晓敏': 'huxiaomin',
    '李鹏': 'lipeng', '王妍': 'wangyan', '石硕': 'shishuo', '张莉君': 'zhanglijun',
    '孙大勇': 'sundayong', '郭魁': 'guokui', '朱丹阳': 'zhudanyang', '刘伟': 'liuwei',
    '韩学成': 'hanxuecheng', '庞晓亮': 'pangxiaoliang', '王润森': 'wangrunsen', '刘彤': 'liutong',
    '胡昭鹏': 'huzhaopeng', '黄宇颖': 'huangyuying', '庞晓玉': 'pangxiaoyu', '柴文鹏': 'chaiwenpeng'
}

# 组织架构定义 (体系, 中心, 部门, 负责人)
ORG_RAW_DATA = [
    ('财务核算部', '财务核算部', None, '田伟'),
    ('服务交付体系', '地方服务交付中心', None, '胡命羽'),
    ('服务交付体系', '地方服务交付中心', '公共支撑服务分中心', '耿亮'),
    ('服务交付体系', '地方服务交付中心', '第一技术支持分中心', '汪新'),
    ('服务交付体系', '地方服务交付中心', '第二技术支持分中心', '周忠义'),
    ('服务交付体系', '地方服务交付中心', '第三技术支持分中心', '周晓佳'),
    ('服务交付体系', '地方服务交付中心', '第四技术支持分中心', '张海军'),
    ('服务交付体系', '地方服务交付中心', '第五技术支持分中心', '王爱伟'),
    ('服务交付体系', '地方服务交付中心', '第六技术支持分中心', '李华军'),
    ('服务交付体系', '地方服务交付中心', '第七技术支持分中心', '桂明'),
    ('服务交付体系', '基础服务交付中心', None, '海延军'),
    ('服务交付体系', '中央服务交付中心', None, '任巧贤'),
    ('服务交付体系', '中央服务交付中心', '北京服务交付部', '阎进'),
    ('服务交付体系', '中央服务交付中心', '中央服务交付支持部', '秦彬彬'),
    ('品牌市场与产品推广部', '品牌市场与产品推广部', None, '骆伟琼'),
    ('行政中心', None, None, '葛小军'),
    ('行政中心', 'IT部', None, '王勇'),
    ('行政中心', '企业管理部', None, '葛小军'),
    ('行政中心', '保密办公室', None, '王勇'),
    ('研发体系', '财政研发中心', None, '贾志涛'),
    ('研发体系', '财政研发中心', '产品部', '邓铭'),
    ('研发体系', '财政研发中心', '中台框架部', '刘天阳'),
    ('研发体系', '财政研发中心', '预算产品一部', '黄涛'),
    ('研发体系', '财政研发中心', '预算产品二部', '王斌'),
    ('研发体系', '财政研发中心', '执行产品部', '欧炫'),
    ('研发体系', '财政研发中心', '项目开发部', '余正燚'),
    ('研发体系', '财政研发中心', '测试部', '苑颖'),
    ('研发体系', '创新业务拓展中心', None, '王海峰'),
    ('研发体系', '创新业务拓展中心', '创新业务产品研发部', '李启飞'),
    ('研发体系', '创新业务拓展中心', '创新业务市场营销部', '孙立'),
    ('研发体系', '大数据及AI业务拓展中心', None, '张兵'),
    ('研发体系', '大数据及AI业务拓展中心', '数智平台研发部', '马世杰'),
    ('研发体系', '大数据及AI业务拓展中心', '数智业务拓展部', '张兵'),
    ('研发体系', '大数据及AI业务拓展中心', '数智业务销售部', '孙治'),
    ('研发体系', '互联网与协同业务拓展中心', None, '杨光'),
    ('研发体系', '互联网与协同业务拓展中心', '非税产品线', '周景伟'),
    ('研发体系', '互联网与协同业务拓展中心', '协同办公产品线', '皎海军'),
    ('研发体系', '行业业务拓展中心', None, '周光硕'),
    ('研发体系', '政务研发中心', None, '宫涛'),
    ('研发体系', '智慧云政务研发中心', None, '赵孝涛'),
    ('研发体系', '智慧云政务研发中心', 'IT服务产品部', '赵孝涛'),
    ('研发体系', '智慧云政务研发中心', '销售部', '张崇稳'),
    ('研发体系', '产品市场与解决方案中心', None, '周玉平'),
    ('营销体系', '产品市场与解决方案中心', '产品市场部', '简宝峦'),
    ('营销体系', '产品市场与解决方案中心', '售前解决方案部', '袁旭光'),
    ('营销体系', '大客户中心', None, '蔺艳丽'),
    ('营销体系', '大客户中心', '财政部驻点服务部', '高青山'),
    ('营销体系', '大客户中心', '市场营销部', '仇晓华'),
    ('营销体系', '大客户中心', '商务支持部', '王京辉'),
    ('营销体系', '地方市场营销中心', None, '董隆斌'),
    ('营销体系', '地方市场营销中心', '第一大区', '吴欣生'),
    ('营销体系', '地方市场营销中心', '第二大区', '王俊江'),
    ('营销体系', '地方市场营销中心', '第三大区', '王俊江'),
    ('营销体系', '地方市场营销中心', '第四大区', '王哲'),
    ('营销体系', '地方市场营销中心', '第五大区', '胡命羽'),
    ('营销体系', '地方市场营销中心', '第六大区', '叶道武'),
    ('营销体系', '地方市场营销中心', '第七大区', '朱晓辉'),
    ('营销体系', '地方市场营销中心', '第八大区', '王旭东'),
    ('营销体系', '地方市场营销中心', '第九大区', '何山'),
    ('营销体系', '地方市场营销中心', '第十大区', '赵勇惠'),
    ('营销体系', '地方市场营销中心', '集成营销部', '陶昕'),
    ('营销体系', '地方市场营销中心', '区域经营管理部', '董隆斌'),
    ('营销体系', '商务渠道拓展中心', None, '高欣'),
    ('运营管理中心', None, None, '常和金'),
    ('运营管理中心', '经营管理部', None, '常和金'),
    ('运营管理中心', '人力资源部', None, '王扬'),
    ('运营管理中心', '质量管理部', None, '许慎'),
]

def get_or_create_user(session, name):
    """根据姓名获取或创建用户占位符。"""
    pinyin = USER_NAME_MAP.get(name)
    if not pinyin:
        logger.warning(f"未找到姓名 {name} 的拼音定义，跳过用户创建。")
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
        logger.info(f"已创建用户: {name} ({email})")
    return user

def init_organizations():
    """解析数据并初始化组织架构。"""
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        logger.info('开始同步全量组织架构及其负责人...')
        
        # 1. 创建顶层根节点
        root_id = 'ORG-ROOT'
        root = session.query(Organization).filter_by(org_id=root_id).first()
        if not root:
            root = Organization(
                org_id=root_id,
                org_name='某集团公司',
                org_level=0,
                parent_org_id=None,
                is_active=True,
                is_current=True
            )
            session.add(root)
            session.flush()

        # 缓存已处理的组织，避免重复
        processed_orgs = {root_id}

        for system_name, center_name, dept_name, manager_name in ORG_RAW_DATA:
            # 2. 处理体系 (Level 1)
            sys_id = f"SYS-{USER_NAME_MAP.get(system_name, system_name)}"[:50]
            if sys_id not in processed_orgs:
                # 获取负责人 (仅当中心和部门都为空时)
                mgr_user = get_or_create_user(session, manager_name) if not center_name and not dept_name else None
                org = session.query(Organization).filter_by(org_id=sys_id).first()
                if not org:
                    org = Organization(org_id=sys_id, org_name=system_name, org_level=1, 
                                     parent_org_id=root_id, is_active=True, is_current=True,
                                     manager_user_id=mgr_user.global_user_id if mgr_user else None)
                    session.add(org)
                else:
                    if mgr_user: org.manager_user_id = mgr_user.global_user_id
                session.flush()
                processed_orgs.add(sys_id)

            # 3. 处理中心 (Level 2)
            current_parent_id = sys_id
            if center_name:
                ctr_id = f"CTR-{USER_NAME_MAP.get(center_name, center_name)}"[:50]
                if ctr_id not in processed_orgs:
                    # 获取负责人
                    mgr_user = get_or_create_user(session, manager_name) if not dept_name else None
                    org = session.query(Organization).filter_by(org_id=ctr_id).first()
                    if not org:
                        org = Organization(
                            org_id=ctr_id, org_name=center_name, org_level=2,
                            parent_org_id=sys_id, is_active=True, is_current=True,
                            manager_user_id=mgr_user.global_user_id if mgr_user else None
                        )
                        session.add(org)
                    else:
                        if mgr_user: org.manager_user_id = mgr_user.global_user_id
                    session.flush()
                    processed_orgs.add(ctr_id)
                current_parent_id = ctr_id

            # 4. 处理部门 (Level 3)
            if dept_name:
                dept_id = f"DEP-{USER_NAME_MAP.get(dept_name, dept_name)}"[:50]
                mgr_user = get_or_create_user(session, manager_name)
                org = session.query(Organization).filter_by(org_id=dept_id).first()
                if not org:
                    org = Organization(
                        org_id=dept_id, org_name=dept_name, org_level=3,
                        parent_org_id=current_parent_id, is_active=True, is_current=True,
                        manager_user_id=mgr_user.global_user_id if mgr_user else None
                    )
                    session.add(org)
                else:
                    if mgr_user: org.manager_user_id = mgr_user.global_user_id
                session.flush()
        
        session.commit()
        logger.info('✅ 组织架构及负责人初始化完成！')

if __name__ == '__main__':
    init_organizations()
