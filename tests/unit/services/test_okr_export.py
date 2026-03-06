import csv
import io
import uuid

import pytest
from sqlalchemy.orm import Session

from devops_collector.core.admin_service import AdminService
from devops_collector.models.base_models import OKRKeyResult, OKRObjective, Organization, User


@pytest.fixture
def admin_service(db_session: Session):
    return AdminService(db_session)


def test_export_okrs_content(admin_service, db_session):
    """验证 OKR 导出内容、格式及进度计算。"""
    # 1. 准备 mock 数据
    user = User(global_user_id=uuid.uuid4(), full_name="测试负责人", primary_email="test_owner@example.com", is_current=True)
    org = Organization(org_id="TEST-ORG", org_name="测试组织", is_current=True)
    db_session.add_all([user, org])
    db_session.flush()

    obj = OKRObjective(
        objective_id="OBJ-UNIT-TEST",
        title="单元测试目标",
        period="2024-Q1",
        owner_id=user.global_user_id,
        org_id=org.org_id,
        status="ACTIVE",
        progress=0.5,  # 50%
    )
    db_session.add(obj)
    db_session.flush()

    kr1 = OKRKeyResult(objective_id=obj.id, title="关键结果1", target_value=100.0, current_value=60.0, progress=0.6, unit="个")
    db_session.add(kr1)
    db_session.commit()

    # 2. 执行导出
    csv_str = admin_service.export_okrs(period="2024-Q1")

    # 3. 验证格式和内容
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["目标标题"] == "单元测试目标"
    assert row["负责人"] == "测试负责人"
    assert row["目标进度%"] == "50.0%"
    assert row["关键结果标题"] == "关键结果1"
    assert row["KR进度%"] == "60.0%"
    assert row["单位"] == "个"


def test_export_okrs_empty_filter(admin_service, db_session):
    """验证过滤器不匹配时返回空表头。"""
    csv_str = admin_service.export_okrs(period="NON-EXISTENT")
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 0
