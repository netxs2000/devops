"""Project Health & Security Cockpit."""

import plotly.express as px
import streamlit as st
from utils import run_query, set_page_config


# --- Configuration & Styling ---
set_page_config()
st.title("🏥 项目交付健康度看板")
st.caption("综合 SonarQube 质量视图、GitLab 产出度量与 dbt 智能模型评估。")

st.markdown(
    """
<style>
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 10px;
    }
    .health-val {
        font-size: 2rem;
        font-weight: bold;
        color: #00ff7f;
    }
    .gate-passed { color: #00ff7f; font-weight: bold; }
    .gate-failed { color: #ff3333; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)

# --- Data Loading ---
query = """
    SELECT 
        project_name,
        health_score,
        bug_count,
        test_coverage_pct,
        tech_debt_hours,
        quality_gate,
        merged_mr_total,
        mr_backlog,
        prod_deploys
    FROM public_marts.fct_project_delivery_health
    ORDER BY health_score DESC
"""
df = run_query(query)

if df.empty:
    st.warning("暂无健康度数据，请确保已集成 SonarQube 与 GitLab 且运行了 dbt。")
    st.stop()

# --- Top Performers Row ---
st.subheader("🏆 交付标杆 (Top Health Ranking)")
top_cols = st.columns(3)
for i, row in df.head(3).iterrows():
    gate_style = "gate-passed" if row["quality_gate"] == "PASSED" else "gate-failed"
    with top_cols[i]:
        st.markdown(
            f"""
        <div class="glass-card">
            <div style="font-size:0.85rem; color:#aaa;">{row["project_name"]}</div>
            <div class="health-val">{row["health_score"]} <span style="font-size:0.8rem; font-weight:300;">pts</span></div>
            <div class="{gate_style}" style="font-size:0.75rem;">Quality Gate: {row["quality_gate"]}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.divider()

# --- Quality vs Debt Scatter ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("🔍 质量-负荷平衡气泡图")
    fig = px.scatter(
        df,
        x="health_score",
        y="tech_debt_hours",
        size="bug_count",
        color="quality_gate",
        hover_name="project_name",
        text="project_name",
        labels={"health_score": "综合健康分", "tech_debt_hours": "技术债 (小时)"},
        color_discrete_map={"PASSED": "#00ff7f", "FAILED": "#ff3333", "WARN": "#ffab00"},
        template="plotly_dark",
    )
    fig.update_layout(height=450, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("📋 待修复风险项")
    # Show projects with high debt or failed gates
    risky_projects = df[(df["quality_gate"] == "FAILED") | (df["tech_debt_hours"] > 40)]
    if not risky_projects.empty:
        for _, r in risky_projects.iterrows():
            st.error(f"**{r['project_name']}**")
            st.caption(f"Bugs: {r['bug_count']} | Debt: {r['tech_debt_hours']}h")
    else:
        st.success("目前全站无关键质量风险。")

# --- Output Distribution ---
st.subheader("📈 交付产出清单")
tab1, tab2 = st.tabs(["MR 合并分布", "测试覆盖率概况"])

with tab1:
    fig_mr = px.bar(
        df,
        x="project_name",
        y=["merged_mr_total", "mr_backlog"],
        title="已合并 vs 积压待处理",
        barmode="group",
        color_discrete_sequence=["#3366ff", "#8F00FF"],
        template="plotly_dark",
    )
    st.plotly_chart(fig_mr, use_container_width=True)

with tab2:
    fig_cov = px.funnel(
        df.sort_values("test_coverage_pct", ascending=False),
        y="project_name",
        x="test_coverage_pct",
        title="单元测试覆盖率排位",
        template="plotly_dark",
    )
    st.plotly_chart(fig_cov, use_container_width=True)

# --- Raw Data Table ---
with st.expander("📊 查看全量监控明细"):
    st.dataframe(
        df,
        column_config={
            "health_score": st.column_config.ProgressColumn("健康指数", min_value=0, max_value=100, format="%d"),
            "test_coverage_pct": st.column_config.NumberColumn("覆盖率", format="%.2f%%"),
            "quality_gate": st.column_config.TextColumn("质量门禁"),
        },
        use_container_width=True,
        hide_index=True,
    )
