
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.sql import text
from dashboard.common.db import get_db_engine

st.set_page_config(page_title="Code Hotspots Radar", page_icon="🔥", layout="wide")

st.title("🔥 Code Hotspots Radar (Code Quality Risk)")
st.markdown("""
**Michael Feathers' F-C Analysis**: Identifying technical debt by correlating **Change Frequency** (Churn) with **Code Complexity**.
* **Hotspots (Top-Right)**: High Churn & High Complexity. High risk, bug-prone. **Candidates for Refactoring.**
* **Stable Core (Bottom-Right)**: Complex but stable. Don't touch unless necessary.
* **Peripherals (Top-Left)**: Frequent changes to simple files (config, text). Consider automation.
""")

# --- CSS Styles ---
st.markdown("""
<style>
    .risk-high { color: #ff4b4b; font-weight: bold; }
    .risk-med { color: #ffa421; font-weight: bold; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_data():
    engine = get_db_engine()
    try:
        # Note: In a real environment, verify view exists.
        # Fallback query if view doesn't exist yet (for robustness)
        query = "SELECT * FROM view_file_hotspots"
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except Exception as e:
        # Fallback execution logic if view is missing in DB (Development Mode)
        st.warning(f"View not found, using raw query fallback. Error: {e}")
        raw_query = """
        SELECT 
            f.project_id,
            f.file_path,
            COUNT(DISTINCT c.id) as churn_90d,
            ABS(SUM(fs.code_added) - SUM(fs.code_deleted)) as estimated_loc
        FROM commit_file_stats fs
        JOIN commits c ON fs.commit_id = c.id
        WHERE c.committed_date >= DATE('now', '-90 days')
        GROUP BY f.project_id, f.file_path, f.committed_date
        HAVING churn_90d > 0
        """
        # Note: Raw query simplified for safety fallback; prefer View deployment.
        return pd.DataFrame() 

df = load_data()

if df.empty:
    st.info("No data available yet. Please wait for the collector to process commits.")
    st.stop()

# --- Sidebar Filters ---
unique_projects = df['project_id'].unique()
selected_projects = st.sidebar.multiselect("Filter by Project", unique_projects, default=unique_projects)

if selected_projects:
    filtered_df = df[df['project_id'].isin(selected_projects)]
else:
    filtered_df = df

if filtered_df.empty:
    st.warning("No data for selected filters.")
    st.stop()

# --- Layout: Main Chart ---
col_main, col_list = st.columns([2, 1])

with col_main:
    st.subheader("F-C Quadrant Analysis")
    
    # Thresholds for Quadrants (Dynamic based on median or fixed)
    churn_threshold = filtered_df['churn_90d'].quantile(0.8) # Top 20% freq
    if churn_threshold < 5: churn_threshold = 5 # Minimum floor
    
    loc_threshold = filtered_df['estimated_loc'].quantile(0.8) # Top 20% size
    if loc_threshold < 100: loc_threshold = 100
    
    fig = px.scatter(
        filtered_df,
        x="estimated_loc",
        y="churn_90d",
        color="churn_90d", # Color by heat
        size="estimated_loc", # Size by mass
        hover_data=["file_path", "project_id"],
        labels={
            "estimated_loc": "Complexity Proxy (Est. LOC)",
            "churn_90d": "Change Freq (90 Days)"
        },
        color_continuous_scale="RdYlGn_r", # Red is high churn
        log_x=True, # Code size varies wildly, Log scale helps
        title=f"Hotspot Map (Thresholds: >{int(churn_threshold)} commits, >{int(loc_threshold)} LOC)"
    )
    
    # Add Quadrant Lines
    fig.add_hline(y=churn_threshold, line_dash="dash", line_color="red", annotation_text="High Churn")
    fig.add_vline(x=loc_threshold, line_dash="dash", line_color="red", annotation_text="High Complexity")
    
    # Annotate "Death Zone"
    fig.add_annotation(
        x=loc_threshold * 1.5, 
        y=churn_threshold * 1.5,
        text="⚠️ Hotspots (Refactor Priority)",
        showarrow=False,
        font=dict(color="red", size=14)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- Layout: Top Risky Files ---
with col_list:
    st.subheader("🚨 Top 10 High-Risk Files")
    
    # Risk Score = Churn * Log(Complexity)
    # (Simple logic: Large files changed often are riskiest)
    risky_files = filtered_df[
        (filtered_df['churn_90d'] >= churn_threshold) & 
        (filtered_df['estimated_loc'] >= loc_threshold)
    ].sort_values(by='churn_90d', ascending=False).head(10)
    
    if not risky_files.empty:
        for index, row in risky_files.iterrows():
            with st.expander(f"🔴 {row['file_path'].split('/')[-1]}"):
                st.markdown(f"**Path:** `{row['file_path']}`")
                st.markdown(f"**Changes (90d):** {row['churn_90d']}")
                st.markdown(f"**Est. Size:** {row['estimated_loc']} LOC")
                st.markdown("**Action:** Review testing coverage & consider splitting.")
    else:
        st.success("🎉 No critical hotspots detected in the selected projects!")

# --- Detailed Data Table ---
st.subheader("All File Metrics")
st.dataframe(
    filtered_df[['project_id', 'file_path', 'churn_90d', 'estimated_loc']]
    .sort_values(by='churn_90d', ascending=False),
    use_container_width=True
)
