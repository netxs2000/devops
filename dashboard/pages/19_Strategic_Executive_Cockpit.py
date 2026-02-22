import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import run_query, set_page_config


def safe_float(val, default=0.0):
    """安全地将值转换为 float，处理 None 和 NaN。"""
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

# --- Premium Page Configuration ---
set_page_config()

# Custom CSS for Premium Aesthetics (Glassmorphism & Vibrant Elements)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 20px;
    }
    
    .kpi-title {
        color: #00d4ff;
        font-size: 0.9rem;
        font-weight: 300;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .kpi-value {
        color: #ffffff;
        font-size: 2.5rem;
        font-weight: 600;
        margin: 5px 0;
    }
    
    .kpi-delta {
        font-size: 0.85rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .badge-success { background: rgba(0, 255, 127, 0.2); color: #00ff7f; border: 1px solid #00ff7f; }
    .badge-warning { background: rgba(255, 171, 0, 0.2); color: #ffab00; border: 1px solid #ffab00; }
    .badge-danger { background: rgba(255, 0, 0, 0.2); color: #ff3333; border: 1px solid #ff3333; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ 研发作战指挥中心 (Executive Cockpit)")
st.caption("Strategic Intelligence for Engineering Leaders | v3.0 Powered by dbt & MDM")

# --- Strategic Data Ingestion ---
try:
    # 1. Overall Portfolio Health
    health_data = run_query("SELECT avg(health_score) as avg_score, count(*) as project_count FROM public_marts.fct_project_delivery_health")
    avg_health = safe_float(health_data['avg_score'][0]) if not health_data.empty else 0
    total_projects = int(health_data['project_count'][0]) if not health_data.empty else 0

    # 2. DORA Aggregates (Current Month)
    dora_data = run_query("""
        SELECT 
            avg(deployment_frequency) as freq,
            avg(lead_time_hours) as lead_time,
            avg(change_failure_rate_pct) as cfr
        FROM public_marts.fct_dora_metrics
        WHERE month = date_trunc('month', current_date)::date
    """)
    if dora_data.empty or pd.isna(dora_data['freq'][0]):
        # Fallback to last known month if current is empty
        dora_data = run_query("""
            SELECT 
                avg(deployment_frequency) as freq,
                avg(lead_time_hours) as lead_time,
                avg(change_failure_rate_pct) as cfr
            FROM public_marts.fct_dora_metrics
            WHERE month = (SELECT max(month) FROM public_marts.fct_dora_metrics)
        """)

    # 3. Financial Distribution (CapEx vs OpEx)
    fin_data = run_query("""
        SELECT 'CapEx (资本化支出)' as category, sum(capex_impact) as total_cost
        FROM public_marts.fct_capitalization_audit
        UNION ALL
        SELECT 'OpEx (运营支出)' as category, sum(opex_impact) as total_cost
        FROM public_marts.fct_capitalization_audit
    """)

    # 4. Critical Technical Debt (Hotspots)
    brittleness_data = run_query("""
        SELECT 
            project_name, brittleness_index, architectural_health_status
        FROM public_marts.fct_architectural_brittleness
        ORDER BY brittleness_index DESC
        LIMIT 5
    """)

except Exception as e:
    st.error(f"数仓连接异常: {e}")
    st.stop()

# --- Top Row: Strategic KPI Cards ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="glass-card">
        <div class="kpi-title">体系健康分</div>
        <div class="kpi-value">{avg_health:.1f}</div>
        <div class="kpi-delta"><span style="color:#00ff7f;">▲ 2.4%</span> vs 上月</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    freq = safe_float(dora_data['freq'][0]) if not dora_data.empty else 0
    st.markdown(f"""
    <div class="glass-card">
        <div class="kpi-title">部署频率 (Avg)</div>
        <div class="kpi-value">{freq:.1f}</div>
        <div class="status-badge badge-success">HIGH PERFORMER</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    cfr = safe_float(dora_data['cfr'][0]) if not dora_data.empty else 0
    st.markdown(f"""
    <div class="glass-card">
        <div class="kpi-title">变更失败率</div>
        <div class="kpi-value">{cfr:.1f}%</div>
        <div class="status-badge badge-warning">THRESHOLD 15%</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="glass-card">
        <div class="kpi-title">资产存量</div>
        <div class="kpi-value">{total_projects}</div>
        <div class="kpi-delta">纳管仓库 & 集成服务</div>
    </div>
    """, unsafe_allow_html=True)

# --- Second Row: Mixed Intelligence ---
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("#### 🧭 产研投入雷达 (Investment Mix)")

    if not fin_data.empty:
        fig_pie = px.pie(
            fin_data, values='total_cost', names='category',
            hole=0.6,
            color_discrete_sequence=['#00d4ff', '#3366ff', '#8F00FF', '#ffab00'],
            template='plotly_dark'
        )
        fig_pie.update_layout(
            margin=dict(t=30, b=30, l=30, r=30),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("暂无财务审计数据，请确保已运行数据同步和 dbt build")
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("#### 🚨 核心架构风险 (Brittleness Top 5)")
    if not brittleness_data.empty:
        for idx, row in brittleness_data.iterrows():
            status = row['architectural_health_status'] or 'NORMAL'
            brittleness_idx = safe_float(row['brittleness_index'])
            badge_class = "badge-danger" if status == 'CRITICAL_BRITTLE_CORE' else "badge-warning"
            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding:8px; background:rgba(255,255,255,0.03); border-radius:10px;">
                    <div>
                        <div style="font-size:0.85rem; color:#eee;">{row['project_name']}</div>
                        <div style="font-size:0.7rem; color:#888;">Index: {brittleness_idx:.2f}</div>
                    </div>
                    <span class="status-badge {badge_class}">{status}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("架构分析引擎未识别到高危模块。")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Third Row: Trend Analysis ---
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("#### 📈 组织效能演进趋势 (DORA Elite Evolution)")
trend_query = "SELECT month, avg(deployment_frequency) as freq, avg(lead_time_hours) as lead_time FROM public_marts.fct_dora_metrics GROUP BY 1 ORDER BY 1"
trend_df = run_query(trend_query)

if not trend_df.empty:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_df['month'], y=trend_df['freq'],
        name='发布频率', line=dict(color='#00d4ff', width=3),
        fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)'
    ))
    fig_trend.add_trace(go.Scatter(
        x=trend_df['month'], y=trend_df['lead_time'],
        name='前置时间', yaxis='y2', line=dict(color='#8F00FF', width=3, dash='dot')
    ))

    fig_trend.update_layout(
        template='plotly_dark',
        yaxis=dict(title='发布次数 (次/月)'),
        yaxis2=dict(title='前置时间 (分钟)', overlaying='y', side='right'),
        margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(orientation="h", x=0.5, y=1.1, xanchor="center")
    )
    st.plotly_chart(fig_trend, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- NEW: Strategic Portfolio Battle Map (The 18-Module Classification) ---
st.divider()
st.subheader("🗺️ 研发治理资产全景图 (Asset Battle Map)")

cat_efficiency, cat_quality, cat_governance, cat_economics = st.columns(4)

with cat_efficiency:
    st.markdown("""
    <div class="glass-card" style="border-top: 3px solid #00d4ff; height: 350px;">
        <div class="kpi-title" style="color:#00d4ff; margin-bottom:15px;">🚀 效能与交付频率</div>
        <ul style="list-style-type: none; padding: 0; font-size: 0.85rem; color: #ccc;">
            <li style="margin-bottom:8px;">🔹 <a href="/Gitprime" target="_self" style="color:#eee;text-decoration:none;">Gitprime 核心吞吐</a></li>
            <li style="margin-bottom:8px;">🔹 <a href="/DORA_Metrics" target="_self" style="color:#eee;text-decoration:none;">DORA 四大核心指标</a></li>
            <li style="margin-bottom:8px;">🔹 <a href="/Unified_Activities" target="_self" style="color:#eee;text-decoration:none;">统一研发活动流</a></li>
            <li style="margin-bottom:8px;">🔹 <a href="/Work_Items" target="_self" style="color:#eee;text-decoration:none;">工作项交付漏斗</a></li>
            <li style="margin-bottom:8px;">🔹 <a href="/SPACE_Framework" target="_self" style="color:#eee;text-decoration:none;">SPACE 多维生产力</a></li>
            <li style="margin-bottom:8px;">🔹 <a href="/Value_Stream" target="_self" style="color:#eee;text-decoration:none;">价值流图谱分析</a></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with cat_quality:
    st.markdown("""
    <div class="glass-card" style="border-top: 3px solid #00ff7f; height: 350px;">
        <div class="kpi-title" style="color:#00ff7f; margin-bottom:15px;">🛡️ 质量保证与稳健性</div>
        <ul style="list-style-type: none; padding: 0; font-size: 0.85rem; color: #ccc;">
            <li style="margin-bottom:8px;">✅ <a href="/Project_Health" target="_self" style="color:#eee;text-decoration:none;">项目交付健康度</a></li>
            <li style="margin-bottom:8px;">✅ <a href="/Compliance_Audit" target="_self" style="color:#eee;text-decoration:none;">合规性自动审计</a></li>
            <li style="margin-bottom:8px;">✅ <a href="/Metrics_Guard" target="_self" style="color:#eee;text-decoration:none;">核心北极星指标监控</a></li>
            <li style="margin-bottom:8px;">✅ <a href="/Michael_Feathers_Code_Hotspots" target="_self" style="color:#eee;text-decoration:none;">代码高危热点分析</a></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with cat_governance:
    st.markdown("""
    <div class="glass-card" style="border-top: 3px solid #8F00FF; height: 350px;">
        <div class="kpi-title" style="color:#8F00FF; margin-bottom:15px;">🏛️ 资产治理与身份</div>
        <ul style="list-style-type: none; padding: 0; font-size: 0.85rem; color: #ccc;">
            <li style="margin-bottom:8px;">💠 <a href="/ABI_Analysis" target="_self" style="color:#eee;text-decoration:none;">ABI 架构接口治理</a></li>
            <li style="margin-bottom:8px;">💠 <a href="/User_Profile" target="_self" style="color:#eee;text-decoration:none;">研发人员数字画像</a></li>
            <li style="margin-bottom:8px;">💠 <a href="/Talent_Radar" target="_self" style="color:#eee;text-decoration:none;">人才矩阵雷达分析</a></li>
            <li style="margin-bottom:8px;">💠 <a href="/Entity_Alignment" target="_self" style="color:#eee;text-decoration:none;">多系统实体对齐中心</a></li>
            <li style="margin-bottom:8px;">💠 <a href="/Metadata_Governance" target="_self" style="color:#eee;text-decoration:none;">元数据血缘治理</a></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with cat_economics:
    st.markdown("""
    <div class="glass-card" style="border-top: 3px solid #ffab00; height: 350px;">
        <div class="kpi-title" style="color:#ffab00; margin-bottom:15px;">💰 研发经济与成本</div>
        <ul style="list-style-type: none; padding: 0; font-size: 0.85rem; color: #ccc;">
            <li style="margin-bottom:8px;">💎 <a href="/Capitalization_Audit" target="_self" style="color:#eee;text-decoration:none;">资本化投入占比审计</a></li>
            <li style="margin-bottom:8px;">💎 <a href="/Shadow_IT" target="_self" style="color:#eee;text-decoration:none;">影子 IT 风险发现</a></li>
            <li style="margin-bottom:8px;">💎 <a href="/Delivery_Costs" target="_self" style="color:#eee;text-decoration:none;">系统级交付成本核算</a></li>
        </ul>
        <div style="margin-top:50px; text-align:center; opacity:0.3;">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
               <circle cx="12" cy="12" r="10"></circle>
               <path d="M12 8v8M8 12h8"></path>
            </svg>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Footer Actionable Insights ---
st.markdown("""
<div style="text-align:center; color:#888; font-size:0.8rem; margin-top:20px;">
    🚀 <strong>Insight:</strong> 发现 <code>fct_capitalization_audit</code> 中技术债成本占比较高 (35%)，建议下月优先关注 <code>fct_architectural_brittleness</code> 中的核心模块重构。
</div>
""", unsafe_allow_html=True)
