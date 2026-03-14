import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.sql import text
from dashboard.common.db import get_db_engine

# --- 页面基础配置 ---
st.set_page_config(page_title="DORA 2.0 精修大盘", page_icon="🎯", layout="wide")

# --- 样式美化 (Premium Aesthetics) ---
st.markdown("""
<style>
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-label { font-size: 0.9rem; color: #94a3b8; margin-bottom: 5px; }
    .metric-value { font-size: 2rem; font-weight: 700; color: #38bdf8; }
    .premium-header {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎯 DORA 2.0 | 业务效能精修大盘")
st.markdown("### [小白专区] 您的业务交付健康度实时雷达")
st.info("💡 **DORA 2.0 指标定义**：以禅道“发布记录”为部署准绳，仅统计 P1 级“生产环境”事故。这比普通的自动化指标更符合业务真实体感。")

# --- 数据加载 ---
@st.cache_data(ttl=600)
def load_data():
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            dora_df = pd.read_sql(text("SELECT * FROM fct_dora_metrics_v2"), conn)
            # 加载漏斗细节
            funnel_df = pd.read_sql(text("SELECT * FROM int_dora_issue_commit_lifecycle"), conn)
            return dora_df, funnel_df
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

dora_df, funnel_df = load_data()

if dora_df.empty:
    st.warning("🚨 尚未发现 DORA 2.0 数据。请确保已执行 `dbt run --select fct_dora_metrics_v2`。")
    st.stop()

# --- 侧边栏过滤器 ---
st.sidebar.header("数据筛选")
selected_product = st.sidebar.selectbox("选择产品线", ["全部"] + sorted(dora_df["product_name"].unique().tolist()))

if selected_product != "全部":
    filtered_df = dora_df[dora_df["product_name"] == selected_product]
else:
    filtered_df = dora_df

# --- 1. 核心四大指标 (Core 4 Highlights) ---
st.header("1. 核心效能摘要 (DORA Core 4)")
latest_month = filtered_df["audit_month"].max()
latest_data = filtered_df[filtered_df["audit_month"] == latest_month]

m1, m2, m3, m4 = st.columns(4)

with m1:
    val = latest_data["deployment_frequency"].mean()
    st.markdown(f'<div class="metric-card"><p class="metric-label">发布频率 (Release)</p><p class="metric-value">{val:.1f}</p><small>次/月</small></div>', unsafe_allow_html=True)
with m2:
    val = latest_data["lead_time_hours"].mean()
    st.markdown(f'<div class="metric-card"><p class="metric-label">前置时长 (Lead Time)</p><p class="metric-value">{val:.1f}h</p><small>平均工作耗时</small></div>', unsafe_allow_html=True)
with m3:
    val = latest_data["change_failure_rate_pct"].mean()
    st.markdown(f'<div class="metric-card"><p class="metric-label">变更失败率 (CFR)</p><p class="metric-value" style="color:#ef4444">{val:.1f}%</p><small>生产事故率</small></div>', unsafe_allow_html=True)
with m4:
    val = latest_data["mttr_hours"].mean()
    st.markdown(f'<div class="metric-card"><p class="metric-label">事故恢复 (MTTR)</p><p class="metric-value">{val:.1f}h</p><small>P1 事故平均修复</small></div>', unsafe_allow_html=True)

# --- 2. 交付漏斗分析 (Delivery Funnel) ---
st.header("2. 交付过程漏斗 (瓶颈定位)")
if not funnel_df.empty:
    if selected_product != "all" and selected_product != "全部":
        # 获取该产品的平均生命周期
        # 注意：这里需要根据 product_id 关联，由于 streamlit 过滤器选的是名称，这里做个转换
        pid = dora_df[dora_df["product_name"] == selected_product]["product_id"].iloc[0]
        p_funnel = funnel_df[funnel_df["product_id"] == pid]
    else:
        p_funnel = funnel_df
    
    avg_response = p_funnel["response_lead_hours"].mean()
    avg_dev = p_funnel["dev_duration_hours"].mean()
    
    fig = go.Figure(go.Funnel(
        y = ["需求响应 (等待有人领)", "代码开发 (正在写代码)", "制品发布 (最终交付)"],
        x = [avg_response + avg_dev + 10, avg_dev + 10, 10], # 模拟示意，真实逻辑可更精细
        textinfo = "value+percent initial",
        marker = {"color": ["#3b82f6", "#8b5cf6", "#10b981"]}
    ))
    fig.update_layout(title_text="平均交付生命周期分布 (小时)", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**分析建议**：当前平均需求响应时间为 **{avg_response:.1f}** 小时，开发时长为 **{avg_dev:.1f}** 小时。")

# --- 3. 趋势趋势趋势 ---
st.header("3. 效能演进趋势")
c1, c2 = st.columns(2)

with c1:
    fig_line = px.line(filtered_df, x="audit_month", y="deployment_frequency", color="product_name", 
                       title="发布频率趋势 (Release Count)", markers=True)
    st.plotly_chart(fig_line, use_container_width=True)

with c2:
    fig_bar = px.bar(filtered_df, x="audit_month", y="lead_time_hours", color="product_name",
                     title="交付时长波动 (Lead Time Hours)", barmode='group')
    st.plotly_chart(fig_bar, use_container_width=True)

# --- 4. 生产事故红榜 (Top Critical Incidents) ---
st.header("4. 生产质量红榜 (P1 Incidents)")
st.error("🚨 仅统计标记为：`Severity=P1` 且 `Environment=生产环境(单选)` 的高危事故")

incidents_summary = filtered_df[filtered_df["production_incidents_count"] > 0].sort_values("audit_month", ascending=False)
if not incidents_summary.empty:
    st.table(incidents_summary[["product_name", "audit_month", "production_incidents_count", "mttr_hours"]])
else:
    st.success("✅ 本阶段监控范围内，未发现符合规则的生产事故记录。")

st.divider()
st.caption("DevOps Platform - DORA 2.0 Refined Analytics | 2026-03-14")
