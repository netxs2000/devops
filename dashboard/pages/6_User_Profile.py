"""Developer DNA & Activity Profile Dashboard."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import run_query, set_page_config


# --- Configuration & Styling ---
set_page_config()
st.title("👤 开发者 DNA 画像 (Developer Analytics)")
st.caption("基于 OneID 体系，全方位透视研发人员的贡献度、技术影响力与协作风格。")

st.markdown(
    """
<style>
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    .dna-archetype {
        font-size: 1.2rem;
        font-weight: 600;
        color: #00d4ff;
        background: rgba(0, 212, 255, 0.1);
        padding: 5px 15px;
        border-radius: 50px;
        display: inline-block;
        margin-bottom: 10px;
    }
    .metric-val {
        font-size: 2.2rem;
        font-weight: bold;
        color: white;
    }
    .metric-label {
        color: #aaa;
        font-size: 0.8rem;
        text-transform: uppercase;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- Data Loading ---
try:
    users_df = run_query("SELECT user_id, real_name, department FROM public_marts.fct_developer_activity_profile")
    if users_df.empty:
        st.warning("暂无开发者画像数据。请确认 dbt 模型 `fct_developer_activity_profile` 已运行。")
        st.stop()
except Exception as e:
    st.error(f"数据查询失败: {e}")
    st.stop()

selected_user_name = st.selectbox("🔍 搜索开发者 (姓名/ID)", users_df["real_name"].unique())
selected_user_id = users_df[users_df["real_name"] == selected_user_name]["user_id"].iloc[0]

# Detailed User Profile
profile_df = run_query(
    f"SELECT * FROM public_marts.fct_developer_activity_profile WHERE user_id = '{selected_user_id}'"
)
if profile_df.empty:
    st.error("无法获取该开发者的详细信息。")
    st.stop()

row = profile_df.iloc[0]

# --- UI Layout: Top DNA Section ---
col_info, col_radar = st.columns([1, 1.2])

with col_info:
    st.markdown(
        f"""
    <div class="glass-card">
        <div class="dna-archetype">🧬 {row["developer_archetype"]}</div>
        <h2 style="margin:0; color:white;">{row["real_name"]}</h2>
        <div style="color:#888; margin-bottom:20px;">{row["department"]} | Tech Impact Leader</div>
        
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
            <div>
                <div class="metric-label">影响力总分</div>
                <div class="metric-val">{row["total_impact_score"]:.0f}</div>
            </div>
            <div>
                <div class="metric-label">日均产出率</div>
                <div class="metric-val">{row["daily_velocity"]:.2f}</div>
            </div>
            <div>
                <div class="metric-label">提交代码数</div>
                <div class="metric-val">{row["commit_count"]}</div>
            </div>
            <div>
                <div class="metric-label">评审贡献数</div>
                <div class="metric-val">{row["review_comment_count"]}</div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col_radar:
    categories = ["代码产出", "评审质量", "协作敏捷度", "需求交付"]
    # Normalizing values for the radar (example ratios)
    values = [row["commit_count"], row["review_comment_count"], row["mr_open_count"], row["issue_closed_count"]]
    max_v = max(values) if max(values) > 0 else 1

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            name=row["real_name"],
            line=dict(color="#00d4ff", width=3),
            fillcolor="rgba(0, 212, 255, 0.2)",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max_v]), bgcolor="rgba(0,0,0,0)"),
        showlegend=False,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=450,
        margin=dict(t=50, b=50, l=50, r=50),
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Contribution Trend (Daily Activity) ---
st.subheader("📊 近期活跃度趋势 (Daily Activity Stream)")
activity_query = f"""
    SELECT metric_date, activity_count 
    FROM public_marts.dws_developer_metrics_daily 
    WHERE master_user_id = (SELECT master_user_id FROM public_staging.stg_mdm_identities WHERE user_id = '{selected_user_id}' LIMIT 1)
    ORDER BY metric_date ASC
"""
activity_df = run_query(activity_query)
if not activity_df.empty:
    fig_trend = px.area(
        activity_df, x="metric_date", y="activity_count", color_discrete_sequence=["#8F00FF"], template="plotly_dark"
    )
    fig_trend.update_layout(height=300, margin=dict(t=20, b=20))
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("该用户近期无活跃数据记录。")

# --- Leaderboard ---
st.divider()
st.subheader("🏆 全站研发影响力排行榜 (Top 10)")
top_df = run_query("""
    SELECT real_name, total_impact_score, developer_archetype, daily_velocity 
    FROM public_marts.fct_developer_activity_profile 
    ORDER BY total_impact_score DESC LIMIT 10
""")

st.dataframe(
    top_df,
    column_config={
        "total_impact_score": st.column_config.ProgressColumn(
            "总影响力", min_value=0, max_value=top_df["total_impact_score"].max() if not top_df.empty else 100
        ),
        "daily_velocity": st.column_config.NumberColumn("速率", format="%.2f"),
    },
    use_container_width=True,
    hide_index=True,
)
