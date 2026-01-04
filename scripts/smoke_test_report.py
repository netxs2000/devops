
"""
冒烟测试脚本：研发效能报告格式预览 (Mock Mode)
在没有真实数据库和机器人 Webhook 的情况下，验证报告生成逻辑与控制台输出。
"""

import sys
import os
from unittest.mock import MagicMock

# 模拟数据库返回的数据结构
class MockRow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# 确保脚本能加载本地模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 我们直接从 ExecutiveAuditBot 修改一个 Mock 版本进行冒烟测试
from scripts.executive_audit_report import ExecutiveAuditBot

def run_smoke_test():
    print("=== [SMOKE TEST] Executive Audit Report - Mock Mode ===\n")
    
    # 初始化 Bot
    bot = ExecutiveAuditBot()
    
    # 模拟数据库会话 (Mocking the session so it doesn't try to connect to a real DB)
    bot.session = MagicMock()
    
    # 模拟 fetch_hotspots 结果
    hotspots_data = [
        MockRow(file_path="app/services/order_service.py", risk_factor=45.2, churn_90d=24),
        MockRow(file_path="core/auth_provider.py", risk_factor=38.1, churn_90d=15)
    ]
    
    # 模拟 fetch_bus_factor_risks 结果
    bus_factor_data = [
        MockRow(subsystem="billing_engine", author_user_id="user_7e2a1b", subsystem_ownership_pct=92.5)
    ]
    
    # 模拟 fetch_talent_spotlight 结果
    talent_data = [
        MockRow(real_name="ZhangSan", talent_archetype="Domain Specialist", talent_influence_index=88.5),
        MockRow(real_name="LiSi", talent_archetype="Collaborative Leader", talent_influence_index=72.3)
    ]
    
    # 模拟 fetch_financial_audit 结果
    fin_audit_data = MockRow(
        audit_week="2026-W01", capitalization_rate=65.5, audit_status="AUDIT_READY"
    )

    # 劫持实例方法以返回 Mock 数据，避免真正的 SQL 执行
    bot.fetch_hotspots = MagicMock(return_value=hotspots_data)
    bot.fetch_bus_factor_risks = MagicMock(return_value=bus_factor_data)
    bot.fetch_financial_audit = MagicMock(return_value=fin_audit_data)
    bot.fetch_talent_spotlight = MagicMock(return_value=talent_data)

    # 运行 Bot (由于没有配置 Webhook，它会自动回退到控制台打印)
    bot.run()
    
    print("\n=== [SMOKE TEST] End of Mock Report ===")

if __name__ == "__main__":
    run_smoke_test()
