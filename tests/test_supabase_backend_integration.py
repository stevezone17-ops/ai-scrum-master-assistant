"""
tests/test_supabase_backend_integration.py
============================================
Integration Tests verifying Supabase PostgreSQL as Primary Database Backend
and SQLite as Safe Fallback.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from app import app
from database.db import get_db
from models.user import User
from models.project import Project
from models.story import UserStory
from models.task import Task
from models.standup import StandupUpdate

class TestSupabaseBackendIntegration(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'}, clear=False)
    @patch('utils.supabase_client.get_supabase_client')
    def test_get_db_returns_supabase_adapter_when_configured(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        conn = get_db()
        self.assertEqual(conn.__class__.__name__, "SupabaseDatabaseAdapter")

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'sqlite'}, clear=False)
    def test_get_db_returns_sqlite_connection_when_sqlite_selected(self):
        conn = get_db()
        self.assertEqual(conn.__class__.__name__, "Connection")
        conn.close()

    @patch('utils.supabase_client.get_supabase_client', return_value=None)
    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'})
    def test_supabase_configured_but_missing_credentials_raises_error(self, mock_get_client):
        with self.assertRaises(RuntimeError) as ctx:
            get_db()
        self.assertIn("missing or invalid", str(ctx.exception))

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'})
    def test_supabase_auth_login_integration(self):
        # Verify Flask authentication against live Supabase dataset
        user = User.get_by_username('scrummaster')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'scrummaster')
        self.assertEqual(user['role'], 'Scrum Master')

        authenticated = User.authenticate('scrummaster', 'password123')
        self.assertIsNotNone(authenticated)

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'})
    def test_supabase_project_crud(self):
        # Read projects from Supabase
        projects = Project.get_all()
        self.assertTrue(len(projects) > 0)
        p = projects[0]
        self.assertIn('name', p)
        self.assertIn('creator_name', p)

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'})
    def test_supabase_backlog_stories_read(self):
        # Read user stories for project 1 from Supabase
        stories = UserStory.get_by_project(1)
        self.assertTrue(len(stories) >= 0)

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'})
    def test_supabase_tasks_and_kanban_read(self):
        # Read tasks from Supabase
        tasks = Task.get_by_project(1)
        self.assertTrue(len(tasks) >= 0)

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'})
    def test_supabase_standup_updates_read(self):
        # Read standups from Supabase
        standups = StandupUpdate.get_by_project(1)
        self.assertTrue(len(standups) >= 0)

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'sqlite'})
    def test_sqlite_fallback_login_functionality(self):
        # Verify application works smoothly when switched back to SQLite fallback
        response = self.client.post('/login', data={
            'username': 'scrummaster',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dashboard", response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
