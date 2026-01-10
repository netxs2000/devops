
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.sql import text
from dashboard.common.db import get_db_engine

st.set_page_config(page_title="R&D Capitalization", page_icon="[Finance]", layout="wide")

# --- Premium Glassmorphism CSS ---
st.markdown("""
<style>
    .reportview-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
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
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #10b981, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .status-tag {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .status-audit { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .status-warning { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .status-info { background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
</style>
""", unsafe_allow_html=True)

st.title("R&D Capitalization & Financial Audit")
st.markdown("""
<div class="glass-card">
    Automatic classification of engineering effort into <strong>Capital Expenditure (CapEx)</strong> and <strong>Operating Expenditure (OpEx)</strong> based on work-item traceability.
</div>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_data():
    engine = get_db_engine()
    try:
        query = "SELECT * FROM public_marts.fct_capitalization_audit"
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.info("No capitalization data. Run dbt to build fct_capitalization_audit.")
    st.stop()

# --- KPIs ---
k1, k2, k3, k4 = st.columns(4)
with k1:
    total_impact = round(df['total_impact'].sum(), 0)
    st.markdown(f'<div class="glass-card"><p>Total Audit Effort</p><p class="metric-value">{total_impact}</p></div>', unsafe_allow_html=True)
with k2:
    capex_total = round(df['capex_impact'].sum(), 0)
    st.markdown(f'<div class="glass-card"><p>Total CapEx Effort</p><p class="metric-value" style="color: #10b981;">{capex_total}</p></div>', unsafe_allow_html=True)
with k3:
    avg_rate = round(df['capitalization_rate'].mean(), 1)
    st.markdown(f'<div class="glass-card"><p>Avg CapEx Rate</p><p class="metric-value">{avg_rate}%</p></div>', unsafe_allow_html=True)
with k4:
    audit_count = len(df[df['audit_status'] == 'AUDIT_READY'])
    st.markdown(f'<div class="glass-card"><p>Audit-Ready Batches</p><p class="metric-value">{audit_count}</p></div>', unsafe_allow_html=True)

# --- Capitalization Trend ---
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.subheader("Financial Distribution Trend (Weekly)")

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df['audit_week'], y=df['capex_impact'],
    name='CapEx (New Features)',
    marker_color='#10b981'
))
fig.add_trace(go.Bar(
    x=df['audit_week'], y=df['opex_impact'],
    name='OpEx (Maintenance)',
    marker_color='#ef4444'
))

fig.update_layout(
    barmode='stack',
    template="plotly_dark",
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    xaxis=dict(title="Week Segment"),
    yaxis=dict(title="Effort Unit (Impact Score)")
)
st.plotly_chart(fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Detailed Project Audit ---
st.subheader("Project Financial Ledger")
for _, row in df.head(15).iterrows():
    status_class = "status-info"
    if row['audit_status'] == 'AUDIT_READY': status_class = "status-audit"
    elif row['audit_status'] == 'HIGH_CAPEX_INSPECTION_REQUIRED': status_class = "status-warning"
    
    with st.expander(f"Project: {row['project_id']} - Week {row['audit_week']}"):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**CapEx Effort:** {row['capex_impact']}")
        c2.write(f"**OpEx Effort:** {row['opex_impact']}")
        c3.write(f"**Rate:** {row['capitalization_rate']}%")
        st.markdown(f"**Audit Status:** <span class='status-tag {status_class}'>{row['audit_status']}</span>", unsafe_allow_html=True)

# --- Full Ledger ---
with st.expander("Financial Data Explorer"):
    st.dataframe(df, use_container_width=True)