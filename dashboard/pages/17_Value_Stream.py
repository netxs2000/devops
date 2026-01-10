
"""Value Stream Management Dashboard (Flow Framework).

This dashboard implements the Mik Kersten's Flow Framework metrics:
- Flow Distribution: What type of value are we delivering? (Feature/Defect/Debt/Risk)
- Flow Velocity: How much value are we delivering?
- Flow Time: How fast is value delivered?
- Flow Load: Is demand outstripping capacity? (WIP)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from dashboard.common.db import get_db_engine

st.set_page_config(page_title="Value Stream Management", page_icon="🌊", layout="wide")

st.title("🌊 Value Stream Management (Flow Framework)")
st.caption("Visualizing the flow of business value through the software delivery lifecycle.")

st.markdown("""
<style>
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 15px;
    }
    .flow-feature { color: #5B9BD5; font-weight: bold; }
    .flow-defect { color: #C00000; font-weight: bold; }
    .flow-debt { color: #FFC000; font-weight: bold; }
    .flow-risk { color: #ED7D31; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_flow_data():
    engine = get_db_engine()
    
    try:
        # v3.0 Update: Use dws layer
        query = "SELECT * FROM public_marts.dws_flow_metrics_weekly"
        with engine.connect() as conn:
            df_weekly = pd.read_sql(text(query), conn)
            
        # Raw items for scatter
        query_items = "SELECT * FROM public_marts.view_flow_items WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'"
        with engine.connect() as conn:
            df_items = pd.read_sql(text(query_items), conn)
            
        return df_weekly, df_items
        
    except Exception as e:
        st.warning(f"无法加载价值流数据 (dws_flow_metrics_weekly)。请运行 dbt 模型。错误: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_weekly, df_items = load_flow_data()

if df_weekly.empty:
    st.info("No Flow data available. Ensure issues are synced and labeled correctly.")
    st.stop()

# --- Sidebar Filters ---
projects = df_weekly['project_id'].unique() # Note: View returns ID, usually join name in View or here
if 'project_id' in df_weekly.columns:
     # Simple filter if logic complex
     pass

# --- 1. Flow Distribution (Allocation) ---
st.subheader("1. Flow Distribution (Allocations)")
st.caption("Are we investing enough in Debt and Risk? Or drowning in Defects?")

# Prepare Stacked Data
fd_chart_data = df_weekly.sort_values('metric_week')

fig_dist = go.Figure()
fig_dist.add_trace(go.Bar(name='Features', x=fd_chart_data['metric_week'], y=fd_chart_data['closed_features'], marker_color='#5B9BD5'))
fig_dist.add_trace(go.Bar(name='Defects', x=fd_chart_data['metric_week'], y=fd_chart_data['closed_defects'], marker_color='#C00000'))
fig_dist.add_trace(go.Bar(name='Debts', x=fd_chart_data['metric_week'], y=fd_chart_data['closed_debts'], marker_color='#FFC000'))
fig_dist.add_trace(go.Bar(name='Risks', x=fd_chart_data['metric_week'], y=fd_chart_data['closed_risks'], marker_color='#ED7D31'))

fig_dist.update_layout(barmode='stack', title="Weekly Work Distribution", height=400, xaxis_title="Week", yaxis_title="Items Completed")
st.plotly_chart(fig_dist, use_container_width=True)

# --- 2. Flow Velocity & Time ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("2. Flow Velocity")
    st.caption("Throughput of value delivered per week.")
    fig_vel = px.line(fd_chart_data, x='metric_week', y='flow_velocity', markers=True, title="Items Completed per Week")
    fig_vel.update_traces(line_color='#00B050', line_width=3)
    st.plotly_chart(fig_vel, use_container_width=True)

with c2:
    st.subheader("3. Flow Time Analysis")
    st.caption("How long does it take to deliver value? (Cycle Time)")
    if not df_items.empty:
        # Scatter plot of recent items
        fig_time = px.scatter(
            df_items, x='closed_at', y='flow_time_days', color='flow_type',
            color_discrete_map={'Feature': '#5B9BD5', 'Defect': '#C00000', 'Debt': '#FFC000', 'Risk': '#ED7D31'},
            hover_data=['title', 'project_name'],
            title="Time to Close (Days) by Item"
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No closed items found for timing analysis.")

# --- 4. Current Flow Load (WIP) ---
st.subheader("4. Current Flow Load (WIP)")
st.caption("Snapshot of currently open work items. High WIP = Bottleneck.")

# Calculate current WIP from items view (Active items)
# Note: Re-querying view might be better for real-time listing, but reusing cached df_items is safer for now if we load 'opened' too.
# For simplicity, we query a summary now.
try:
    engine = get_db_engine()
    with engine.connect() as conn:
        wip_query = """
        SELECT flow_type, count(*) as count 
        FROM public_marts.view_flow_items 
        WHERE state = 'opened' 
        GROUP BY flow_type
        """
        wip_df = pd.read_sql(text(wip_query), conn)
    
    if not wip_df.empty:
        fig_wip = px.pie(
            wip_df, values='count', names='flow_type', 
            color='flow_type',
            color_discrete_map={'Feature': '#5B9BD5', 'Defect': '#C00000', 'Debt': '#FFC000', 'Risk': '#ED7D31'},
            title="Current Active Work Breakdown",
            hole=0.4
        )
        c_wip1, c_wip2 = st.columns([1, 2])
        with c_wip1:
            st.metric("Total WIP Items", wip_df['count'].sum())
            st.write(wip_df.set_index('flow_type'))
        with c_wip2:
            st.plotly_chart(fig_wip, use_container_width=True)
            
except Exception as e:
    st.error(f"Error loading WIP: {e}")

# --- Insights ---
st.divider()
st.markdown("### 🧠 Value Stream Insights")

# Logic-based insights
total_items = fd_chart_data['flow_velocity'].sum()
defect_ratio = fd_chart_data['closed_defects'].sum() / total_items if total_items > 0 else 0
debt_ratio = fd_chart_data['closed_debts'].sum() / total_items if total_items > 0 else 0

if defect_ratio > 0.4:
    st.error(f"🚨 **Quality Crisis**: {defect_ratio:.1%} of recent work is Defects (Target: < 20%). Innovation is stalled.")
elif defect_ratio > 0.2:
    st.warning(f"⚠️ **High Failure Demand**: {defect_ratio:.1%} is Defects. Investigate testing practices.")

if debt_ratio < 0.1:
    st.warning(f"⚠️ **Tech Debt Pile-up**: Only {debt_ratio:.1%} invested in Debt/Refactoring. Future velocity is at risk.")

st.success(f"ℹ️ **Feature Allocation**: {1 - defect_ratio - debt_ratio:.1%} of capacity is delivering new business value.")
