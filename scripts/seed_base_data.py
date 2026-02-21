"""
Seed base data (Organizations & Products) from docs/ CSV files.

Reads docs/organizations.csv and docs/products.csv, transforms them
to match the DB schema, and inserts via SQLAlchemy.

Usage (in Docker):
    docker-compose exec api python scripts/seed_base_data.py
"""

import sys
import csv
import io
import hashlib
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from devops_collector.config import settings
from devops_collector.models.base_models import Organization, Product, User


def generate_org_id(name: str) -> str:
    """Generate a stable, short org_id from name hash."""
    return "ORG_" + hashlib.md5(name.encode()).hexdigest()[:8].upper()


def seed_organizations(session: Session, csv_path: Path):
    """Import hierarchical organizations from CSV.
    
    CSV format: 中心, 部门, 负责人, 所属体系
    Maps to 3 levels:
      Level 1: 公司 (Root)
      Level 2: 中心 (e.g., 财政研发中心)
      Level 3: 部门 (e.g., 测试部)
    "所属体系" is saved as business_line attribute.
    """
    print(f"\n--- Seeding Organizations from {csv_path} ---")
    
    if not csv_path.exists():
        print(f"WARN: {csv_path} not found, skipping.")
        return

    # Clear existing organizations to start fresh
    session.execute(text("UPDATE mdm_identities SET department_id = NULL"))
    session.execute(text("UPDATE mdm_product SET owner_team_id = NULL"))
    session.execute(text("UPDATE mdm_organizations SET parent_org_id = NULL"))
    session.execute(text("DELETE FROM mdm_organizations"))
    session.commit()
    print("Cleared existing organizations.")

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Build user name -> user map for manager lookup
    users = {u.full_name: u for u in session.query(User).filter(User.is_current == True).all()}

    created_orgs = {}  # org_name -> org_id (for dedup)
    stats = {"created": 0, "skipped": 0}

    # --- Level 1: 公司 (Root) ---
    root_org_id = generate_org_id("公司")
    root_org = Organization(
        org_id=root_org_id, org_name="公司", org_level=1,
        parent_org_id=None, business_line=None,
        is_active=True, is_current=True, sync_version=1
    )
    session.add(root_org)
    created_orgs["公司"] = root_org_id
    stats["created"] += 1

    for row in rows:
        tixi = (row.get('所属体系') or '').strip()
        center = (row.get('中心') or '').strip()
        dept = (row.get('部门') or '').strip()
        manager_name = (row.get('负责人') or '').strip()

        if not center:
            continue

        # --- Level 2: 中心 ---
        if center and center not in created_orgs:
            org_id = generate_org_id(center)
            parent_id = root_org_id
            mgr_uid = None
            # Only set manager for center-level if this row has no dept (center row)
            if not dept and manager_name and manager_name in users:
                mgr_uid = users[manager_name].global_user_id

            org = Organization(
                org_id=org_id, org_name=center, org_level=2,
                parent_org_id=parent_id, manager_user_id=mgr_uid,
                business_line=tixi or None,
                is_active=True, is_current=True, sync_version=1
            )
            session.add(org)
            stats["created"] += 1
            created_orgs[center] = org_id

        # --- Level 3: 部门 ---
        if dept and dept not in created_orgs:
            org_id = generate_org_id(dept)
            parent_id = created_orgs.get(center)
            mgr_uid = None
            if manager_name and manager_name in users:
                mgr_uid = users[manager_name].global_user_id

            org = Organization(
                org_id=org_id, org_name=dept, org_level=3,
                parent_org_id=parent_id, manager_user_id=mgr_uid,
                business_line=tixi or None,
                is_active=True, is_current=True, sync_version=1
            )
            session.add(org)
            stats["created"] += 1
            created_orgs[dept] = org_id

    session.commit()
    print(f"Organizations: {stats['created']} created, {stats['skipped']} skipped.")


def seed_products(session: Session, csv_path: Path):
    """Import products from CSV.
    
    CSV format: PRODUCT_ID, 产品名称, 节点类型, parent_product_id, 产品分类, ...
    """
    print(f"\n--- Seeding Products from {csv_path} ---")
    
    if not csv_path.exists():
        print(f"WARN: {csv_path} not found, skipping.")
        return

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Build org name -> org_id map for owner_team lookup
    org_name_map = {
        o.org_name: o.org_id
        for o in session.query(Organization).filter(Organization.is_current == True).all()
    }

    stats = {"created": 0, "skipped": 0}

    for row in rows:
        pid = (row.get('PRODUCT_ID') or row.get('product_id') or '').strip()
        name = (row.get('产品名称') or row.get('product_name') or '').strip()
        node_type = (row.get('节点类型') or row.get('node_type') or 'APP').strip()
        parent_id = (row.get('parent_product_id') or '').strip() or None
        category = (row.get('产品分类') or row.get('category') or '').strip() or None
        version_schema = (row.get('version_schema') or 'SemVer').strip()
        owner_team_name = (row.get('负责团队') or row.get('owner_team_id') or '').strip() or None

        # Resolve team name to org_id FK, set None if not found
        owner_team_id = org_name_map.get(owner_team_name) if owner_team_name else None

        if not pid or not name:
            continue

        existing = session.query(Product).filter(Product.product_id == pid).first()
        if existing:
            stats["skipped"] += 1
            continue

        product = Product(
            product_id=pid,
            product_name=name,
            product_description=f"{name} 产品线",
            node_type=node_type,
            parent_product_id=parent_id,
            category=category,
            version_schema=version_schema,
            owner_team_id=owner_team_id,
            lifecycle_status='active'
        )
        session.add(product)
        stats["created"] += 1

    session.commit()
    print(f"Products: {stats['created']} created, {stats['skipped']} skipped (already exist).")


def main():
    docs_dir = Path(__file__).parent.parent / 'docs'
    
    engine = create_engine(settings.database.uri)
    with Session(engine) as session:
        seed_organizations(session, docs_dir / 'organizations.csv')
        seed_products(session, docs_dir / 'products.csv')
    
    print("\n✅ Base data seeding complete.")


if __name__ == '__main__':
    main()
