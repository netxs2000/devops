from devops_collector.config import settings
from devops_collector.plugins.zentao.client import ZenTaoClient


client = ZenTaoClient(
    url=settings.zentao.url,
    token=settings.zentao.token,
    account=settings.zentao.account,
    password=settings.zentao.password,
)
resp = client._get("departments")
depts = resp.json()
print("Type:", type(depts))
if isinstance(depts, dict):
    print("Keys:", list(depts.keys()))
    first_dept = depts.get("departments") or depts.get("items") or list(depts.values())
    print("Sample:", first_dept[:2] if isinstance(first_dept, list) else first_dept)
elif isinstance(depts, list):
    print("List len:", len(depts))
    print("First item:", depts[0] if depts else "empty")
