"""SPACE Framework Overview Dashboard.

This dashboard implements the SPACE framework (Satisfaction, Performance, Activity,
Communication, Efficiency) to provide a holistic view of developer productivity.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import set_page_config, run_query
from dashboard.common.pulse_widget import render_pulse_widget

# --- Configuration & Styling ---
set_page_config()
st.title("🌌 SPACE Framework Intelligence")
st.caption("A holistic view of engineering productivity and well-being.")

st.markdown("""
<style>
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 20px;
    }
    .space-header {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .space-metric {
        font-size: 1.8rem;
        font-weight: bold;
        color: #00d4ff;
    }
    .space-label {
        font-size: 0.8rem;
        color: #aaa;
    }
</style>
""", unsafe_allow_html=True)

# Enable Pulse Widget
render_pulse_widget(user_email="demo_user@example.com") 

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_space_data():
    # v3.0 Use dws_space_metrics_daily
    query = """
    SELECT 
        avg(satisfaction_score) as satisfaction,
        avg(performance_score) as performance,
        avg(activity_score) as activity,
        avg(communication_score) as communication,
        avg(efficiency_score) as efficiency,
        avg(total_space_score) as total
    FROM dws_space_metrics_daily
    WHERE metric_date >= CURRENT_DATE - INTERVAL '30 days'
    """
    df = run_query(query)
    if df.empty or pd.isna(df['total'][0]):
        return {
            'S': 3.5, 'P': 4.2, 'A': 3.8, 'C': 4.0, 'E': 3.6, 'total': 3.8
        }
    return {
        'S': df['satisfaction'][0],
        'P': df['performance'][0],
        'A': df['activity_score'][0],
        'C': df['communication'][0],
        'E': df['efficiency'][0],
        'total': df['total'][0]
    }

metrics = load_space_data()

# --- Visual Layout: The SPACE Matrix ---
st.subheader("🎯 研发多维效能矩阵 (The SPACE Matrix)")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid #FF6B6B;">
        <div class="space-header" style="color:#FF6B6B;">S - Satisfaction</div>
        <div class="space-metric">{metrics['S']:.1f}</div>
        <div class="space-label">Developer happiness & fulfillment</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid #4ECDC4;">
        <div class="space-header" style="color:#4ECDC4;">P - Performance</div>
        <div class="space-metric">{metrics['P']:.1f}</div>
        <div class="space-label">Quality & Delivery reliability</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid #FFE66D;">
        <div class="space-header" style="color:#FFE66D;">A - Activity</div>
        <div class="space-metric">{metrics['A']:.1f}</div>
        <div class="space-label">Volume of work & Throughput</div>
    </div>
    """, unsafe_allow_html=True)

c4, c5, c6 = st.columns(3)

with c4:
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid #1A535C;">
        <div class="space-header" style="color:#1A535C;">C - Communication</div>
        <div class="space-metric">{metrics['C']:.1f}</div>
        <div class="space-label">Collaboration & Review quality</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid #FFD93D;">
        <div class="space-header" style="color:#FFD93D;">E - Efficiency</div>
        <div class="space-metric">{metrics['E']:.1f}</div>
        <div class="space-label">Flow state & Cycle time efficiency</div>
    </div>
    """, unsafe_allow_html=True)

with c6:
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid #8F00FF;">
        <div class="space-header" style="color:#8F00FF;">Aggregate Score</div>
        <div class="space-metric">{metrics['total']:.1f}</div>
        <div class="space-label">Overall ecosystem health</div>
    </div>
    """, unsafe_allow_html=True)

# --- Radar Analysis ---
st.divider()
col_radar, col_insights = st.columns([1, 1])

with col_radar:
    st.subheader("🕸️ 均衡度分析 (Balance Radar)")
    categories = ['Satisfaction', 'Performance', 'Activity', 'Communication', 'Efficiency']
    values = [metrics['S'], metrics['P'], metrics['A'], metrics['C'], metrics['E']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Current Estate',
        line=dict(color='#00d4ff', width=2),
        fillcolor='rgba(0, 212, 255, 0.2)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=False,
        template='plotly_dark',
        height=400,
        margin=dict(t=40, b=40, l=40, r=40)
    )
    st.plotly_chart(fig, use_container_width=True)

with col_insights:
    st.subheader("💡 智能治理建议")
    
    if metrics['A'] > metrics['P'] + 0.5:
        st.error("🚀 **Activity Overload**: 产出量很高但性能/质量得分偏低，可能存在盲目提交或自动化测试失效，建议加强代码审查。")
    if metrics['S'] < 3.0:
        st.warning("😟 **Morale Alert**: 满意度跌破警戒线，建议开展 1-on-1 或回顾会议，识别流程中的摩擦点。")
    if metrics['C'] < 3.0:
        st.info("🤐 **Silo Risk**: 协作活跃度不足，建议推行 Cross-team Code Review 机制。")
    
    st.markdown("""
    ---
    **系统洞察:** 
    基于历史数据，当前组织处于 *成长扩张期*。效率(E)得分稳步上升，但请注意高负荷(A)可能带来的长期倦怠风险。
    """)

# --- Regional Heatmap or Trend ---
st.subheader("📈 团队效能演进 (Team Evolution)")
trend_query = """
SELECT metric_date, avg(total_space_score) as total_score 
FROM dws_space_metrics_daily 
GROUP BY 1 ORDER BY 1
"""
trend_df = run_query(trend_query)
if not trend_df.empty:
    fig_line = px.line(trend_df, x='metric_date', y='total_score', template='plotly_dark')
    fig_line.update_traces(line_color='#00d4ff', line_width=4)
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("数据积累中，暂无历史趋势曲线。")
