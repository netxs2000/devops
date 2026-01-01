import streamlit as st
import plotly.express as px
from utils import set_page_config, run_query

set_page_config()

st.title("🏗️ 架构脆性指数 (ABI) 分析")
st.caption("基于组件入度 (In-degree)、认知复杂度与测试覆盖率，识别组织内的“单点崩溃”风险模块。")

# 加载数据
query = """
    select 
        project_name,
        total_in_degree,
        complexity,
        cognitive_complexity,
        coverage_pct,
        brittleness_index,
        risk_level
    from fct_architectural_brittleness
    order by brittleness_index desc
"""

df = run_query(query)

if df.empty:
    st.warning("暂无架构脆性数据。请确保 dbt 模型 `fct_architectural_brittleness` 已生成。")
else:
    # 顶部风险统计
    high_risk_count = len(df[df['risk_level'] == 'CRITICAL'])
    st.warning(f"☢️ 检测到 {high_risk_count} 个关键模块处于高危 (CRITICAL) 状态，极易引发多米诺骨牌效应。")
    
    # 1. 脆性气泡图
    st.subheader("🌋 架构风险分布")
    fig = px.scatter(df, x="total_in_degree", y="brittleness_index", size="cognitive_complexity", 
                     color="risk_level", hover_name="project_name", text="project_name",
                     color_discrete_map={"CRITICAL": "#ff4b4b", "STABLE": "#00cc96", "MEDIUM": "#ffa500"},
                     title="组件入度 (影响力) vs 脆性指数 (风险)", 
                     labels={"total_in_degree": "组件入度 (被下游引用的总数)", "brittleness_index": "脆性指数 (ABI)"},
                     template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # 2. 详细数据
    st.subheader("📋 组件风险清单")
    st.dataframe(
        df,
        column_config={
            "brittleness_index": st.column_config.NumberColumn("脆性指数", format="%.2f"),
            "coverage_pct": st.column_config.NumberColumn("覆盖率", format="%.1f%%"),
            "total_in_degree": st.column_config.NumberColumn("下游引用数"),
        },
        use_container_width=True,
        hide_index=True
    )

    st.info("""
    **为什么关注 ABI？**
    如果一个组件被大量下游服务引用（入度高），但其内部代码极其复杂（认知复杂度高）且缺乏测试守护（覆盖率低），那么该组件的任何微小变更或隐藏 Bug 都可能导致整个系统的大规模瘫痪。
    """)
