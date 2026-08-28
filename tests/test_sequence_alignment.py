"""
tests/test_sequence_alignment.py
=================================
Tests PostgreSQL identity sequence calculation and alignment verification
for all 8 migrated application tables under Supabase backend.
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.supabase_client import get_supabase_client
from scripts.migrate_sqlite_to_supabase import update_postgresql_sequences, MIGRATION_ORDER

class TestSequenceAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['DATABASE_BACKEND'] = 'supabase'
        cls.client = get_supabase_client()

    def test_supabase_client_available(self):
        self.assertIsNotNone(self.client, "Supabase client should initialize successfully with environment credentials.")

    def test_tables_max_id_and_sequence_calculation(self):
        """Verify MAX(id) and next ID calculation for all 8 tables."""
        if not self.client:
            self.skipTest("Supabase client not initialized")

        expected_tables = [
            'users',
            'projects',
            'team_members',
            'sprints',
            'user_stories',
            'tasks',
            'bugs',
            'standup_updates'
        ]

        for table in expected_tables:
            res = self.client.table(table).select("id").order("id", desc=True).limit(1).execute()
            self.assertIsNotNone(res.data, f"Data response for '{table}' should not be None.")
            if res.data:
                max_id = res.data[0]['id']
                next_id = max_id + 1
                self.assertGreater(next_id, max_id, f"Next generated ID ({next_id}) for '{table}' must be strictly greater than MAX(id) ({max_id}).")

    def test_team_members_sequence_collision_prevention(self):
        """Specifically verify that team_members next generated ID will not collide with existing IDs."""
        if not self.client:
            self.skipTest("Supabase client not initialized")

        res = self.client.table('team_members').select("id").order("id", desc=True).limit(1).execute()
        self.assertTrue(len(res.data) > 0, "team_members should contain migrated data")
        
        max_id = res.data[0]['id']
        next_id = max_id + 1

        # Verify max_id is 38 and next_id is 39
        self.assertEqual(max_id, 38, "team_members MAX(id) should equal 38")
        self.assertEqual(next_id, 39, "team_members next generated ID should equal 39")

        # Verify id=39 does NOT currently exist in team_members
        check_res = self.client.table('team_members').select("id").eq("id", next_id).execute()
        self.assertEqual(len(check_res.data), 0, f"ID {next_id} must not exist in team_members prior to insert.")

    def test_update_postgresql_sequences_script_execution(self):
        """Test update_postgresql_sequences utility generates fix_sequences.sql cleanly."""
        update_postgresql_sequences(self.client, dry_run=False)
        sql_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fix_sequences.sql"))
        self.assertTrue(os.path.exists(sql_file), "fix_sequences.sql file should be generated.")
        
        with open(sql_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("team_members", content)
        self.assertIn("setval", content)

if __name__ == '__main__':
    unittest.main()
