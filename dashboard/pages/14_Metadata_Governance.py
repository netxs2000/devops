import streamlit as st
import pandas as pd
from utils import get_db_connection

def run():
    st.set_page_config(page_title="Metadata Governance | DataHub", layout="wide")
    
    st.title("🛡️ 元数据治理与血缘目录")
    st.markdown("---")

    st.sidebar.info("基于 DataHub 的现代元数据管理系统。支持全链路血缘追踪与数据资产目录索引。")

    # 快捷统计与状态
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("治理实体总数", "128+", "+12%")
    with col2:
        st.metric("血缘覆盖率", "94%", "+5%")
    with col3:
        st.metric("元数据健康得分", "98", "Excellent")

    st.markdown("### 🔭 DataHub 治理视图")
    st.info("提示: 下方为 DataHub 管理控制台。您可以在此搜索表、查看字段描述以及 dbt 管道血缘。")
    
    # 嵌入 DataHub Web UI
    # 默认端口 9002
    datahub_url = "http://localhost:9002"
    
    st.components.v1.iframe(datahub_url, height=800, scrolling=True)

    st.markdown("### 🛠️ 运维操作")
    if st.button("🚀 立即触发全量元数据扫描 (Batch Ingestion)"):
        st.code("make datahub-ingest")
        st.warning("请确保 DataHub Ingestion CLI 已安装且本地 Docker 服务已启动。")

if __name__ == "__main__":
    run()
