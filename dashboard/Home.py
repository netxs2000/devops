"""TODO: Add module description."""
import streamlit as st
from utils import set_page_config, run_query
set_page_config()
st.title('🚀 DevOps 智能决策指挥中心')
st.markdown('\n<div style="background-color: #1e2130; padding: 20px; border-radius: 10px; border-left: 5px solid #00d4ff; margin-bottom: 25px;">\n    <strong>欢迎使用 DevOps Intelligence Dashboard。</strong><br>\n    本系统整合了 GitLab, Jira, SonarQube 的研发现据，通过 dbt 深度挖掘处理，为您提供实时的效能看板、健康评估与风险预警。\n</div>\n', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
try:
    project_stats = run_query('SELECT count(*) as total FROM mdm_projects')
    total_projects = project_stats['total'][0] if not project_stats.empty else 0
    health_stats = run_query('SELECT avg(health_score) as avg_score FROM fct_project_delivery_health')
    avg_health = round(health_stats['avg_score'][0], 1) if not health_stats.empty else 0
    deploy_stats = run_query('SELECT count(*) as count FROM stg_gitlab_deployments WHERE created_at >= CURRENT_DATE')
    today_deploys = deploy_stats['count'][0] if not deploy_stats.empty else 0
    compliance_stats = run_query("SELECT count(*) as count FROM fct_compliance_audit WHERE compliance_status = 'NON_COMPLIANT'")
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
st.subheader('🎯 核心能力矩阵')
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.info('📊 **DORA 看板**')
    if st.button('查看 DORA', key='dora'):
        st.switch_page('pages/1_DORA_Metrics.py')
with m2:
    st.success('🏥 **项目健康度**')
    if st.button('查看健康度', key='health'):
        st.switch_page('pages/2_Project_Health.py')
with m3:
    st.warning('⚠️ **合规审计**')
    if st.button('查看合规报告', key='compliance'):
        st.switch_page('pages/3_Compliance_Audit.py')
with m4:
    st.error('📉 **架构脆性(ABI)**')
    if st.button('查看架构分析', key='abi'):
        st.switch_page('pages/4_ABI_Analysis.py')
st.markdown('<br>', unsafe_allow_html=True)
m5, m6, m7, m8 = st.columns(4)
with m5:
    st.markdown('👤 **开发者画像**')
    if st.button('查看人才 DNA', key='profile'):
        st.switch_page('pages/5_User_Profile.py')
with m6:
    st.markdown('💰 **研发资本化**')
    if st.button('审计审计核算', key='capex'):
        st.switch_page('pages/6_Capitalization_Audit.py')
with m7:
    st.markdown('🕵️ **影子 IT 发现**')
    if st.button('查看资产风险', key='shadow'):
        st.switch_page('pages/7_Shadow_IT.py')
with m8:
    st.markdown('🎯 **人才雷达**')
    if st.button('识别明日之星', key='talent'):
        st.switch_page('pages/8_Talent_Radar.py')
st.divider()
st.markdown('🔗 [跳转至 Dagster 控制台](http://localhost:3000)')
st.sidebar.markdown('---')
st.sidebar.caption('DevOps Collector v2.0 | Powered by dbt & Streamlit')