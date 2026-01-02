"""TODO: Add module description."""
import streamlit as st
import networkx as nx
import plotly.graph_objects as go
from utils import run_query, set_page_config
set_page_config()
st.title('🔗 模糊实体对齐与链接 (Entity Alignment)')
st.markdown('---')
alignment_df = run_query('SELECT source_entity_id, target_entity_id, alignment_type, confidence_score, mapping_reason FROM int_entity_alignment')
st.markdown('\n平台通过语义识别与启发式算法，自动发现不同系统间的隐含关联。\n例如：Jira Issue 与 GitLab Merge Request 的自动链接，或 Sonar 项目与 Jenkins 任务的对齐。\n')
c1, c2 = st.columns(2)
c1.metric('对齐链接总数', len(alignment_df))
c2.metric('平均置信度', f"{alignment_df['confidence_score'].mean() * 100:.1f}%")
st.markdown('### 实体对齐明细')
st.dataframe(alignment_df.sort_values('confidence_score', ascending=False), use_container_width=True)
st.markdown('### 实体关联拓扑 (Top 20 置信度)')
top_links = alignment_df.nlargest(20, 'confidence_score')
G = nx.Graph()
for _, row in top_links.iterrows():
    G.add_edge(row['source_entity_id'], row['target_entity_id'], weight=row['confidence_score'], type=row['alignment_type'])
pos = nx.spring_layout(G)
edge_x = []
edge_y = []
for edge in G.edges():
    x0, y0 = pos[edge[0]]
    x1, y1 = pos[edge[1]]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])
edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), hoverinfo='none', mode='lines')
node_x = []
node_y = []
node_text = []
for node in G.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)
    node_text.append(str(node))
node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', hoverinfo='text', text=node_text, marker=dict(showscale=False, color='#636EFA', size=15, line_width=2))
fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(title='实体对齐知识图谱 (示例)', showlegend=False, hovermode='closest', margin=dict(b=20, l=5, r=5, t=40), xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'))
st.plotly_chart(fig, use_container_width=True)