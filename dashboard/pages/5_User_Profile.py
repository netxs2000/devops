import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import run_query, set_page_config

set_page_config()

st.title("👤 开发者 DNA 画像 (Developer Activity Profile)")
st.markdown("---")

# User Selection
users_df = run_query("SELECT user_id, real_name, department FROM fct_developer_activity_profile")
selected_user_name = st.selectbox("选择开发者进行透视", users_df['real_name'].unique())
selected_user = users_df[users_df['real_name'] == selected_user_name].iloc[0]

# Detailed Query
profile_df = run_query(f"SELECT * FROM fct_developer_activity_profile WHERE user_id = {selected_user['user_id']}")
row = profile_df.iloc[0]

# Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.header(f" {row['real_name']}")
    st.subheader(f"🏷️ 类型: {row['developer_archetype']}")
    st.write(f"🏢 部门: {row['department']}")
    
    st.divider()
    
    m1, m2 = st.columns(2)
    m1.metric("总影响力分数", f"{row['total_impact_score']:.0f}")
    m2.metric("日均产出率", f"{row['daily_velocity']:.2f}")
    
    m3, m4 = st.columns(2)
    m3.metric("提交代码数", row['commit_count'])
    m4.metric("评审注释数", row['review_comment_count'])
    
with col2:
    # Radar Chart
    categories = ['代码提交', '评审贡献', 'MR开启', '需求终结']
    values = [row['commit_count'], row['review_comment_count'], row['mr_open_count'], row['issue_closed_count']]
    
    # Normalize values for radar chart visibility
    max_val = max(values) if max(values) > 0 else 1
    norm_values = [v/max_val for v in values]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=row['real_name'],
        line_color='#636EFA'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max_val]),
            bgcolor="#1e2130"
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title="开发者能力雷达图"
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### 🏆 团队贡献者排行榜")
top_contributors = run_query("SELECT real_name, total_impact_score, developer_archetype, daily_velocity FROM fct_developer_activity_profile ORDER BY total_impact_score DESC LIMIT 10")
st.table(top_contributors)
