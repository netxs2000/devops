"""PyAirbyte GitLab 集成原型验证脚本。

本脚本演示如何使用 airbyte 库直接在 Python 中调用 GitLab 连接器，
并利用 DuckDB 作为本地缓存，实现轻量级的数据提取。
"""

import os
import logging
from typing import Any, Dict, List
import airbyte as ab
from devops_collector.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_gitlab_source() -> ab.Source:
    """初始化 GitLab 数据源。

    Returns:
        ab.Source: 配置好的 Airbyte Source 对象。
    """
    logger.info("正在初始化 GitLab 数据源...")
    
    # 构造连接器配置
    # 注意：连接器配置参数需参考 Airbyte 官方文档：
    # https://docs.airbyte.com/integrations/sources/gitlab
    config: Dict[str, Any] = {
        "api_url": settings.gitlab.url,
        "credentials": {
            "auth_type": "access_token",
            "access_token": settings.gitlab.private_token
        },
        "start_date": "2024-01-01T00:00:00Z",
        "groups": ""  # 可选，同步特定群组
    }
    
    source = ab.get_source("source-gitlab", config=config)
    return source

def run_prototype_sync():
    """执行原型同步流程。
    
    该函数演示了：
    1. 获取数据源
    2. 检查连接（虽环境未连接，但演示代码逻辑）
    3. 同步数据到 DuckDB 缓存
    4. 读取为 Pandas DataFrame
    """
    try:
        source = setup_gitlab_source()
        
        # 验证连接情况
        logger.info("测试连接中...")
        check_result = source.check()
        if not check_result:
            logger.warning("连接测试未通过（预期行为，因为环境未连接），将仅展示配置逻辑。")
        else:
            logger.info("连接测试成功！")

        # 列出所有可用的数据流
        logger.info("可用数据流: %s", source.streams)
        
        # 演示：仅选取部分流进行同步（如 projects, issues）
        # source.select_streams(["projects", "issues"])
        
        # 将数据同步到内存/本地缓存 (DuckDB)
        # cache = ab.get_default_cache()
        # result = source.read(cache=cache)
        
        # 演示：将同步的数据读取为 DataFrame
        # df = result["projects"].to_pandas()
        # logger.info("成功获取项目数据，共 %d 条记录", len(df))
        
        logger.info("原型代码逻辑加载成功。")

    except Exception as e:
        logger.error("运行原型同步时发生错误: %s", e)

if __name__ == "__main__":
    run_prototype_sync()
