import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.common.db import get_db_engine

# 页面基础配置
st.set_page_config(page_title="Nexus FinOps Dashboard", layout="wide")

st.title("💰 Nexus FinOps & 资产治理大盘")
st.markdown("""
### [小白专区] 您的智能存储管家
这个看板整合了 Nexus 仓库的**财务支出**与**资产健康度**。
1. **财务支出**：帮您算出每个产品线每月在存储上花了多少冤枉钱。
2. **资产治理**：利用“积分制”揪出那些没人要的、“脏乱差”的组件，并提供自动化清理建议。
""")

# 连接数据库
engine = get_db_engine()

# --- 模块 1: 财务概览 ---
st.header("1. 存储成本中心 (FinOps)")

try:
    # 读取成本事实表
    cost_df = pd.read_sql("SELECT * FROM fct_nexus_storage_costs", engine)
    
    if not cost_df.empty:
        # 指标卡片
        total_cost = cost_df["estimated_monthly_cost_cny"].sum()
        total_gb = cost_df["size_gb"].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("预估总月度成本", f"¥ {total_cost:,.2f} CNY")
        m2.metric("总空间占用", f"{total_gb:,.2f} GB")
        m3.metric("受监控产品数量", cost_df["product_id"].nunique())

        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("各产品线成本占比")
            fig_pie = px.pie(cost_df, values='estimated_monthly_cost_cny', names='product_id', hole=.3)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            st.subheader("高成本组件 Top 10")
            top_10 = cost_df.sort_values("estimated_monthly_cost_cny", ascending=False).head(10)
            st.dataframe(top_10[["component_name", "version", "size_gb", "estimated_monthly_cost_cny"]])

    else:
        st.info("💡 尚未发现成本数据。请确保已执行过 `dbt build` 且 Nexus 采集已完成。")
except Exception as e:
    st.error(f"无法加载成本数据: {e}")


# --- 模块 2: 资产治理 (清理评分系统) ---
st.header("2. 资源健康度 & “死亡名单”扫描")

try:
    cleanup_df = pd.read_sql("SELECT * FROM fct_nexus_cleanup_list", engine)
    
    if not cleanup_df.empty:
        # 统计各级别的数量
        level_counts = cleanup_df["cleanup_priority_level"].value_counts().reset_index()
        level_counts.columns = ["危险等级", "数量"]
        
        o1, o2 = st.columns([1, 2])
        
        with o1:
            st.subheader("危险等级分布")
            fig_bar = px.bar(level_counts, x="危险等级", y="数量", color="危险等级",
                             color_discrete_map={
                                 "CRITICAL_DELETE": "#FF4B4B", 
                                 "WARNING_CLEANUP": "#FFA500",
                                 "KEEP_SAFE": "#2EB82E"
                             })
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # 自动清理开关统计
            auto_count = cleanup_df["is_safe_to_auto_cleanup"].sum()
            st.info(f"🤖 自动化清理系统侦测到 **{auto_count}** 个组件符合“安全自动物理删除”规则。")
            
        with o2:
            st.subheader("高风险资产清单 (待清理)")
            # 仅显示高风险和中风险
            danger_list = cleanup_df[cleanup_df["cleanup_priority_level"] != "KEEP_SAFE"].sort_values("total_risk_score", ascending=False)
            st.dataframe(danger_list[[
                "component_name", 
                "component_version", 
                "size_gb", 
                "cleanup_priority_level", 
                "cleanup_reasons_text"
            ]], use_container_width=True)

    else:
        st.success("✅ 扫描完成：未发现待清理资产，仓库非常健康！")
except Exception as e:
    st.error(f"无法加载治理数据: {e}")

st.divider()
st.caption("DevOps Platform - Nexus FinOps Module | 2026-03-14")
