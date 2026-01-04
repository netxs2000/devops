
"""
研发体系月度效能与审计自动播报脚本 (Executive Audit & Efficiency Report)

核心功能：
1. 技术风险审计：识别 RED_ZONE 代码热点（Michael Feathers 指标）。
2. 知识风险预警：识别核心子系统的 Bus Factor（单点知识孤岛）。
3. 财务合规分析：识别研发资本化率异常（CapEx vs OpEx）。
4. 人才星探：汇总高影响力开发者。
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 确保能找到项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devops_collector.config import settings
from devops_collector.core.notifiers import WeComBot, FeishuBot, DingTalkBot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExecutiveAuditBot:
    def __init__(self):
        self.engine = create_engine(settings.database.uri)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.report_date = datetime.now().strftime('%Y-%m-%d')
        
        # 初始化机器人
        self.bots = []
        # 尝试从环境变量或 settings 加载（根据实际配置结构调整）
        # 这里演示假设 settings.wecom.webhook 存在，或者直接读 ENV
        wecom_webhook = os.getenv('WECOM_WEBHOOK')
        if wecom_webhook:
            self.bots.append(WeComBot(wecom_webhook))

    def fetch_hotspots(self):
        """获取代码红区风险。"""
        query = text("""
            SELECT file_path, risk_factor, churn_90d 
            FROM fct_code_hotspots 
            WHERE risk_zone = 'RED_ZONE' 
            ORDER BY risk_factor DESC 
            LIMIT 5
        """)
        return self.session.execute(query).fetchall()

    def fetch_bus_factor_risks(self):
        """获取知识孤岛风险。"""
        query = text("""
            SELECT subsystem, author_user_id, subsystem_ownership_pct, knowledge_risk_status 
            FROM dws_subsystem_bus_factor 
            WHERE knowledge_risk_status IN ('KNOWLEDGE_SILO', 'TRUCK_FACTOR_ONE') 
            ORDER BY subsystem_ownership_pct DESC 
            LIMIT 5
        """)
        return self.session.execute(query).fetchall()

    def fetch_financial_audit(self):
        """获取财务审计概览。"""
        query = text("""
            SELECT audit_week, capitalization_rate, audit_status 
            FROM fct_capitalization_audit 
            ORDER BY audit_week DESC 
            LIMIT 1
        """)
        return self.session.execute(query).fetchone()

    def fetch_talent_spotlight(self):
        """获取本月 Top 影响力开发者。"""
        query = text("""
            SELECT real_name, talent_archetype, talent_influence_index 
            FROM fct_talent_radar 
            ORDER BY talent_influence_index DESC 
            LIMIT 3
        """)
        return self.session.execute(query).fetchall()

    def run(self):
        logger.info("Starting Executive Audit Report Generation...")
        
        hotspots = self.fetch_hotspots()
        bus_risks = self.fetch_bus_factor_risks()
        fin_audit = self.fetch_financial_audit()
        talents = self.fetch_talent_spotlight()

        # 构建报告内容
        title = f"[Audit] 研发效能与风险月度审计报告 ({self.report_date})"
        
        details = []
        
        # 1. 技术风险
        hotspot_str = "\n".join([f"• {r.file_path.split('/')[-1]} (Risk: {r.risk_factor})" for r in hotspots])
        details.append({"技术热点风险": hotspot_str or "暂无显著红区"})
        
        # 2. 知识风险
        bus_risk_str = "\n".join([f"• {r.subsystem}: {r.subsystem_ownership_pct}% by user_id {str(r.author_user_id)[:8]}" for r in bus_risks])
        details.append({"知识孤岛预警": bus_risk_str or "知识分布健康"})
        
        # 3. 财务核算
        if fin_audit:
            fin_str = f"本周资本化率: {fin_audit.capitalization_rate}% | 状态: {fin_audit.audit_status}"
            details.append({"研发投入审计": fin_str})
        
        # 4. 人才星探
        talent_str = "\n".join([f"• {r.real_name} [{r.talent_archetype}] (Index: {r.talent_influence_index})" for r in talents])
        details.append({"关键影响力人才": talent_str or "数据计算中"})

        # 执行推送
        if not self.bots:
            logger.warning("No bots configured. Printing report to console:")
            print(f"\n=== {title} ===")
            for d in details:
                for k, v in d.items():
                    print(f"\n[{k}]\n{v}")
            return

        for bot in self.bots:
            try:
                bot.send_risk_card(title, details, level="HIGH" if hotspots else "INFO")
                logger.info(f"Report sent to {bot.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed to send report: {e}")

        self.session.close()

if __name__ == "__main__":
    ExecutiveAuditBot().run()
