"""
tests/test_error_handlers.py
=============================
Step 14: Custom Error Handlers (404, 403, 500) Tests
"""

import unittest
from app import app
from database.db import init_db

class TestErrorHandlers(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = app.test_client()
        self.client.testing = True

    def test_404_error_page(self):
        response = self.client.get('/non-existent-route-12345')
        self.assertEqual(response.status_code, 404)
        html = response.get_data(as_text=True)
        self.assertIn("Page Not Found", html)
        self.assertIn("404", html)

    def test_403_access_denied_page(self):
        self.client.post('/login', data={'username': 'developer1', 'password': 'password123'})
        response = self.client.get('/projects/999/standup', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("do not have access", html)


if __name__ == '__main__':
    unittest.main()
