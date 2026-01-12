"""调试登录问题的脚本。"""
import sys
sys.path.insert(0, 'c:\\Users\\netxs\\devops\\devops')

from devops_collector.auth.database import SessionLocal
from devops_collector.auth.services import get_user_by_email, verify_password
from devops_collector.models.base_models import User, UserCredential

def debug_login():
    """诊断登录问题。"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("1. 检查数据库连接...")
        print("=" * 60)
        
        # 检查用户表
        user_count = db.query(User).count()
        print(f"   用户总数: {user_count}")
        
        # 检查凭据表
        cred_count = db.query(UserCredential).count()
        print(f"   凭据总数: {cred_count}")
        
        print("\n" + "=" * 60)
        print("2. 查找管理员用户 admin@tjhq.com...")
        print("=" * 60)
        
        user = get_user_by_email(db, "admin@tjhq.com")
        if user:
            print(f"   找到用户: {user.full_name}")
            print(f"   Global User ID: {user.global_user_id}")
            print(f"   Primary Email: {user.primary_email}")
            print(f"   Is Active: {user.is_active}")
            print(f"   Is Current: {user.is_current}")
            
            print("\n" + "=" * 60)
            print("3. 检查用户凭据...")
            print("=" * 60)
            
            if user.credential:
                print(f"   凭据存在: 是")
                print(f"   密码哈希前10字符: {user.credential.password_hash[:10]}...")
                
                # 验证密码
                test_password = "admin_password_123!"
                is_valid = verify_password(test_password, user.credential.password_hash)
                print(f"   密码验证 (admin_password_123!): {'成功' if is_valid else '失败'}")
            else:
                print("   凭据存在: 否 - 这是问题所在!")
                print("   用户没有关联的凭据记录")
        else:
            print("   未找到用户 admin@tjhq.com")
            print("\n   列出所有用户:")
            all_users = db.query(User).filter(User.is_current == True).limit(10).all()
            for u in all_users:
                print(f"     - {u.primary_email} ({u.full_name})")
                
    except Exception as e:
        print(f"错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_login()
