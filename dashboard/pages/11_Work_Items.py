"""统一扁平化工作项仪表盘。"""
import streamlit as st
import plotly.express as px
from utils import run_query, set_page_config
set_page_config()
st.title('统一扁平化工作项 (Unified Work Items)')
st.markdown('---')
work_items_df = run_query("""
    SELECT 
        source_system, 
        work_item_type, 
        current_status, 
        title, 
        author_user_id, 
        created_at 
    FROM public_intermediate.int_unified_work_items
""")
c1, c2, c3 = st.columns(3)
c1.metric('总工作项', len(work_items_df))
c2.metric('待处理 (Opened)', len(work_items_df[work_items_df['current_status'] == 'opened']))
c3.metric('多源融合度', work_items_df['source_system'].nunique())
tab1, tab2 = st.tabs(['统计分布', '工作项列表'])
with tab1:
    fig_source = px.sunburst(work_items_df, path=['source_system', 'work_item_type', 'current_status'], title='工作项层级分布 (来源 > 类型 > 状态)')
    st.plotly_chart(fig_source, use_container_width=True)
    fig_trend = px.histogram(work_items_df, x='created_at', color='work_item_type', nbins=20, title='工作项创建趋势')
    st.plotly_chart(fig_trend, use_container_width=True)
with tab2:
    st.markdown('### 跨源工作项检索')
    st.dataframe(work_items_df.sort_values('created_at', ascending=False), use_container_width=True)