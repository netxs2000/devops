"""DORA Core Metrics Dashboard.

This module implements the industry-standard DORA (DevOps Research and Assessment)
metrics dashboard, enabling organizations to visualize and track their software
delivery performance.

Metrics tracked:
1. Deployment Frequency: How often an organization successfully releases to production.
2. Lead Time for Changes: The amount of time it takes a commit to get into production.
3. Change Failure Rate: The percentage of deployments causing a failure in production.
4. Time to Restore Service: How long it takes an organization to recover from a failure.

Benchmarks (2023 DORA Report):
- Elite: On-demand (freq), < 1 day (lead time), < 5% (failure rate), < 1 hour (restore).
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import set_page_config, run_query

# --- Configuration & Styling ---
set_page_config()
st.title('📊 DORA 核心效能看板')
st.caption('基于 Google Cloud DORA 研究框架，量化组织研发效能。')

st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #3366ff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .rating-elite { color: #8F00FF; font-weight: bold; } /* Purple */
    .rating-high { color: #00C853; font-weight: bold; }   /* Green */
    .rating-medium { color: #FFAB00; font-weight: bold; }  /* Amber */
    .rating-low { color: #D50000; font-weight: bold; }     /* Red */
</style>
""", unsafe_allow_html=True)

# --- DORA Rating Logic ---
def get_dora_rating(metric: str, value: float) -> tuple:
    """Determine DORA rating based on standard benchmarks (approximate).
    
    Args:
        metric: Metric name ('frequency', 'lead_time', 'cfr', 'mttr').
        value: Metric value.
        
    Returns:
        tuple: (Rating Label, CSS Class suffix)
    """
    if metric == 'frequency':
        # monthly count: >30 (daily), >4 (weekly), >1 (monthly)
        if value >= 30: return "Elite 🏆", "elite"
        if value >= 4: return "High 🟢", "high"
        if value >= 1: return "Medium 🟡", "medium"
        return "Low 🔴", "low"
        
    elif metric == 'lead_time':
        # minutes: < 1 day (1440), < 1 week (10080), < 1 month (43200)
        if value <= 1440: return "Elite 🏆", "elite"
        if value <= 10080: return "High 🟢", "high"
        if value <= 43200: return "Medium 🟡", "medium"
        return "Low 🔴", "low"

    elif metric == 'cfr':
        # percentage: < 5%, < 15%, < 45%
        if value <= 5: return "Elite 🏆", "elite"
        if value <= 15: return "High 🟢", "high"
        if value <= 45: return "Medium 🟡", "medium"
        return "Low 🔴", "low"
        
    elif metric == 'mttr':
        # hours: < 1h, < 1d (24h), < 1w (168h)
        if value <= 1: return "Elite 🏆", "elite"
        if value <= 24: return "High 🟢", "high"
        if value <= 168: return "Medium 🟡", "medium"
        return "Low 🔴", "low"
    
    return "N/A", "medium"

# --- Data Loading ---
query = """
    select 
        project_name,
        month,
        deployment_frequency,
        lead_time_minutes,
        change_failure_rate_pct,
        mttr_hours,
        -- Calculated sorting helper
        month as sort_month
    from fct_dora_metrics
    order by month asc
"""
df = run_query(query)

if df.empty:
    st.info('🚀 暂无 DORA 指标数据。请配置 GitHub/GitLab 采集器并运行 dbt 模型以生成数据。')
    st.stop()

# --- Sidebar Filters ---
projects = st.sidebar.multiselect(
    '选择项目', 
    options=df['project_name'].unique(), 
    default=df['project_name'].unique()
)
filtered_df = df[df['project_name'].isin(projects)]

if filtered_df.empty:
    st.warning("所选项目暂无数据。")
    st.stop()

# --- Latest Snapshot (Cards) ---
st.subheader("📈 最新月度概览 (Latest Snapshot)")

try:
    latest_month = filtered_df['month'].max()
    latest_df = filtered_df[filtered_df['month'] == latest_month]
    
    # Calculate Averages for the selected group
    avg_freq = latest_df['deployment_frequency'].mean()
    avg_lead = latest_df['lead_time_minutes'].mean()
    avg_cfr = latest_df['change_failure_rate_pct'].mean()
    avg_mttr = latest_df['mttr_hours'].mean()
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    def display_kpi(col, title, value, unit, metric_key):
        rating, css = get_dora_rating(metric_key, value)
        with col:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: {'#8F00FF' if css=='elite' else '#00C853' if css=='high' else '#FFAB00' if css=='medium' else '#D50000'};">
                <div style="font-size:12px; color:#aaa;">{title}</div>
                <div style="font-size:24px; font-weight:bold;">{value:.1f} <span style="font-size:14px;">{unit}</span></div>
                <div class="rating-{css}" style="margin-top:5px;">{rating}</div>
            </div>
            """, unsafe_allow_html=True)

    display_kpi(col_kpi1, "发布频率", avg_freq, "次/月", "frequency")
    display_kpi(col_kpi2, "变更前置时间", avg_lead, "分钟", "lead_time")
    display_kpi(col_kpi3, "变更失败率", avg_cfr, "%", "cfr")
    display_kpi(col_kpi4, "平均修复时长", avg_mttr, "小时", "mttr")

except Exception as e:
    st.error(f"无法计算概览数据: {e}")

st.divider()

# --- Detailed Charts ---

# 1. Velocity Metrics
st.markdown("### 💨 交付速度 (Velocity)")
c1, c2 = st.columns(2)

with c1:
    st.markdown("**发布频率 (Deployment Frequency)**")
    fig_df = px.line(
        filtered_df, x='month', y='deployment_frequency', color='project_name', 
        markers=True, template='plotly_dark',
        labels={'deployment_frequency': '每月发布次数', 'month': '月份'}
    )
    fig_df.update_layout(height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_df, use_container_width=True)

with c2:
    st.markdown("**变更前置时间 (Lead Time)**")
    fig_lt = px.line(
        filtered_df, x='month', y='lead_time_minutes', color='project_name',
        markers=True, template='plotly_dark',
        labels={'lead_time_minutes': '前置时间 (分钟)', 'month': '月份'}
    )
    fig_lt.update_layout(height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_lt, use_container_width=True)

# 2. Stability Metrics
st.markdown("### 🛡️ 交付质量 (Stability)")
c3, c4 = st.columns(2)

with c3:
    st.markdown("**变更失败率 (Change Failure Rate)**")
    # Using Bar for CFR to better show magnitude
    fig_cfr = px.bar(
        filtered_df, x='month', y='change_failure_rate_pct', color='project_name',
        barmode='group', template='plotly_dark',
        labels={'change_failure_rate_pct': '失败率 (%)', 'month': '月份'}
    )
    fig_cfr.update_layout(height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    # Add reference line for "High Performer" (< 15%)
    fig_cfr.add_hline(y=15, line_dash="dash", line_color="green", annotation_text="High Performer Limit (15%)")
    st.plotly_chart(fig_cfr, use_container_width=True)

with c4:
    st.markdown("**平均修复时间 (Time to Restore)**")
    fig_mttr = px.line(
        filtered_df, x='month', y='mttr_hours', color='project_name',
        markers=True, template='plotly_dark',
        labels={'mttr_hours': '修复时长 (小时)', 'month': '月份'}
    )
    fig_mttr.update_layout(height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_mttr, use_container_width=True)

# --- Raw Data ---
with st.expander('📊 查看详细数据表'):
    st.dataframe(
        filtered_df.sort_values(['month', 'project_name'], ascending=[False, True]), 
        use_container_width=True,
        column_config={
            "month": "月份",
            "project_name": "项目名称",
            "deployment_frequency": st.column_config.NumberColumn("发布次数", format="%d"),
            "lead_time_minutes": st.column_config.NumberColumn("前置时间(分)", format="%d"),
            "change_failure_rate_pct": st.column_config.NumberColumn("失败率", format="%.2f%%"),
            "mttr_hours": st.column_config.NumberColumn("修复时间(时)", format="%.1f")
        }
    )