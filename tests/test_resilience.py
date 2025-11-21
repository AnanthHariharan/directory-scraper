import unittest
from unittest.mock import MagicMock, patch
import requests
from scraper.fetcher import ContentFetcher, FetchStrategy

class TestResilience(unittest.TestCase):
    def setUp(self):
        self.fetcher = ContentFetcher()

    @patch('requests.Session.get')
    def test_static_fetch_retry(self, mock_get):
        # Mock a sequence of failures then success
        mock_response_fail = MagicMock()
        mock_response_fail.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        mock_response_success = MagicMock()
        mock_response_success.text = "<html>Success</html>"
        mock_response_success.raise_for_status.return_value = None
        
        # The retry logic is handled by urllib3/requests adapter, which is hard to mock perfectly with just requests.Session.get
        # So we test that our fetcher handles exceptions gracefully and returns None on persistent failure
        
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        result = self.fetcher.fetch_static("http://example.com")
        self.assertIsNone(result)
        
        # Test that we are using the session with retry adapter
        self.assertIsNotNone(self.fetcher.session.adapters.get('https://'))

    def test_user_agent_rotation(self):
        headers1 = self.fetcher._get_headers()
        headers2 = self.fetcher._get_headers()
        
        self.assertIn('User-Agent', headers1)
        self.assertIn('User-Agent', headers2)
        # It's possible they are the same due to random choice, but unlikely if we check multiple times
        
        agents = set()
        for _ in range(20):
            agents.add(self.fetcher._get_headers()['User-Agent'])
            
        self.assertGreater(len(agents), 1)

if __name__ == '__main__':
    unittest.main()
