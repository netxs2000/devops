"""TODO: Add module description."""
import streamlit as st
import plotly.express as px
from utils import set_page_config, run_query
set_page_config()
st.title('🏗️ 架构脆性指数 (ABI) 分析')
st.caption('基于组件入度 (In-degree)、认知复杂度与测试覆盖率，识别组织内的“单点崩溃”风险模块。')
query = """
    SELECT 
        project_name,
        impact_in_degree,
        complexity_score,
        cognitive_complexity,
        coverage_pct,
        brittleness_index,
        architectural_health_status
    FROM public_marts.fct_architectural_brittleness
    ORDER BY brittleness_index DESC
"""
df = run_query(query)
if df.empty:
    st.warning('暂无架构脆性数据。请确保 dbt 模型 `fct_architectural_brittleness` 已生成。')
else:
    high_risk_count = len(df[df['architectural_health_status'] == 'CRITICAL_BRITTLE_CORE'])
    st.warning(f'☢️ 检测到 {high_risk_count} 个关键模块处于脆弱核心 (CRITICAL_BRITTLE_CORE) 状态，极易引发多米诺骨牌效应。')
    st.subheader('🌋 架构风险分布')
    
    fig = px.scatter(
        df, 
        x='impact_in_degree', 
        y='brittleness_index', 
        size='cognitive_complexity', 
        color='architectural_health_status', 
        hover_name='project_name',
        text='project_name', 
        color_discrete_map={
            'CRITICAL_BRITTLE_CORE': '#ff4b4b', 
            'STABLE_INFRA': '#00cc96', 
            'NORMAL': '#ffa500'
        }, 
        title='组件影响力 (In-degree) vs 脆性指数 (ABI)', 
        labels={
            'impact_in_degree': '组件入度 (被下游引用的总数)', 
            'brittleness_index': '脆性指数 (ABI)',
            'architectural_health_status': '架构健康状态'
        }, 
        template='plotly_dark'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader('📋 组件风险清单')
    st.dataframe(
        df, 
        column_config={
            'brittleness_index': st.column_config.NumberColumn('脆性指数', format='%.2f'), 
            'coverage_pct': st.column_config.NumberColumn('覆盖率', format='%.1f%%'), 
            'impact_in_degree': st.column_config.NumberColumn('下游引用数'),
            'complexity_score': st.column_config.NumberColumn('复杂度')
        }, 
        use_container_width=True, 
        hide_index=True
    )
    st.info('**为什么关注 ABI？**\n如果一个组件被大量下游服务引用（入度高），但其内部代码极其复杂且缺乏测试守护（覆盖率低），那么该组件的任何微小变更或隐藏 Bug 都可能导致整个系统的大规模瘫痪。')