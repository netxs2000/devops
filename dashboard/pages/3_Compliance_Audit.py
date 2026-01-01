import streamlit as st
import plotly.express as px
from utils import set_page_config, run_query

set_page_config()

st.title("⚠️ 合规审计与过程风控")
st.caption("基于“四眼原则”与分支保护规范，识别研发流程中的违规隐患。")

# 加载数据
query = """
    select 
        project_name,
        path_with_namespace,
        total_merged_mrs,
        suspicious_bypass_mrs,
        bypass_rate_pct,
        direct_push_incidents,
        compliance_status
    from fct_compliance_audit
    order by bypass_rate_pct desc
"""

df = run_query(query)

if df.empty:
    st.warning("暂无合规数据。请确保 dbt 模型 `fct_compliance_audit` 已生成。")
else:
    # 顶部风险统计
    risk_df = df[df['compliance_status'] != 'COMPLIANT']
    
    st.error(f"🚨 检测到 {len(risk_df)} 个项目存在流程合规风险")
    
    # 1. 违规分布情况
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🛠️ 绕过评审率 (Bypass Rate)")
        fig_bypass = px.bar(df, x="project_name", y="bypass_rate_pct", color="compliance_status",
                           color_discrete_map={"NON_COMPLIANT": "#ff4b4b", "PROCESS_RISK": "#ffa500", "COMPLIANT": "#00cc96"},
                           title="Merge Request 未经独立评审占比", template="plotly_dark")
        st.plotly_chart(fig_bypass, use_container_width=True)
        
    with col2:
        st.subheader("🚫 直连推送次数 (Direct Pushes)")
        fig_push = px.scatter(df, x="total_merged_mrs", y="direct_push_incidents", size="direct_push_incidents",
                             color="compliance_status", hover_name="project_name",
                             title="直连推送 vs 总合并量 (识别手工绕过流水线行为)", template="plotly_dark")
        st.plotly_chart(fig_push, use_container_width=True)

    # 2. 详细审计清单
    st.subheader("📋 详细审计清单")
    
    def color_status(val):
        color = '#00cc96' # Green
        if val == 'NON_COMPLIANT':
            color = '#ff4b4b' # Red
        elif val == 'PROCESS_RISK':
            color = '#ffa500' # Orange
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        df.style.applymap(color_status, subset=['compliance_status']),
        column_config={
            "bypass_rate_pct": st.column_config.NumberColumn("绕过率", format="%.2f%%"),
            "direct_push_incidents": st.column_config.NumberColumn("直连推送次数"),
            "compliance_status": st.column_config.TextColumn("合规评级状态"),
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("""
    ---
    **审计规则定义：**
    1. **NON_COMPLIANT (不合规)**: 绕过评审率 > 30%。
    2. **PROCESS_RISK (流程风险)**: 存在超过 10 次直连推送（绕过 MR 流程）。
    3. **COMPLIANT (合规)**: 流程严谨，建议保持。
    """)
