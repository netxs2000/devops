"""多渠道风险预警推送脚本 (Multi-channel Risk Bot)

该脚本定时运行，从数据库风险宽表中获取异常记录，并推送到企业微信、飞书、钉钉。
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 确保代码在导入时能找到核心库
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devops_collector.core.notifiers import WeComBot, FeishuBot, DingTalkBot
from devops_config import config 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_risk_check():
    """执行风险检查并发送告警。"""
    
    # 1. 数据库连接
    db_uri = config.get('database', 'uri')
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 2. 初始化所有已配置的机器人
    bots = []
    
    wecom_url = config.get('notifiers', 'wecom_webhook')
    if wecom_url: bots.append(WeComBot(wecom_url))
        
    feishu_url = config.get('notifiers', 'feishu_webhook')
    if feishu_url: bots.append(FeishuBot(feishu_url))
        
    dingtalk_url = config.get('notifiers', 'dingtalk_webhook')
    if dingtalk_url: bots.append(DingTalkBot(dingtalk_url))

    if not bots:
        logger.error("No notification channels configured.")
        return
    
    try:
        # 3. 查询风险
        query = text("SELECT project_name, risk_type, severity, description, owner FROM view_pmo_risk_anomalies")
        risks = session.execute(query).fetchall()
        
        if not risks:
            logger.info("No risks detected.")
            return
            
        # 4. 扇出推送
        for r in risks:
            title = f"【风险预警】{r.project_name}"
            details = [
                {"风险类型": r.risk_type},
                {"异常描述": r.description},
                {"责任人": r.owner or "未指定"}
            ]
            
            for bot in bots:
                bot.send_risk_card(title, details, level=r.severity)
                
        logger.info(f"Broadcasted {len(risks)} risks to {len(bots)} channels.")
                
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    run_risk_check()
