"""TODO: Add module description."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, Organization, Product

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
        self.engine = create_engine('sqlite:///:memory:')
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
        center = Organization(name='Financial Services Center', level='Center')
        self.session.add(center)
        self.session.flush()
        pm = User(username='pm_user', name='Product Manager', email='pm@example.com')
        dev = User(username='dev_user', name='Dev Lead', email='dev@example.com')
        self.session.add_all([pm, dev])
        self.session.flush()
        pline = Product(name='Retail Banking Line', level='Line', organization_id=center.id)
        self.session.add(pline)
        self.session.flush()
        prod = Product(name='Mobile App', level='Product', parent_id=pline.id, product_line_name=pline.name, organization_id=center.id, product_manager_id=pm.id, dev_manager_id=dev.id)
        self.session.add(prod)
        self.session.commit()
        saved_prod = self.session.query(Product).filter_by(name='Mobile App').first()
        self.assertEqual(saved_prod.parent.name, 'Retail Banking Line')
        self.assertEqual(saved_prod.product_line_name, 'Retail Banking Line')
        self.assertEqual(saved_prod.organization.name, 'Financial Services Center')
        self.assertEqual(saved_prod.product_manager.name, 'Product Manager')
        self.assertEqual(saved_prod.dev_manager.name, 'Dev Lead')
        saved_pline = self.session.query(Product).filter_by(name='Retail Banking Line').first()
        self.assertEqual(len(saved_pline.children), 1)
        self.assertEqual(saved_pline.children[0].name, 'Mobile App')
if __name__ == '__main__':
    unittest.main()