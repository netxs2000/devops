import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils import set_page_config, run_query

set_page_config()

st.title("🏥 项目交付健康度看板")
st.caption("综合 SonarQube 质量视图、GitLab 产出度量与 dbt 智能模型评估。")

# 加载数据
query = """
    select 
        project_name,
        health_score,
        bug_count,
        test_coverage_pct,
        tech_debt_hours,
        quality_gate,
        merged_mr_total,
        mr_backlog,
        prod_deploys
    from fct_project_delivery_health
    order by health_score desc
"""

df = run_query(query)

if df.empty:
    st.warning("暂无健康度数据，请确保已集成 SonarQube 与 GitLab 且运行了 dbt。")
else:
    # 顶部 Top 3 健康项目
    st.subheader("🏆 健康度排名 (Top Projects)")
    cols = st.columns(3)
    for i, row in df.head(3).iterrows():
        with cols[i]:
            st.metric(label=row['project_name'], value=f"{row['health_score']} pts", 
                      delta=f"Gate: {row['quality_gate']}")

    st.divider()

    # 1. 健康分 vs 技术债
    st.subheader("🔍 质量与瓶颈分析")
    fig = px.scatter(df, x="health_score", y="tech_debt_hours", size="bug_count", color="quality_gate",
                     hover_name="project_name", text="project_name",
                     title="健康分 - 技术债 - Bug 数 气泡图", 
                     labels={"health_score": "综合健康分", "tech_debt_hours": "技术债 (小时)"},
                     template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # 2. 交付产出分布
    st.subheader("📈 交付产出清单")
    tab1, tab2 = st.tabs(["合并 MR 分布", "测试覆盖率"])
    
    with tab1:
        fig_mr = px.bar(df, x="project_name", y=["merged_mr_total", "mr_backlog"], 
                        title="已合并 MR vs 待处理积压", template="plotly_dark")
        st.plotly_chart(fig_mr, use_container_width=True)
        
    with tab2:
        fig_cov = px.funnel(df.sort_values('test_coverage_pct', ascending=False), 
                           y="project_name", x="test_coverage_pct",
                           title="单元测试覆盖率 (%)", template="plotly_dark")
        st.plotly_chart(fig_cov, use_container_width=True)

    # 数据表格
    st.subheader("📋 详细指标")
    st.dataframe(
        df,
        column_config={
            "health_score": st.column_config.ProgressColumn("健康指数", min_value=0, max_value=100, format="%d"),
            "test_coverage_pct": st.column_config.NumberColumn("覆盖率", format="%.2f%%"),
            "quality_gate": st.column_config.TextColumn("质量门禁"),
        },
        use_container_width=True,
        hide_index=True
    )
