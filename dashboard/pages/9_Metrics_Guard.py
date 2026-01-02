"""TODO: Add module description."""
import streamlit as st
import plotly.express as px
from utils import run_query, set_page_config
set_page_config()
st.title('🛡️ 指标一致性哨兵 (Metrics Audit Guard)')
st.markdown('---')
audit_df = run_query('SELECT * FROM fct_metrics_audit_guard')
anomalies = audit_df[audit_df['is_anomaly'] == True]
if not anomalies.empty:
    st.error(f'🚨 警告：发现 {len(anomalies)} 处指标异常！')
else:
    st.success('✅ 所有核心指标在 ODS 与 Marts 间保持一致。')
c1, c2, c3 = st.columns(3)
c1.metric('已审计指标数', len(audit_df))
c2.metric('异常数', len(anomalies))
c3.metric('指标可信度', f'{(1 - len(anomalies) / max(len(audit_df), 1)) * 100:.1f}%')
st.markdown('### 指标审计报告')
st.dataframe(audit_df, use_container_width=True)
if not audit_df.empty:
    fig = px.bar(audit_df, x='metric_name', y='variance_percentage', color='is_anomaly', title='指标偏差百分比 (Variance %)', labels={'variance_percentage': '偏差 %', 'metric_name': '指标项目'})
    st.plotly_chart(fig, use_container_width=True)