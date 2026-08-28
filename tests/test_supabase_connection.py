"""
tests/test_supabase_connection.py
==================================
Unit and Integration Tests for Supabase Connection & Health Checks.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from app import app
import utils.supabase_client as sc

class TestSupabaseConnection(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        # Reset singleton client for test isolation
        sc._supabase_client = None

    def tearDown(self):
        sc._supabase_client = None

    @patch.dict(os.environ, {'SUPABASE_URL': '', 'SUPABASE_KEY': ''}, clear=True)
    def test_missing_environment_variables_returns_none(self):
        client = sc.get_supabase_client()
        self.assertIsNone(client)
        success, msg = sc.test_supabase_connection()
        self.assertFalse(success)
        self.assertIn("Configuration Missing", msg)

    @patch('supabase.create_client')
    @patch.dict(os.environ, {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_KEY': 'testkey123'})
    def test_client_initialization_success(self, mock_create_client):
        mock_instance = MagicMock()
        mock_create_client.return_value = mock_instance

        client = sc.get_supabase_client()
        self.assertIsNotNone(client)
        mock_create_client.assert_called_once_with('https://example.supabase.co', 'testkey123')

    @patch('utils.supabase_client.get_supabase_client')
    def test_connection_success_mock(self, mock_get_client):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_limit = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.limit.return_value = mock_limit
        mock_limit.execute.return_value = MagicMock(data=[{'id': 1}])

        mock_get_client.return_value = mock_client

        success, msg = sc.test_supabase_connection()
        self.assertTrue(success)
        self.assertEqual(msg, "Supabase: Connected")

    @patch('utils.supabase_client.get_supabase_client')
    def test_connection_failure_mock(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("Network timeout")
        mock_get_client.return_value = mock_client

        success, msg = sc.test_supabase_connection()
        self.assertFalse(success)
        self.assertIn("Network timeout", msg)

    @patch.dict(os.environ, {'SUPABASE_URL': '', 'SUPABASE_KEY': ''})
    def test_app_startup_without_supabase_config(self):
        response = self.client.get('/health/supabase')
        self.assertEqual(response.status_code, 503)
        data = response.get_json()
        self.assertEqual(data['supabase'], 'Disconnected')

    @patch('utils.supabase_client.test_supabase_connection')
    def test_app_health_check_route_connected(self, mock_test_conn):
        mock_test_conn.return_value = (True, "Supabase: Connected")
        response = self.client.get('/health/supabase')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['supabase'], 'Connected')

    def test_existing_sqlite_dashboard_remains_functional(self):
        # Verify existing SQLite functionality is completely unaffected
        response = self.client.post('/login', data={
            'username': 'scrummaster',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Dashboard", html)


if __name__ == '__main__':
    unittest.main()
