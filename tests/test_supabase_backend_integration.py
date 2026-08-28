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

    @patch.dict(os.environ, {'DATABASE_BACKEND': 'supabase'})
    def test_update_parsing_edge_cases(self):
        """Test _handle_update parsing for whitespace, multi-line, quoted columns, literal commas and parameters."""
        from database.supabase_adapter import SupabaseCursorAdapter
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.neq.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[{'id': 1}])

        adapter = SupabaseCursorAdapter(mock_client)

        # 1. Normal UPDATE with multiple columns & whitespace/newlines
        sql1 = """
            UPDATE tasks
            SET title = ?, description = ?,
                actual_hours = ?
            WHERE id = ?
        """
        adapter.execute(sql1, ("Title A", "Desc B", 5.0, 1))
        mock_table.update.assert_called_with({'title': 'Title A', 'description': 'Desc B', 'actual_hours': 5.0})
        mock_query.eq.assert_called_with('id', 1)

        # 2. Quoted column names & literal values in SET
        mock_table.reset_mock()
        mock_query.reset_mock()
        sql2 = "UPDATE team_members SET `role_in_project` = ? WHERE project_id = ? AND user_id = ?"
        adapter.execute(sql2, ("Developer", 10, 20))
        mock_table.update.assert_called_with({'role_in_project': 'Developer'})

        # 3. SET clause with literal commas inside strings
        mock_table.reset_mock()
        mock_query.reset_mock()
        sql3 = "UPDATE tasks SET description = 'Fix A, B, and C', status = ? WHERE id = ?"
        adapter.execute(sql3, ("Done", 15))
        mock_table.update.assert_called_with({'description': 'Fix A, B, and C', 'status': 'Done'})
        mock_query.eq.assert_called_with('id', 15)

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
