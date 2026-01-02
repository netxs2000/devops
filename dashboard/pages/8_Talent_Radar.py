"""TODO: Add module description."""
import streamlit as st
import plotly.express as px
from utils import run_query, set_page_config
set_page_config()
st.title('🎯 人才雷达与成长识别 (Talent Radar)')
st.markdown('---')
radar_df = run_query('SELECT * FROM fct_talent_radar')
c1, c2, c3 = st.columns(3)
c1.metric('明日之星 (Rising Stars)', len(radar_df[radar_df['talent_category'] == 'Rising Star']))
c2.metric('核心专家 (Key Experts)', len(radar_df[radar_df['talent_category'] == 'Key Expert']))
c3.metric('高潜人才', len(radar_df[radar_df['growth_potential'] > 0.7]))
st.markdown('### 人才分类分布')
fig_pie = px.pie(radar_df, names='talent_category', title='人才梯队分布', hole=0.4)
st.plotly_chart(fig_pie, use_container_width=True)
st.markdown('### 详细人才雷达列表')
st.dataframe(radar_df[['real_name', 'department', 'talent_category', 'growth_potential', 'skill_breadth_score']], use_container_width=True)
st.markdown('### 技能广度 vs 成长潜力')
fig_scatter = px.scatter(radar_df, x='skill_breadth_score', y='growth_potential', color='talent_category', hover_name='real_name', size='impact_score_z_score', title='人才潜力分布图')
st.plotly_chart(fig_scatter, use_container_width=True)