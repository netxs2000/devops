"""模糊实体对齐与链接仪表盘。"""
import streamlit as st
import plotly.express as px
from utils import run_query, set_page_config
set_page_config()
st.title('模糊实体对齐与链接 (Entity Alignment)')
st.markdown('---')

st.markdown('''
平台通过语义识别与启发式算法，自动发现 GitLab 仓库与 MDM 主数据实体之间的关联。
支持三种对齐策略：精确ID匹配、名称精确匹配、路径模糊匹配。
''')

alignment_df = run_query("""
    SELECT 
        gitlab_project_id,
        project_name,
        master_entity_id,
        master_entity_name,
        alignment_strategy,
        master_entity_importance
    FROM public_intermediate.int_entity_alignment
""")

if alignment_df.empty:
    st.warning("暂无实体对齐数据。请确保已运行 dbt build 并存在 MDM 实体拓扑数据。")
else:
    # 统计指标
    c1, c2, c3 = st.columns(3)
    total_repos = len(alignment_df)
    aligned_repos = len(alignment_df[alignment_df['master_entity_id'].notna()])
    alignment_rate = aligned_repos / total_repos * 100 if total_repos > 0 else 0
    
    c1.metric('仓库总数', total_repos)
    c2.metric('已对齐数', aligned_repos)
    c3.metric('对齐率', f"{alignment_rate:.1f}%")
    
    # 对齐策略分布
    st.subheader("对齐策略分布")
    strategy_counts = alignment_df['alignment_strategy'].value_counts().reset_index()
    strategy_counts.columns = ['strategy', 'count']
    fig = px.pie(strategy_counts, values='count', names='strategy', 
                 color_discrete_sequence=['#00d4ff', '#3366ff', '#8F00FF', '#ffab00'],
                 template='plotly_dark', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
    
    # 实体对齐明细
    st.subheader("实体对齐明细")
    st.dataframe(
        alignment_df.sort_values('alignment_strategy'),
        column_config={
            'gitlab_project_id': st.column_config.TextColumn('GitLab项目ID'),
            'project_name': st.column_config.TextColumn('项目名称'),
            'master_entity_id': st.column_config.TextColumn('主数据实体ID'),
            'master_entity_name': st.column_config.TextColumn('主数据实体名称'),
            'alignment_strategy': st.column_config.TextColumn('对齐策略'),
            'master_entity_importance': st.column_config.TextColumn('实体重要性')
        },
        use_container_width=True,
        hide_index=True
    )