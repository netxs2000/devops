"""Developer Value Contribution Leaderboard (ELOC).

此页面展示基于代码当量 (ELOC) 的开发人员价值贡献榜。
核心指标包括 ELOC 分数、测试覆盖率贡献、文档贡献率以及重构强度。
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from devops_collector.config import settings

# Page Configuration
st.set_page_config(
    page_title="Developer Value Leaderboard",
    page_icon="CODE",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database Connection
@st.cache_resource
def get_db_engine():
    return create_engine(settings.database.uri)

def load_data():
    """Loads leaderboard data from the SQL view."""
    engine = get_db_engine()
    query = """
    SELECT 
        rank_position,
        full_name,
        department_id,
        eloc_score,
        commits_90d,
        "test_coverage_rate%",
        "doc_contribution_rate%",
        "refactor_intensity%",
        contributor_level
    FROM view_leaderboard_value_contribution
    ORDER BY rank_position ASC;
    """
    try:
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Main UI
st.title("Developer Value Contribution Leaderboard")
st.markdown("""
> **ELOC (Equivalent Lines of Code)**: A fairer metric than raw lines of code. 
> It weights contributions based on code complexity, documentation value, test coverage, and refactoring efforts.
""")

df = load_data()

if df.empty:
    st.info("No data available yet. Please run the collector to generate metrics.")
else:
    # Top Stats Row
    col1, col2, col3, col4 = st.columns(4)
    
    top_dev = df.iloc[0]
    total_eloc = df['eloc_score'].sum()
    avg_test_rate = df['test_coverage_rate%'].mean()
    
    with col1:
        st.metric(label="Top Contributor", value=top_dev['full_name'], delta=f"{top_dev['eloc_score']:.0f} ELOC")
    with col2:
        st.metric(label="Total Team Value", value=f"{total_eloc:,.0f}", help="Total ELOC across all developers")
    with col3:
        st.metric(label="Avg Test Contribution", value=f"{avg_test_rate:.1f}%", help="Average percentage of code that is tests")
    with col4:
        st.metric(label="Active Contributors", value=len(df), help="Developers with commits in last 90 days")

    st.divider()

    # 1. Bubble Chart: ELOC vs Commits vs Refactoring
    # X=Commits, Y=ELOC, Size=Refactor, Color=Level
    st.subheader("Contribution Efficiency Matrix")
    st.caption("Are developers committing often but adding little value? Or few commits with high impact?")
    
    fig = px.scatter(
        df, 
        x="commits_90d", 
        y="eloc_score",
        size="refactor_intensity%", 
        color="contributor_level",
        hover_name="full_name",
        text="full_name",
        labels={
            "commits_90d": "Commit Frequency (90d)",
            "eloc_score": "Value Output (ELOC)",
            "refactor_intensity%": "Refactor Intensity",
            "contributor_level": "Level"
        },
        title="Impact vs. Effort Analysis",
        color_discrete_map={
            "Elite": "#FFD700",
            "Core": "#C0C0C0", 
            "Contributor": "#CD7F32",
            "Member": "#A0A0A0"
        },
        height=500
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # 2. Detailed Leaderboard Table
    st.subheader("Detailed Rankings")
    
    # Styling the dataframe
    def highlight_elite(row):
        if row['contributor_level'] == 'Elite':
            return ['background-color: rgba(255, 215, 0, 0.1)'] * len(row)
        return [''] * len(row)

    st.dataframe(
        df.style.apply(highlight_elite, axis=1).format({
            "eloc_score": "{:,.1f}",
            "test_coverage_rate%": "{:.1f}%",
            "doc_contribution_rate%": "{:.1f}%",
            "refactor_intensity%": "{:.1f}%"
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "rank_position": st.column_config.NumberColumn("Rank", width="small"),
            "full_name": "Developer",
            "department_id": "Department",
            "eloc_score": st.column_config.ProgressColumn(
                "Value Score (ELOC)", 
                format="%.1f", 
                min_value=0, 
                max_value=df['eloc_score'].max()
            ),
            "commits_90d": st.column_config.NumberColumn("Commits", width="small"),
            "test_coverage_rate%": st.column_config.NumberColumn("Tests %", format="%.1f%%"),
            "doc_contribution_rate%": st.column_config.NumberColumn("Docs %", format="%.1f%%"),
            "refactor_intensity%": st.column_config.NumberColumn("Refactor %", format="%.1f%%"),
            "contributor_level": "Level"
        }
    )

    st.markdown("---")
    st.caption("*Data updated daily via DevOps Collector ETL pipeline.*")
