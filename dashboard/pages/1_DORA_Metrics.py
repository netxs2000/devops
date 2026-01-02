"""TODO: Add module description."""
import streamlit as st
import plotly.express as px
from utils import set_page_config, run_query
set_page_config()
st.title('📊 DORA 核心效能看板')
st.caption('基于 Google Cloud DORA 研究框架，量化组织研发效能。')
query = '\n    select \n        project_name,\n        month,\n        deployment_frequency,\n        lead_time_minutes,\n        change_failure_rate_pct,\n        mttr_hours\n    from fct_dora_metrics\n    order by month asc\n'
df = run_query(query)
if df.empty:
    st.warning('暂无 DORA 指标数据，请确保执行了 `dbt run` 且已采集生产发布数据。')
else:
    projects = st.sidebar.multiselect('选择项目', options=df['project_name'].unique(), default=df['project_name'].unique())
    filtered_df = df[df['project_name'].isin(projects)]
    st.subheader('🚀 发布频率 (Deployment Frequency)')
    fig_df = px.line(filtered_df, x='month', y='deployment_frequency', color='project_name', markers=True, title='每月生产环境发布次数', template='plotly_dark')
    st.plotly_chart(fig_df, use_container_width=True)
    st.subheader('⏱️ 变更前置时间 (Lead Time for Changes)')
    fig_lt = px.bar(filtered_df, x='month', y='lead_time_minutes', color='project_name', barmode='group', title='从代码提交到部署到生产的平均时间 (分钟)', template='plotly_dark')
    st.plotly_chart(fig_lt, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader('💔 变更失败率 (CFR)')
        fig_cfr = px.area(filtered_df, x='month', y='change_failure_rate_pct', color='project_name', title='生产发布导致故障的比例 (%)', template='plotly_dark')
        st.plotly_chart(fig_cfr, use_container_width=True)
    with col2:
        st.subheader('🛠️ 平均修复时间 (MTTR)')
        fig_mttr = px.line(filtered_df, x='month', y='mttr_hours', color='project_name', markers=True, title='故障恢复平均时长 (小时)', template='plotly_dark')
        st.plotly_chart(fig_mttr, use_container_width=True)
    with st.expander('查看数据明细'):
        st.dataframe(filtered_df, use_container_width=True)