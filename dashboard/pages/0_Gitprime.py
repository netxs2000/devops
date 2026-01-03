"""Developer Value Contribution Leaderboard (ELOC).

此页面展示基于代码当量 (ELOC) 的开发人员价值贡献榜。
核心指标包括 ELOC 分数、Impact (影响力)、Churn Rate (近期代码重写率) 以及 Sherpa Score (协作贡献)。
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from devops_collector.config import settings

# Page Configuration
st.set_page_config(
    page_title="GitPrime Engineering Insights",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 5px;
        color: #B0B0B0;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #262730;
        color: #FFD700;
        border-bottom: 2px solid #FFD700;
    }
</style>
""", unsafe_allow_html=True)

# Database Connection
@st.cache_resource
def get_db_engine():
    """Create and cache the database engine connection.

    Returns:
        sqlalchemy.engine.Engine: Database engine instance.
    """
    return create_engine(settings.database.uri)

def load_data():
    """Loads leaderboard data from database with fallback logic."""
    engine = get_db_engine()
    
    # Query trying to join all metrics including Collaboration (Reviews)
    query_full = """
    SELECT 
        u.full_name,
        u.department_id,
        u.primary_email,
        COALESCE(SUM(cm.eloc_score), 0) as eloc_score,
        COALESCE(SUM(cm.impact_score), 0) as impact_score,
        COALESCE(SUM(cm.churn_lines), 0) as churn_lines,
        COALESCE(SUM(cm.raw_additions), 0) as raw_additions,
        COALESCE(SUM(cm.test_lines), 0) as test_lines,
        COALESCE(AVG(cm.refactor_ratio), 0) as refactor_ratio,
        COALESCE(SUM(dds.review_count), 0) as review_count,
        count(distinct cm.commit_id) as commits_90d,
        count(distinct date(cm.committed_at)) as active_days
    FROM mdm_identities u
    LEFT JOIN commit_metrics cm ON u.primary_email = cm.author_email 
        AND cm.committed_at >= NOW() - INTERVAL '90 days'
    LEFT JOIN daily_dev_stats dds ON u.id = dds.user_id 
        AND dds.date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY u.full_name, u.department_id, u.primary_email, u.id
    HAVING SUM(cm.eloc_score) > 0 OR SUM(dds.review_count) > 0
    ORDER BY impact_score DESC;
    """
    
    # Fallback query
    query_basic = """
    SELECT 
        u.full_name,
        u.department_id,
        u.primary_email,
        COALESCE(SUM(cm.eloc_score), 0) as eloc_score,
        COALESCE(SUM(cm.impact_score), 0) as impact_score,
        COALESCE(SUM(cm.churn_lines), 0) as churn_lines,
        COALESCE(SUM(cm.raw_additions), 0) as raw_additions,
        COALESCE(SUM(cm.test_lines), 0) as test_lines,
        COALESCE(AVG(cm.refactor_ratio), 0) as refactor_ratio,
        0 as review_count,
        count(distinct cm.commit_id) as commits_90d,
        count(distinct date(cm.committed_at)) as active_days
    FROM mdm_identities u
    LEFT JOIN commit_metrics cm ON u.primary_email = cm.author_email 
        AND cm.committed_at >= NOW() - INTERVAL '90 days'
    GROUP BY u.full_name, u.department_id, u.primary_email
    HAVING SUM(cm.eloc_score) > 0
    ORDER BY impact_score DESC;
    """

    try:
        with engine.connect() as conn:
             df = pd.read_sql(text(query_full), conn)
    except Exception as e:
        with engine.connect() as conn:
            df = pd.read_sql(text(query_basic), conn)
            
    return df

def process_metrics(df):
    """Process raw metrics into derived KPIs and ranks.

    Calculates Churn Rate, Test Rate, Refactor Intensity, and Sherpa Score.
    Assigns contributor levels based on ELOC rank.

    Args:
        df (pd.DataFrame): Raw metrics dataframe.

    Returns:
        pd.DataFrame: Processed dataframe with extra columns.
    """
    if df.empty:
        return df
        
    # Calculate Ratios
    df['churn_rate'] = df.apply(lambda x: (x['churn_lines'] / x['raw_additions'] * 100) if x['raw_additions'] > 0 else 0, axis=1)
    df['test_rate'] = df.apply(lambda x: (x['test_lines'] / x['raw_additions'] * 100) if x['raw_additions'] > 0 else 0, axis=1)
    df['refactor_intensity'] = df['refactor_ratio'] * 100
    
    # Assign Levels based on Rank (Dense Rank)
    df['rank'] = df['eloc_score'].rank(method='dense', ascending=False)
    
    def get_level(rank):
        if rank <= 3: return 'Elite'
        if rank <= 10: return 'Core'
        if rank <= 30: return 'Contributor'
        return 'Member'
        
    df['level'] = df['rank'].apply(get_level)
    
    # Sherpa Score (Placeholder logic: 1 review = 5 points)
    df['sherpa_score'] = df['review_count'] * 5 
    
    # TTF Placeholder
    df['ttf'] = "N/A" 
    
    return df

# Main UI
st.title("🌊 GitPrime Engineering Insights")
st.markdown("""
<div style='background-color:rgba(255, 215, 0, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #FFD700;'>
    <b>GitPrime Core Metrics</b><br>
    Focusing on <b>Impact</b> (Legacy Value), <b>Active Days</b> (Coding Focus), and <b>Efficiency</b> (Churn Analysis).
</div>
""", unsafe_allow_html=True)
st.button("Refresh Data", on_click=st.cache_resource.clear)

raw_df = load_data()
df = process_metrics(raw_df)

if df.empty:
    st.info("No data available yet. Please run the collector to generate metrics.")
else:
    # --- Top Stats Banner ---
    top_row = st.columns(4)
    file_impact = df['impact_score'].sum()
    total_churn = df['churn_lines'].sum()
    avg_churn = df['churn_rate'].mean()
    
    with top_row[0]:
        st.metric("Total Team Impact", f"{file_impact:,.0f}", help="Sum of Impact Score (ELOC * Legacy Factor)")
    with top_row[1]:
        st.metric("Avg Churn Rate", f"{avg_churn:.1f}%", help="Percentage of code rewritten shortly after merge")
    with top_row[2]:
        st.metric("Avg Active Days", f"{df['active_days'].mean():.1f}", help="Average number of coding days per engineer (90d)")
    with top_row[3]:
        st.metric("Top Sheriff", df.sort_values('sherpa_score', ascending=False).iloc[0]['full_name'] if not df.empty else "N/A")

    st.markdown("---")

    # --- Tabs ---
    tab_value, tab_quality, tab_collab = st.tabs([
        "💎 Value Creation (ELOC & Impact)", 
        "🛡️ Quality & Efficiency (Churn & TTF)", 
        "🤝 Collaboration (Sherpa Score)"
    ])

    # === Tab 1: Value ===
    with tab_value:
        st.caption("Focus: Code production, Complexity weighting, Legacy Refactoring Impact.")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_val = px.scatter(
                df, x="commits_90d", y="impact_score", size="eloc_score", color="level",
                hover_data=["full_name", "churn_rate"],
                text="full_name",
                title="Impact vs. Activity",
                labels={"impact_score": "Impact (Value)", "commits_90d": "Commits (90d)"},
                color_discrete_map={"Elite": "#FFD700", "Core": "#C0C0C0", "Contributor": "#CD7F32", "Member": "#808080"}
            )
            fig_val.update_traces(textposition='top center')
            st.plotly_chart(fig_val, use_container_width=True)
            
        with c2:
            st.subheader("Leaderboard (by Impact)")
            st.dataframe(
                df[['rank', 'full_name', 'impact_score', 'active_days', 'level']].sort_values('impact_score', ascending=False),
                column_config={
                    "rank": "Rank",
                    "impact_score": st.column_config.NumberColumn("Impact", format="%d"),
                    "active_days": st.column_config.NumberColumn("📅 Active Days", format="%d")
                },
                hide_index=True,
                use_container_width=True
            )

    # === Tab 2: Quality ===
    with tab_quality:
        st.caption("Focus: Code Stability (Churn), Turnaround Time (TTF). Lower Churn is better.")
        
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            # Churn Rate Bar Chart
            fig_churn = px.bar(
                df.sort_values('churn_rate', ascending=True).head(15), 
                x="churn_rate", y="full_name", orientation='h',
                title="Lowest Churn Rate (Top Stability)",
                labels={"churn_rate": "Churn Rate %", "full_name": "Developer"},
                color="churn_rate", color_continuous_scale="RdYlGn_r" # Green is low churn
            )
            st.plotly_chart(fig_churn, use_container_width=True)
            
        with col_q2:
            st.subheader("Quality Metrics Detail")
            st.dataframe(
                df[['full_name', 'churn_rate', 'test_rate', 'refactor_intensity', 'ttf']],
                column_config={
                    "churn_rate": st.column_config.ProgressColumn("Churn %", format="%.1f%%", min_value=0, max_value=100),
                    "test_rate": st.column_config.NumberColumn("Test Coverage %", format="%.1f%%"),
                    "refactor_intensity": st.column_config.NumberColumn("Refactor %", format="%.1f%%"),
                    "ttf": "Time to Fix (Hours)"
                },
                hide_index=True,
                use_container_width=True
            )

    # === Tab 3: Collaboration ===
    with tab_collab:
        st.caption("Focus: Code Review contributions, Mentorship (Sherpa Score).")
        
        col_c1, col_c2 = st.columns([1, 2])
        
        with col_c1:
            st.metric("Total Reviews (90d)", f"{df['review_count'].sum():,.0f}")
            st.markdown("##### What is Sherpa Score?")
            st.info("""
            **Sherpa Score** measures a developer's contribution to helping others 'climb'.
            Calculated based on Code Reviews Code Comments, and Mentorship activities.
            """)
        
        with col_c2:
            st.subheader("Sherpa Leaderboard")
            st.dataframe(
                df[['rank', 'full_name', 'review_count', 'sherpa_score']].sort_values('sherpa_score', ascending=False),
                column_config={
                    "rank": "Rank",
                    "review_count": st.column_config.NumberColumn("Reviews Done"),
                    "sherpa_score": st.column_config.ProgressColumn("Sherpa Score", format="%d", max_value=max(df['sherpa_score'].max(), 100))
                },
                hide_index=True,
                use_container_width=True
            )

    st.markdown("---")
    st.caption(f"*Data updated via DevOps Collector. Last analysis includes rolling 90 days.*")
