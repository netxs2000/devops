"""TODO: Add module description."""

import unittest
from unittest.mock import MagicMock, patch

from devops_collector.plugins.zentao.client import ZenTaoClient


class TestZenTaoClient(unittest.TestCase):
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
        self.client = ZenTaoClient("http://zentao.fake.com/api.php/v1", "token")

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.request")
    def test_get_products(self, mock_request, mock_sleep):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"products": [{"id": 1, "name": "Prod 1"}]}
        mock_request.return_value = mock_response
        
        products = self.client.get_products()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["name"], "Prod 1")

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.request")
    def test_get_stories_pagination(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            MagicMock(status_code=200, json=lambda: {"total": 3, "stories": [{"id": 1}, {"id": 2}]}),
            MagicMock(status_code=200, json=lambda: {"total": 3, "stories": [{"id": 3}]}),
        ]
        stories = self.client.get_stories(1)
        self.assertEqual(len(stories), 3)
        self.assertGreaterEqual(mock_request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
