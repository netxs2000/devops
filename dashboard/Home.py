"""TODO: Add module description."""
import streamlit as st
from utils import set_page_config, run_query
set_page_config()
st.cache_data.clear()
st.title('🚀 DevOps 智能决策指挥中心')
st.markdown("""
<div style="background-color: #1e2130; padding: 25px; border-radius: 15px; border-left: 8px solid #00d4ff; margin-bottom: 25px; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
    <h3 style="margin-top:0; color:#00d4ff;">研发效能指挥舰桥 (Management Bridge)</h3>
    <p style="color:#eee; font-size:1.1rem;">
        基于 <strong>dbt v3.0</strong> 架构重构，全站数据已实现 MDM OneID 对齐。
    </p>
    <div style="margin-top:15px;">
        <p style="font-size:0.9rem; color:#aaa;">旗舰视图已就绪：深度融合 DORA, SPACE 与 财务投入产出比。</p>
    </div>
</div>
""", unsafe_allow_html=True)

if st.button('🔥 进入战略指挥中心 (Executive Cockpit)', use_container_width=True, type="primary"):
    st.switch_page('pages/19_Strategic_Executive_Cockpit.py')

st.divider()
col1, col2, col3, col4 = st.columns(4)
try:
    project_stats = run_query('SELECT count(*) as total FROM public.mdm_projects')
    total_projects = project_stats['total'][0] if not project_stats.empty else 0
    health_stats = run_query('SELECT avg(health_score) as avg_score FROM public_marts.fct_project_delivery_health')
    avg_health = round(health_stats['avg_score'][0], 1) if not health_stats.empty else 0
    deploy_stats = run_query('SELECT count(*) as count FROM public_staging.stg_gitlab_deployments WHERE created_at >= CURRENT_DATE')
    today_deploys = deploy_stats['count'][0] if not deploy_stats.empty else 0
    compliance_stats = run_query("SELECT count(*) as count FROM public_marts.fct_compliance_audit WHERE compliance_status = 'NON_COMPLIANT'")
    risk_count = compliance_stats['count'][0] if not compliance_stats.empty else 0
    try:
        quality_stats = run_query('SELECT success FROM sys_data_quality_results')
        passed_count = quality_stats[quality_stats['success'] == True].shape[0]
        total_checks = quality_stats.shape[0]
        quality_status = f'{passed_count}/{total_checks} 合规'
        quality_delta = 'Passed' if passed_count == total_checks else 'Issues Found'
        quality_color = 'normal' if passed_count == total_checks else 'inverse'
    except:
        quality_status = '未校验'
        quality_delta = None
        quality_color = 'off'
    col1.metric('纳管项目总数', f'{total_projects}', delta=None)
    col2.metric('全站交付健康分', f'{avg_health}', delta='1.2%', delta_color='normal')
    col3.metric('数据质量检测 (GX)', quality_status, delta=quality_delta, delta_color=quality_color)
    col4.metric('合规异常告警', f'{risk_count}', delta=f'-{risk_count}' if risk_count > 0 else '0', delta_color='inverse')
except Exception as e:
    st.error(f'数据加载失败，请检查数据库连接或 dbt 模型是否已生成。错误: {e}')
st.divider()
st.subheader('🎯 核心能力矩阵 (Capability Matrix)')

# Category: Strategic & Executive
st.markdown("##### 🏛️ 战略与治理 (Strategy & Governance)")
g1, g2, g3, g4 = st.columns(4)
with g1:
    if st.button('🏁 战略指挥中心', key='btn_cockpit', use_container_width=True): st.switch_page('pages/19_Strategic_Executive_Cockpit.py')
with g2:
    if st.button('💰 研发资本化', key='btn_capex', use_container_width=True): st.switch_page('pages/6_Capitalization_Audit.py')
with g3:
    if st.button('⚠️ 合规审计', key='btn_compliance', use_container_width=True): st.switch_page('pages/3_Compliance_Audit.py')
with g4:
    if st.button('📋 元数据治理', key='btn_meta', use_container_width=True): st.switch_page('pages/14_Metadata_Governance.py')

# Category: Delivery & Productivity
st.markdown("##### 🚀 交付与活力 (Delivery & Productivity)")
p1, p2, p3, p4 = st.columns(4)
with p1:
    if st.button('📊 DORA 看板', key='btn_dora', use_container_width=True): st.switch_page('pages/1_DORA_Metrics.py')
with p2:
    if st.button('🌌 SPACE 框架', key='btn_space', use_container_width=True): st.switch_page('pages/16_SPACE_Framework.py')
with p3:
    if st.button('🌊 价值流分析', key='btn_vsm', use_container_width=True): st.switch_page('pages/17_Value_Stream.py')
with p4:
    if st.button('💎 GitPrime 指导', key='btn_gitprime', use_container_width=True): st.switch_page('pages/0_Gitprime.py')

# Category: Quality & Engineering
st.markdown("##### 🛡️ 质量与工程 (Quality & Engineering)")
q1, q2, q3, q4 = st.columns(4)
with q1:
    if st.button('🏥 项目健康度', key='btn_health', use_container_width=True): st.switch_page('pages/2_Project_Health.py')
with q2:
    if st.button('📉 架构脆性', key='btn_abi', use_container_width=True): st.switch_page('pages/4_ABI_Analysis.py')
with q3:
    if st.button('🔥 代码热点图', key='btn_hotspots', use_container_width=True): st.switch_page('pages/15_Michael_Feathers_Code_Hotspots.py')
with q4:
    if st.button('🛡️ 指标护卫队', key='btn_guard', use_container_width=True): st.switch_page('pages/9_Metrics_Guard.py')

# Category: People & Talent
st.markdown("##### 👤 人才与组织 (People & Talent)")
t1, t2, t3, t4 = st.columns(4)
with t1:
    if st.button('👤 开发者 DNA', key='btn_profile', use_container_width=True): st.switch_page('pages/5_User_Profile.py')
with t2:
    if st.button('🎯 人才雷达', key='btn_talent', use_container_width=True): st.switch_page('pages/8_Talent_Radar.py')
with t3:
    if st.button('🕵️ 影子 IT', key='btn_shadow', use_container_width=True): st.switch_page('pages/7_Shadow_IT.py')
with t4:
    if st.button('🧵 活动流追踪', key='btn_activity', use_container_width=True): st.switch_page('pages/10_Unified_Activities.py')
st.divider()
st.markdown('🔗 [跳转至 Dagster 控制台](http://localhost:3000)')
st.sidebar.markdown('---')
st.sidebar.caption('DevOps Collector v2.0 | Powered by dbt & Streamlit')