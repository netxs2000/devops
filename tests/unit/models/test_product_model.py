"""TODO: Add module description."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devops_collector.models.base_models import Base, Organization, Product, User


class TestProductModel(unittest.TestCase):
    '''"""TODO: Add class description."""'''

    def setUp(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        self.session.close()

    def test_product_hierarchy_and_roles(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        center = Organization(org_code="FIN_CENTER", org_name="Financial Services Center", org_level=1)
        self.session.add(center)
        self.session.flush()
        pm = User(username="pm_user", full_name="Product Manager", primary_email="pm@example.com", employee_id="HR001")
        dev = User(username="dev_user", full_name="Dev Lead", primary_email="dev@example.com", employee_id="HR002")
        self.session.add_all([pm, dev])
        self.session.flush()
        pline = Product(
            product_code="BANK_LINE",
            product_name="Retail Banking Line",
            node_type="LINE",
            owner_team_id=center.id,
            product_description="Retail Banking Product Line",
            version_schema="SemVer",
        )
        self.session.add(pline)
        self.session.flush()
        prod = Product(
            product_code="MOBILE_APP",
            product_name="Mobile App",
            node_type="APP",
            parent_product_id=pline.id,
            owner_team_id=center.id,
            product_manager_id=pm.global_user_id,
            dev_lead_id=dev.global_user_id,
            product_description="Mobile App for Banking",
            version_schema="SemVer",
        )
        self.session.add(prod)
        self.session.commit()
        saved_prod = self.session.query(Product).filter_by(product_name="Mobile App").first()
        self.assertEqual(saved_prod.parent.product_name, "Retail Banking Line")
        self.assertEqual(saved_prod.owner_team.org_name, "Financial Services Center")
        self.assertEqual(saved_prod.product_manager.full_name, "Product Manager")
        self.assertEqual(saved_prod.dev_lead.full_name, "Dev Lead")
        saved_pline = self.session.query(Product).filter_by(product_name="Retail Banking Line").first()
        self.assertEqual(len(saved_pline.children), 1)
        self.assertEqual(saved_pline.children[0].product_name, "Mobile App")


if __name__ == "__main__":
    unittest.main()
