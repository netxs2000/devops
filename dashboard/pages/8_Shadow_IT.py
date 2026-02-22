"""TODO: Add module description."""
import plotly.express as px
import streamlit as st
from utils import run_query, set_page_config


set_page_config()
st.title('🕵️ 影子系统发现 (Shadow IT Discovery)')
st.markdown('---')
shadow_df = run_query('SELECT * FROM public_marts.fct_shadow_it_discovery')
total_shadow = len(shadow_df[shadow_df['discovery_reason'] != 'Unknown'])
st.metric('发现的异常/影子项目', total_shadow)
st.markdown('\n通过监控 **非标准化仓库命名**、**长期无 Readme**、**非官方 CI 工具链** 以及 **权限配置异常** 识别研发过程中的影子资产。\n')
if not shadow_df.empty:
    fig = px.scatter(shadow_df, x='risk_score', y='last_activity_days_ago', size='contributor_count', color='discovery_reason', hover_name='project_name', title='影子 IT 风险评估图 (气泡大小代表参与人数)', labels={'risk_score': '风险评分', 'last_activity_days_ago': '最后活跃(天)'})
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('### 风险项目清单')
    st.dataframe(shadow_df.sort_values('risk_score', ascending=False), use_container_width=True)
else:
    st.success('目前未发现任何影子 IT 风险项目。')
