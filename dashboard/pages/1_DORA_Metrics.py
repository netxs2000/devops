
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy.sql import text
from dashboard.common.db import get_db_engine

st.set_page_config(page_title="DORA Metrics", page_icon="[DORA]", layout="wide")

# --- Premium Glassmorphism CSS ---
st.markdown("""
<style>
    .reportview-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    .main { background: transparent; }
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .rating-tag {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .rating-elite { background: rgba(168, 85, 247, 0.2); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); }
    .rating-high { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
    .rating-medium { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .rating-low { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
</style>
""", unsafe_allow_html=True)

st.title("DORA Core Performance Indicators")
st.markdown("""
<div class="glass-card">
    High-fidelity engineering throughput and stability metrics based on the <strong>DORA Research Framework</strong>.
</div>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_dora_data():
    engine = get_db_engine()
    try:
        query = "SELECT * FROM fct_dora_metrics"
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except:
        return pd.DataFrame()

df = load_dora_data()

if df.empty:
    st.info("No DORA data. Please run dbt to build fct_dora_metrics.")
    st.stop()

# --- Sidebar Filters ---
unique_projects = sorted(df['project_name'].unique())
selected_projects = st.sidebar.multiselect("Filter by Project", unique_projects, default=unique_projects)

if selected_projects:
    filtered_df = df[df['project_name'].isin(selected_projects)]
else:
    filtered_df = df

# --- Global KPIs (Latest Average) ---
latest_month = filtered_df['month'].max()
latest_df = filtered_df[filtered_df['month'] == latest_month]

k1, k2, k3, k4 = st.columns(4)
with k1:
    val = round(latest_df['deployment_frequency'].mean(), 1)
    st.markdown(f'<div class="glass-card"><p>Deployment Frequency</p><p class="metric-value">{val}</p><div style="font-size:0.8rem; color:#94a3b8;">deploys / month</div></div>', unsafe_allow_html=True)
with k2:
    val = round(latest_df['lead_time_hours'].mean(), 1)
    st.markdown(f'<div class="glass-card"><p>Lead Time for Changes</p><p class="metric-value">{val}</p><div style="font-size:0.8rem; color:#94a3b8;">hours (avg)</div></div>', unsafe_allow_html=True)
with k3:
    val = round(latest_df['change_failure_rate_pct'].mean(), 1)
    st.markdown(f'<div class="glass-card"><p>Change Failure Rate</p><p class="metric-value">{val}%</p><div style="font-size:0.8rem; color:#94a3b8;">production failures</div></div>', unsafe_allow_html=True)
with k4:
    elite_pct = round(len(latest_df[latest_df['performance_rating'] == 'ELITE']) * 100.0 / len(latest_df), 1)
    st.markdown(f'<div class="glass-card"><p>Elite Team Ratio</p><p class="metric-value">{elite_pct}%</p><div style="font-size:0.8rem; color:#94a3b8;">of all selected projects</div></div>', unsafe_allow_html=True)

# --- Visualizations ---
col_v, col_s = st.columns(2)

with col_v:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Throughput & Delivery Efficiency")
    fig = px.line(
        filtered_df,
        x="month",
        y="lead_time_hours",
        color="project_name",
        markers=True,
        template="plotly_dark",
        labels={"lead_time_hours": "Lead Time (Hours)", "month": "Month"}
    )
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_s:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Process Waste: Wait vs Work")
    # Stacked bar for wait vs work time
    fig = go.Figure()
    # Aggregate by month for the chart
    monthly_agg = filtered_df.groupby('month').agg({'wait_time_hours': 'mean', 'work_time_hours': 'mean'}).reset_index()
    
    fig.add_trace(go.Bar(name='Wait (Pickup Delay)', x=monthly_agg['month'], y=monthly_agg['wait_time_hours'], marker_color='#ef4444'))
    fig.add_trace(go.Bar(name='Work (Review Effort)', x=monthly_agg['month'], y=monthly_agg['work_time_hours'], marker_color='#10b981'))
    
    fig.update_layout(barmode='stack', template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Bottleneck Deep Dive ---
st.subheader("Process Bottleneck Analysis")
for _, row in latest_df.head(10).iterrows():
    rating_class = f"rating-{row['performance_rating'].lower()}"
    
    with st.expander(f"Project: {row['project_name']} - Rating: {row['performance_rating']}"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wait Time", f"{row['wait_time_hours']:.1f}h")
        c2.metric("Review Time", f"{row['work_time_hours']:.1f}h")
        c3.markdown(f"**Bottleneck:** `{row['primary_bottleneck']}`")
        c4.markdown(f"**Performance:** <span class='rating-tag {rating_class}'>{row['performance_rating']}</span>", unsafe_allow_html=True)

# --- Full Data ---
with st.expander("Explore Full DORA Data"):
    st.dataframe(filtered_df.sort_values('month', ascending=False), use_container_width=True)