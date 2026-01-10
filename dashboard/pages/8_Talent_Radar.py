
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.sql import text
from dashboard.common.db import get_db_engine

st.set_page_config(page_title="Talent Radar", page_icon="[Talent]", layout="wide")

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
    .archetype-tag {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .arch-specialist { background: rgba(168, 85, 247, 0.2); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); }
    .arch-leader { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
    .arch-contributor { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .arch-active { background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
</style>
""", unsafe_allow_html=True)

st.title("Talent Radar & Knowledge Map")
st.markdown("""
<div class="glass-card">
    Identifying technical leadership through <strong>implicit impact</strong>, <strong>collaboration</strong>, and <strong>knowledge domain depth</strong>.
</div>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_talent_data():
    engine = get_db_engine()
    try:
        query = "SELECT * FROM public_marts.fct_talent_radar"
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_bus_factor():
    engine = get_db_engine()
    try:
        query = "SELECT * FROM public_marts.dws_subsystem_bus_factor WHERE knowledge_risk_status != 'HEALTHY_DISTRIBUTION'"
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except:
        return pd.DataFrame()

df = load_talent_data()
df_risk = load_bus_factor()

if df.empty:
    st.info("No talent data. Please run dbt to build fct_talent_radar.")
    st.stop()

# --- Sidebar Filters ---
unique_depts = sorted(df['department_id'].fillna('Unknown').unique())
selected_depts = st.sidebar.multiselect("Filter by Department", unique_depts, default=unique_depts)

if selected_depts:
    filtered_df = df[df['department_id'].isin(selected_depts)]
else:
    filtered_df = df

# --- KPIs ---
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="glass-card"><p>Top Talents</p><p class="metric-value">{len(filtered_df[filtered_df["talent_influence_index"] > 50])}</p></div>', unsafe_allow_html=True)
with k2:
    specialists = len(filtered_df[filtered_df["talent_archetype"] == "Domain Specialist"])
    st.markdown(f'<div class="glass-card" style="border-left: 4px solid #a855f7;"><p>Domain Specialists</p><p class="metric-value" style="background: linear-gradient(90deg, #a855f7, #ec4899); -webkit-background-clip: text;">{specialists}</p></div>', unsafe_allow_html=True)
with k3:
    avg_domains = round(filtered_df['metric_knowledge_domains'].mean(), 1)
    st.markdown(f'<div class="glass-card"><p>Avg Knowledge Domains</p><p class="metric-value">{avg_domains}</p></div>', unsafe_allow_html=True)
with k4:
    risk_count = len(df_risk)
    st.markdown(f'<div class="glass-card" style="border-left: 4px solid #ef4444;"><p>Bus Factor Risks</p><p class="metric-value" style="background: linear-gradient(90deg, #ef4444, #f87171); -webkit-background-clip: text;">{risk_count}</p></div>', unsafe_allow_html=True)

# --- Visualization ---
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Influence Matrix: Collaboration vs Knowledge")
    
    fig = px.scatter(
        filtered_df,
        x="metric_knowledge_domains",
        y="metric_review_comments",
        size="talent_influence_index",
        color="talent_archetype",
        hover_name="real_name",
        hover_data=["department_id", "talent_influence_index"],
        color_discrete_map={
            "Domain Specialist": "#a855f7",
            "Collaborative Leader": "#38bdf8",
            "Reliable Contributor": "#10b981",
            "Active Engineer": "#94a3b8"
        },
        template="plotly_dark"
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Owned Knowledge Domains", showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(title="Review Comments (90d)", showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.subheader("Leadership Leaderboard")
    top_talents = filtered_df.sort_values('talent_influence_index', ascending=False).head(10)
    
    for _, row in top_talents.iterrows():
        arch_class = "arch-active"
        if row['talent_archetype'] == 'Domain Specialist': arch_class = "arch-specialist"
        elif row['talent_archetype'] == 'Collaborative Leader': arch_class = "arch-leader"
        elif row['talent_archetype'] == 'Reliable Contributor': arch_class = "arch-contributor"
        
        st.markdown(f"""
        <div class="glass-card" style="padding: 12px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="font-weight: 600; color: #f8fafc;">{row['real_name']}</div>
                <span class="archetype-tag {arch_class}">{row['talent_archetype']}</span>
            </div>
            <div style="font-size: 0.75rem; color: #94a3b8;">{row['department_id']}</div>
            <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.85rem;">
                <span style="color: #38bdf8;">Index: <b>{row['talent_influence_index']}</b></span>
                <span style="color: #94a3b8;">Domains: <b>{row['metric_knowledge_domains']}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- Bus Factor Risk Warning ---
if not df_risk.empty:
    st.markdown('<div class="glass-card" style="border-top: 2px solid #ef4444;">', unsafe_allow_html=True)
    st.subheader("Critical Knowledge Risks (Bus Factor)")
    st.warning("The following sub-systems are heavily dependent on a single contributor.")
    
    # Simple table for risks
    risk_display = df_risk[['project_id', 'subsystem', 'contributor_count', 'subsystem_ownership_pct', 'knowledge_risk_status']]
    st.table(risk_display.head(10))
    st.markdown('</div>', unsafe_allow_html=True)

# --- Raw Data ---
with st.expander("Explore Full Talent Data"):
    st.dataframe(filtered_df.sort_values('talent_influence_index', ascending=False), use_container_width=True)