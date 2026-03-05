import os
import sys
import logging
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
# 尝试导入所有模型以避免 SQLAlchemy 映射错误
import devops_collector.models 
from devops_collector.plugins.zentao.client import ZenTaoClient
from devops_collector.plugins.zentao.models import ZenTaoProduct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DiagZenTao")

def diag_zentao():
    print("="*60)
    print("ZenTao Connection & Model Diagnosis")
    print("="*60)
    
    # 1. 检查配置
    print(f"URL: {settings.zentao.url}")
    print(f"Token: {settings.zentao.token[:5]}***{settings.zentao.token[-5:] if len(settings.zentao.token)>10 else ''}")
    
    # 2. 测试 API 连通性
    print("\n[1/3] Testing API connectivity...")
    client = ZenTaoClient(url=settings.zentao.url, token=settings.zentao.token)
    try:
        # 使用基础 requests 测试以获得更多信息
        headers = {"Token": settings.zentao.token, "Accept": "application/json"}
        resp = requests.get(f"{settings.zentao.url}/products", headers=headers, verify=False)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            products = resp.json().get('products', [])
            print(f"✓ Success! Found {len(products)} products.")
        else:
            print(f"✗ Failed! Body: {resp.text}")
            
            # 尝试不同的 Header
            print("\nTrying with x-zentao-token...")
            resp2 = requests.get(f"{settings.zentao.url}/products", headers={"x-zentao-token": settings.zentao.token}, verify=False)
            print(f"x-zentao-token Status: {resp2.status_code}")
            
            print("\nTrying with Authorization Header...")
            resp3 = requests.get(f"{settings.zentao.url}/products", headers={"Authorization": f"Bearer {settings.zentao.token}"}, verify=False)
            print(f"Authorization Status: {resp3.status_code}")
            
    except Exception as e:
        print(f"✗ API Error: {e}")

    # 3. 检查数据库和模型映射
    print("\n[2/3] Checking DB mapping...")
    try:
        engine = create_engine(settings.database.uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        p_count = session.query(ZenTaoProduct).count()
        print(f"✓ DB connection OK. ZenTaoProduct count: {p_count}")
        session.close()
    except Exception as e:
        print(f"✗ DB Mapping Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diag_zentao()
