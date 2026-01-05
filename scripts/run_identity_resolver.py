"""身份自动治理引擎 (Identity Resolver Engine)

该脚本用于扫描 mdm_identity_mappings 表中尚未验证或自动生成的身份。
通过模糊匹配与启发式规则计算置信度（Confidence Score），并将外部帐号对齐到 HR 金数据用户。

遵循 Google Python Style Guide。
"""
import os
import sys
import logging
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker

# 确保可以导入项目模块
sys.path.append(os.getcwd())

from devops_collector.config import Config
from devops_collector.models.base_models import User, IdentityMapping

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [IdentityResolver] %(message)s'
)
logger = logging.getLogger(__name__)

class IdentityResolver:
    """身份对齐治理类。"""

    def __init__(self, session):
        self.session = session
        # 获取所有有效的 MDM 用户（金数据）
        self.mdm_users = self.session.query(User).filter(
            User.is_current == True,
            User.employee_id != None  # 必须有工号的才是金数据用户
        ).all()
        logger.info(f"Loaded {len(self.mdm_users)} MDM golden users for matching.")

    def run(self, dry_run=False):
        """执行治理循环。"""
        # 查找所有待治理的映射：未验证且置信度不为 1 的
        mappings = self.session.query(IdentityMapping).filter(
            or_(
                IdentityMapping.mapping_status == 'PENDING',
                IdentityMapping.mapping_status == 'AUTO',
                IdentityMapping.confidence_score < 1.0
            )
        ).all()

        logger.info(f"Found {len(mappings)} identity mappings to re-evaluate.")
        
        updated_count = 0
        for mapping in mappings:
            best_match, score = self._find_best_match(mapping)
            
            if best_match and score >= 0.6:
                if mapping.global_user_id != best_match.global_user_id or mapping.confidence_score != score:
                    logger.info(f"Match found: {mapping.external_username} -> {best_match.full_name} (Score: {score})")
                    
                    if not dry_run:
                        mapping.global_user_id = best_match.global_user_id
                        mapping.confidence_score = score
                        # 超过 0.9 自动标记为验证，否则标记待确认
                        mapping.mapping_status = 'AUTO' if score < 0.9 else 'VERIFIED'
                    updated_count += 1

        if not dry_run:
            self.session.commit()
            logger.info(f"Governance complete. Updated {updated_count} mappings.")
        else:
            logger.info(f"[Dry Run] Would have updated {updated_count} mappings.")

    def _find_best_match(self, mapping):
        """核心匹配逻辑。"""
        email = (mapping.external_email or "").lower()
        ext_username = (mapping.external_username or "").lower()
        ext_uid = (mapping.external_user_id or "").lower()
        
        email_prefix = email.split('@')[0] if '@' in email else None

        best_user = None
        max_score = 0.0

        for user in self.mdm_users:
            current_score = 0.0
            u_email = user.primary_email.lower() if user.primary_email else ""
            u_name = user.full_name.lower() if user.full_name else ""
            u_emp_id = user.employee_id.lower() if user.employee_id else ""

            # 1. Email 精确匹配 (Weight: 1.0)
            if email and email == u_email:
                current_score = 1.0
            
            # 2. 工号精确匹配 (Weight: 1.0)
            elif ext_uid == u_emp_id:
                current_score = 1.0
                
            # 3. Email 前缀匹配 (Weight: 0.8)
            elif email_prefix and (email_prefix == u_emp_id or email_prefix == user.username):
                current_score = 0.8
                
            # 4. 姓名 + Email 域匹配 (Weight: 0.7)
            elif ext_username == u_name and "@" in email:
                # 检查是否是公司内部域名
                if email.endswith("@yourcompany.com"): # TODO: 从配置读取
                    current_score = 0.7
                else:
                    current_score = 0.5
            
            # 5. 仅姓名匹配 (Weight: 0.4)
            elif ext_username == u_name:
                current_score = 0.4

            if current_score > max_score:
                max_score = current_score
                best_user = user
                
            if max_score == 1.0: # 找到完美匹配直接退出
                break
                
        return best_user, max_score

def main():
    """入口函数。"""
    logger.info("Starting Identity Resolver script...")
    
    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        resolver = IdentityResolver(session)
        # 默认执行 Dry run
        dry_run = "--apply" not in sys.argv
        if dry_run:
            logger.info("Running in DRY-RUN mode. Use --apply to save changes.")
        
        resolver.run(dry_run=dry_run)
    except Exception as e:
        logger.error(f"Resolver failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
