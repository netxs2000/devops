"""TODO: Add module description."""
import plotly.express as px
import streamlit as st
from utils import run_query, set_page_config


set_page_config()
st.title('💸 交付成本与 FinOps (Delivery Costs)')
st.markdown('---')
costs_df = run_query('SELECT * FROM public_marts.fct_delivery_costs')
if not costs_df.empty:
    st.markdown('### 交付成本概览')
    c1, c2 = st.columns(2)
    c1.metric('总估算成本', f"${costs_df['total_estimated_cost'].sum():,.2f}")
    c2.metric('涵盖项目数', len(costs_df))
    fig_costs = px.pie(costs_df, values='total_estimated_cost', names='project_name', title='各项目估算交付成本分布 (USD)', hole=0.4)
    st.plotly_chart(fig_costs, use_container_width=True)
    st.markdown('### 成本明细表')
    st.dataframe(costs_df, use_container_width=True)
    fig_bar = px.bar(costs_df, x='project_name', y=['labor_estimated_score', 'infra_cost_factor'], title='成本结构分析 (人工分数 vs 基建因子)', barmode='group')
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.warning('暂无交付成本数据，请初始化成本费率。')
