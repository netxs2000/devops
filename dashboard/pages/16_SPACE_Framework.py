
"""SPACE Framework Overview Dashboard.

This dashboard implements the SPACE framework (Satisfaction, Performance, Activity,
Communication, Efficiency) to provide a holistic view of developer productivity.

Reference:
    "The SPACE of Developer Productivity" - Nicole Forsgren et al. (Microsoft/GitHub)
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy import create_engine, text
from dashboard.common.db import get_db_engine

from dashboard.common.pulse_widget import render_pulse_widget

# ... Configuration ...
st.set_page_config(page_title="SPACE Framework Overview", page_icon="🌌", layout="wide")

# Enable Pulse Widget
render_pulse_widget(user_email="demo_user@example.com") # Mock user for demo

# ...

# --- Data Loading ---
@st.cache_data(ttl=600)
def load_space_metrics():
    engine = get_db_engine()
    metrics = {}
    
    with engine.connect() as conn:
        # 0. Satisfaction (S) -> From Pulse
        try:
            query_sat = """
            SELECT AVG(score) as avg_score, COUNT(*) as responses
            FROM satisfaction_records
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            """
            res_sat = conn.execute(text(query_sat)).fetchone()
            metrics['sat_score'] = res_sat[0] if res_sat and res_sat[0] else 0.0
            metrics['sat_responses'] = res_sat[1] if res_sat and res_sat[1] else 0
        except Exception:
            metrics['sat_score'] = 0.0
            metrics['sat_responses'] = 0

        # 1. Activity (A) -> From ELOC / Commits
        try:
            query_activity = """
            SELECT COUNT(distinct commit_id) as total_commits, SUM(impact_score) as total_impact 
            FROM commit_metrics 
            WHERE committed_at >= NOW() - INTERVAL '30 days'
            """
            res_activity = conn.execute(text(query_activity)).fetchone()
            metrics['activity_commits'] = res_activity[0] if res_activity and res_activity[0] else 0
            metrics['activity_impact'] = res_activity[1] if res_activity and res_activity[1] else 0
        except Exception:
            metrics['activity_commits'] = 0
            
        # 2. Performance (P) -> From DORA
        try:
            query_perf = """
            SELECT AVG(change_failure_rate_pct) as cfr, AVG(deployment_frequency) as freq
            FROM fct_dora_metrics
            WHERE month >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
            """
            res_perf = conn.execute(text(query_perf)).fetchone()
            metrics['perf_cfr'] = res_perf[0] if res_perf and res_perf[0] is not None else 0.0
            metrics['perf_freq'] = res_perf[1] if res_perf and res_perf[1] is not None else 0.0
        except Exception:
            metrics['perf_cfr'] = 0.0
            
        # 3. Collaboration (C) -> From Reviews (Sherpa)
        try:
            # Fallback table check
            query_collab = """
            SELECT SUM(review_count) 
            FROM daily_dev_stats 
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            """
            # Note: If table doesn't exist, this will fail gracefully
            res_collab = conn.execute(text(query_collab)).fetchone()
            metrics['collab_reviews'] = res_collab[0] if res_collab and res_collab[0] else 0
        except Exception:
            metrics['collab_reviews'] = 0

    return metrics

metrics = load_space_metrics()

# --- Visual Layout ---

# Top Row: S, P, A
c1, c2, c3 = st.columns(3)

with c1:
    sat_score = metrics.get('sat_score', 0)
    emoji = "😐"
    if sat_score >= 4: emoji = "🤩"
    elif sat_score >= 3: emoji = "🙂"
    elif sat_score > 0: emoji = "😟"
    else: emoji = "🤷‍♂️"

    st.markdown(f"""
    <div class="space-card" style="border-top-color: #FF6B6B;">
        <div class="space-header">S - Satisfaction</div>
        <div class="space-desc">Developer happiness (Mood Score).</div>
        <br>
        <div>Mood Score: <span class="space-metric">{sat_score:.1f} / 5</span> {emoji}</div>
        <div>Responses: <span class="space-metric">{metrics.get('sat_responses', 0)}</span></div>
        <div style="font-size:12px; color:#aaa; margin-top:5px;">Based on sidebar Pulse check</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="space-card" style="border-top-color: #4ECDC4;">
        <div class="space-header">P - Performance</div>
        <div class="space-desc">Quality and reliability of software delivery (DORA).</div>
        <br>
        <div>Fail Rate (CFR): <span class="space-metric">{metrics.get('perf_cfr', 0):.1f}%</span></div>
        <div>Deploy Freq: <span class="space-metric">{metrics.get('perf_freq', 0):.1f}</span> /mo</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="space-card" style="border-top-color: #FFE66D;">
        <div class="space-header">A - Activity</div>
        <div class="space-desc">Volume of work performed (Commits, ELOC).</div>
        <br>
        <div>Commits (30d): <span class="space-metric">{metrics.get('activity_commits', 0)}</span></div>
        <div>Impact Score: <span class="space-metric">{int(metrics.get('activity_impact', 0))}</span></div>
    </div>
    """, unsafe_allow_html=True)

st.write("") # Spacer

# Bottom Row: C, E
c4, c5 = st.columns(2)

with c4:
    st.markdown(f"""
    <div class="space-card" style="border-top-color: #1A535C;">
        <div class="space-header">C - Communication</div>
        <div class="space-desc">Review velocity, documentation, and knowledge sharing.</div>
        <br>
        <div>Code Reviews (30d): <span class="space-metric">{metrics.get('collab_reviews', 0)}</span></div>
        <div style="color:#aaa; font-size:12px; margin-top:5px;">Target: Ensure > 1 review per PR</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="space-card" style="border-top-color: #FFD93D;">
        <div class="space-header">E - Efficiency</div>
        <div class="space-desc">Flow state, interruptions, and handoffs.</div>
        <br>
        <!-- Placeholder for Flow Time / Lead Time -->
        <div>Lead Time: <span class="space-metric">See DORA</span></div>
        <div style="color:#aaa; font-size:12px; margin-top:5px;">
            <i>Tip: High Activity + Low Performance = Low Efficiency.</i>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- Detailed Analysis & Recommendations ---
st.subheader("💡 Insights & Recommendations")

insights = []

# Logic for simple insights
if metrics.get('activity_commits', 0) > 100 and metrics.get('perf_cfr', 0) > 15:
    insights.append("🚨 **High Churn Risk**: Activity is high (A) but Failure Rate is also high (P). Slow down and focus on testing.")

if metrics.get('collab_reviews', 0) == 0:
    insights.append("⚠️ **Silo Risk**: No Code Review activity detected (C). This impacts quality sharing. Enable peer reviews.")

if not insights:
    insights.append("✅ System balance looks okay based on available metrics. Monitor Satisfaction (S) manually.")

for i in insights:
    st.markdown(i)

# Radar Chart Conceptual
st.subheader("SPACE Balance Radar (Conceptual)")
categories = ['Satisfaction', 'Performance', 'Activity', 'Communication', 'Efficiency']
# Normalize values to 0-100 for radar (Mock logic for demo)
start_vals = [
    0, 
    min(100, (100 - metrics.get('perf_cfr', 0))), # Lower CFR is better
    min(100, metrics.get('activity_commits', 0) / 10), # Pseudo normalization
    min(100, metrics.get('collab_reviews', 0) * 5),
    60 # Efficiency placeholder
]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=start_vals,
    theta=categories,
    fill='toself',
    name='Current State'
))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    showlegend=False,
    height=400
)
st.plotly_chart(fig, use_container_width=True)
