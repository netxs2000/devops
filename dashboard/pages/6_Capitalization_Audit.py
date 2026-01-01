import streamlit as st
import plotly.express as px
from utils import run_query, set_page_config

set_page_config()

st.title("💰 研发投入资本化核算 (Capitalization Audit)")
st.markdown("---")

cap_df = run_query("SELECT * FROM fct_capitalization_audit")

# Summary Metrics
c1, c2, c3 = st.columns(3)
c1.metric("可资本化 Epic 数量", len(cap_df))
c2.metric("高置信度项目", len(cap_df[cap_df['audit_status'] == 'High Confidence']))
c3.metric("总审计提交数", cap_df['audit_effort_unit'].sum())

st.markdown("""
本模型通过“需求-代码-审计”穿透链路，自动核算符合研发费用资本化条件的投入。
""")

st.markdown("### 审计明细")
st.dataframe(cap_df, use_container_width=True)

fig_audit = px.bar(
    cap_df, 
    x="epic_title", 
    y="audit_effort_unit", 
    color="audit_status",
    title="Epic 审计投入分布",
    labels={"audit_effort_unit": "提交数", "epic_title": "Epic 名称"}
)
st.plotly_chart(fig_audit, use_container_width=True)
