#!/usr/bin/env python3
"""
Unit test for WebSocket origin validation function
Tests the _validate_origin function directly without needing the server.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the backend directory to the path
sys.path.insert(0, '/root/.openclaw/workspace/cerebrum-fix/backend')


class MockWebSocket:
    """Mock WebSocket for testing."""
    def __init__(self, headers=None):
        self.headers = headers or {}


class TestValidateOrigin(unittest.TestCase):
    """Test cases for _validate_origin function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import here to ensure fresh module state
        from app.agent.websocket import _validate_origin
        self.validate_origin = _validate_origin
    
    def _create_mock_settings(self, debug=False, cors_origins=None):
        """Create mock settings object."""
        mock_settings = MagicMock()
        mock_settings.DEBUG = debug
        mock_settings.cors_origins_list = cors_origins or ["http://localhost:3000"]
        return mock_settings
    
    @patch('app.core.config.settings')
    def test_debug_mode_allows_all(self, mock_settings):
        """Test that DEBUG=True allows all origins."""
        mock_settings.DEBUG = True
        mock_settings.cors_origins_list = []
        
        # Should allow any origin in debug mode
        ws_no_origin = MockWebSocket({})
        self.assertTrue(self.validate_origin(ws_no_origin))
        
        ws_localhost = MockWebSocket({"origin": "http://localhost:3000"})
        self.assertTrue(self.validate_origin(ws_localhost))
        
        ws_evil = MockWebSocket({"origin": "http://evil.com"})
        self.assertTrue(self.validate_origin(ws_evil))
    
    @patch('app.core.config.settings')
    def test_no_origin_header_allowed(self, mock_settings):
        """Test that empty origin header is allowed (non-browser clients)."""
        mock_settings.DEBUG = False
        mock_settings.cors_origins_list = []
        
        ws_no_origin = MockWebSocket({})
        self.assertTrue(self.validate_origin(ws_no_origin))
        
        ws_empty_origin = MockWebSocket({"origin": ""})
        self.assertTrue(self.validate_origin(ws_empty_origin))
    
    @patch('app.core.config.settings')
    def test_localhost_origins_allowed(self, mock_settings):
        """Test that localhost origins are allowed."""
        mock_settings.DEBUG = False
        mock_settings.cors_origins_list = []
        
        test_cases = [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            "ws://localhost:8000",
            "wss://localhost:8000",
        ]
        
        for origin in test_cases:
            ws = MockWebSocket({"origin": origin})
            self.assertTrue(self.validate_origin(ws), f"Should allow: {origin}")
    
    @patch('app.core.config.settings')
    def test_cors_origins_allowed(self, mock_settings):
        """Test that CORS origins from settings are allowed."""
        mock_settings.DEBUG = False
        mock_settings.cors_origins_list = ["https://cerebrum-frontend.onrender.com"]
        
        ws = MockWebSocket({"origin": "https://cerebrum-frontend.onrender.com"})
        self.assertTrue(self.validate_origin(ws))
    
    @patch('app.core.config.settings')
    def test_file_origin_allowed(self, mock_settings):
        """Test that file:// origins are allowed (local file clients)."""
        mock_settings.DEBUG = False
        mock_settings.cors_origins_list = []
        
        ws = MockWebSocket({"origin": "file:///path/to/client.html"})
        self.assertTrue(self.validate_origin(ws))
    
    @patch('app.core.config.settings')
    def test_invalid_origin_rejected(self, mock_settings):
        """Test that invalid origins are rejected."""
        mock_settings.DEBUG = False
        mock_settings.cors_origins_list = []
        
        ws = MockWebSocket({"origin": "http://evil.com"})
        self.assertFalse(self.validate_origin(ws))
        
        ws2 = MockWebSocket({"origin": "https://malicious-site.com"})
        self.assertFalse(self.validate_origin(ws2))


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Origin Validation Unit Tests")
    print("=" * 60)
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestValidateOrigin)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
