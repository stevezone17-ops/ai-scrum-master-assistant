"""
tests/test_migration.py
========================
Unit and Integration Tests for SQLite-to-Supabase Data Migration.
"""

import unittest
import sqlite3
import os
from unittest.mock import patch, MagicMock
import scripts.migrate_sqlite_to_supabase as mig

class TestMigrationScript(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database populated with sample test data for all tables
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        tables = [
            'users', 'projects', 'team_members', 'sprints',
            'user_stories', 'tasks', 'bugs', 'standup_updates'
        ]
        for t in tables:
            cursor.execute(f"CREATE TABLE {t} (id INTEGER PRIMARY KEY, title TEXT, created_at TEXT)")

        cursor.execute("INSERT INTO users (id, title) VALUES (1, 'dev1')")
        cursor.execute("INSERT INTO tasks (id, title) VALUES (10, 'Task 10')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_transform_record(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = 10")
        raw_task = cursor.fetchone()

        transformed = mig.transform_record('tasks', raw_task)
        self.assertEqual(transformed['id'], 10)
        self.assertEqual(transformed['title'], 'Task 10')

    def test_migration_order_integrity(self):
        expected_order = [
            'users',
            'projects',
            'team_members',
            'sprints',
            'user_stories',
            'tasks',
            'bugs',
            'standup_updates'
        ]
        self.assertEqual(mig.MIGRATION_ORDER, expected_order)

    def test_migrate_table_dry_run(self):
        res = mig.migrate_table(self.conn, None, 'users', dry_run=True)
        self.assertEqual(res['sqlite_count'], 1)
        self.assertEqual(res['migrated'], 1)
        self.assertEqual(res['skipped'], 0)
        self.assertEqual(len(res['errors']), 0)

    @patch('utils.supabase_client.get_supabase_client')
    def test_migrate_table_live_upsert_mock(self, mock_get_client):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_upsert = MagicMock()
        mock_execute = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = mock_execute

        res = mig.migrate_table(self.conn, mock_client, 'users', dry_run=False)
        self.assertEqual(res['sqlite_count'], 1)
        self.assertEqual(res['migrated'], 1)
        self.assertEqual(res['skipped'], 0)
        mock_table.upsert.assert_called_once()

    @patch('os.path.exists', return_value=True)
    @patch('sqlite3.connect')
    def test_run_migration_dry_run_full(self, mock_connect, mock_exists):
        mock_connect.return_value = self.conn

        # Execute full dry-run controller
        success = mig.run_migration(dry_run=True)
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
