
st.set_page_config(page_title="Code Hotspots Radar", page_icon="[Heat]", layout="wide")

# --- Premium Glassmorphism CSS ---
st.markdown("""
<style>
    .reportview-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .risk-tag {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .tag-red { background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .tag-amber { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .tag-clear { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
</style>
""", unsafe_allow_html=True)

st.title("Code Hotspots Radar")
st.markdown("""
<div class="glass-card">
    <strong>Michael Feathers' F-C Analysis</strong>: Identifying technical debt by correlating <strong>Change Frequency</strong> (Churn) with <strong>Code Complexity</strong>.
    <ul>
        <li><span style="color: #ef4444;">●</span> <strong>Hotspots</strong>: High Churn & High Complexity. High risk, bug-prone.</li>
        <li><span style="color: #f59e0b;">●</span> <strong>Stable Core</strong>: Complex but stable. High knowledge value.</li>
        <li><span style="color: #10b981;">●</span> <strong>Peripherals</strong>: Low churn, low complexity. General maintenance.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_data():
    engine = get_db_engine()
    query = "SELECT * FROM fct_code_hotspots"
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

df = load_data()

if df.empty:
    st.info("No data available yet. Please run dbt to build fct_code_hotspots.")
    st.stop()

# --- Sidebar Filters ---
unique_projects = sorted(df['project_id'].unique())
selected_projects = st.sidebar.multiselect("Filter by Project", unique_projects, default=unique_projects)

if selected_projects:
    filtered_df = df[df['project_id'].isin(selected_projects)]
else:
    filtered_df = df

# --- Global KPIs ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.markdown(f'<div class="glass-card"><p>Total Files</p><p class="metric-value">{len(filtered_df)}</p></div>', unsafe_allow_html=True)
with kpi2:
    red_count = len(filtered_df[filtered_df['risk_zone'] == 'RED_ZONE'])
    st.markdown(f'<div class="glass-card"><p>Red Zone (Critical)</p><p class="metric-value" style="background: linear-gradient(90deg, #ef4444, #f87171); -webkit-background-clip: text;">{red_count}</p></div>', unsafe_allow_html=True)
with kpi3:
    avg_churn = round(filtered_df['churn_90d'].mean(), 1)
    st.markdown(f'<div class="glass-card"><p>Avg Churn (90d)</p><p class="metric-value">{avg_churn}</p></div>', unsafe_allow_html=True)
with kpi4:
    max_risk = round(filtered_df['risk_factor'].max(), 1)
    st.markdown(f'<div class="glass-card"><p>Peak Risk Score</p><p class="metric-value">{max_risk}</p></div>', unsafe_allow_html=True)

# --- Main Visualization ---
col_main, col_list = st.columns([2, 1])

with col_main:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Complexity vs Churn Quadrant")
    
    fig = px.scatter(
        filtered_df,
        x="estimated_loc",
        y="churn_90d",
        color="risk_zone",
        size="risk_factor",
        hover_data=["file_path", "project_id", "risk_factor"],
        color_discrete_map={
            "RED_ZONE": "#ef4444",
            "AMBER_ZONE": "#f59e0b",
            "CLEAR": "#10b981"
        },
        labels={
            "estimated_loc": "Complexity (Est. LOC)",
            "churn_90d": "Churn (Last 90d)"
        },
        log_x=True,
        template="plotly_dark"
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_list:
    st.subheader("Critical Hotspots")
    hotspots = filtered_df[filtered_df['risk_zone'] == 'RED_ZONE'].sort_values('risk_factor', ascending=False).head(15)
    
    if not hotspots.empty:
        for _, row in hotspots.iterrows():
            tag_class = "tag-red"
            st.markdown(f"""
            <div class="glass-card" style="padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="font-size: 0.9rem; font-weight: 600; color: #f8fafc; overflow: hidden; text-overflow: ellipsis;">{row['file_path'].split('/')[-1]}</div>
                    <span class="risk-tag {tag_class}">Rank #{row['project_risk_rank']}</span>
                </div>
                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">{row['file_path']}</div>
                <div style="display: flex; gap: 15px; margin-top: 8px; font-size: 0.8rem;">
                    <span>Churn: <b>{row['churn_90d']}</b></span>
                    <span>LOC: <b>{row['estimated_loc']}</b></span>
                    <span style="color: #ef4444;">Risk: <b>{row['risk_factor']}</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No RED_ZONE files detected in selection.")

# --- Detailed View ---
with st.expander("Full Data Explorer"):
    st.dataframe(
        filtered_df[['project_id', 'file_path', 'churn_90d', 'estimated_loc', 'risk_factor', 'risk_zone', 'last_modified_at']]
        .sort_values('risk_factor', ascending=False),
        use_container_width=True
    )
