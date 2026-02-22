"""TODO: Add module description."""
import pandas as pd
import plotly.express as px
import streamlit as st
from utils import run_query, set_page_config


set_page_config()
st.title('📜 统一活动流引擎 (Unified Activities)')
st.markdown('---')
col1, col2 = st.columns(2)
with col1:
    activity_type = st.multiselect('活动类型', ['COMMIT', 'ISSUE_OPEN', 'ISSUE_CLOSE', 'MR_OPEN', 'MR_MERGE', 'REVIEW_COMMENT'], default=['COMMIT', 'MR_MERGE'])
with col2:
    limit = st.slider('显示最近记录数', 100, 1000, 500)
query = f"""
    SELECT 
        occurred_at, 
        activity_type, 
        author_name, 
        project_id, 
        summary, 
        base_impact_score 
    FROM public_intermediate.int_unified_activities 
    WHERE activity_type IN ({','.join([f"'{t}'" for t in activity_type])})
    ORDER BY occurred_at DESC 
    LIMIT {limit}
"""
activities_df = run_query(query)
st.markdown(f'### 最近 {len(activities_df)} 条平台活动')
st.dataframe(activities_df, use_container_width=True)
st.markdown('### 活动强度趋势')
activities_df['occurred_at'] = pd.to_datetime(activities_df['occurred_at'])
daily_counts = activities_df.groupby([activities_df['occurred_at'].dt.date, 'activity_type']).size().reset_index(name='count')
fig = px.area(daily_counts, x='occurred_at', y='count', color='activity_type', title='平台活动实时强度 (基于采样数据)', line_group='activity_type')
st.plotly_chart(fig, use_container_width=True)
