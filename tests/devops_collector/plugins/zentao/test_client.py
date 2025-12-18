import unittest
from unittest.mock import patch, MagicMock
from devops_collector.plugins.zentao.client import ZenTaoClient

class TestZenTaoClient(unittest.TestCase):
    def setUp(self):
        self.client = ZenTaoClient("http://zentao.fake.com/api.php/v1", "token")

    @patch('requests.get')
    def test_get_products(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"products": [{"id": 1, "name": "Prod 1"}]}
        
        products = self.client.get_products()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['name'], "Prod 1")

    @patch('requests.get')
    def test_get_stories_pagination(self, mock_get):
        # Page 1: 3 total, returns 2
        # Page 2: returns 1
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"total": 3, "stories": [{"id": 1}, {"id": 2}]}),
            MagicMock(status_code=200, json=lambda: {"total": 3, "stories": [{"id": 3}]})
        ]
        
        stories = self.client.get_stories(1)
        self.assertEqual(len(stories), 3)
        self.assertEqual(mock_get.call_count, 2)

if __name__ == '__main__':
    unittest.main()
