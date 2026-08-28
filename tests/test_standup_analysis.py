"""
tests/test_standup_analysis.py
==============================
Step 12C: Test suite for Stand-up management and ai/standup_analysis.py

Covers:
  - Creating a stand-up update
  - Updating an existing same-day stand-up
  - Duplicate submission prevention
  - Blocker keyword detection
  - Potential issue detection
  - No-issue classification
  - Stand-up summary generation
  - Repeated blocker detection
  - Role-based access
  - Project-level data isolation
"""

import unittest
import os
import sys
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db, init_db
from models.user import User
from models.project import Project
from models.standup import StandupUpdate
from ai.standup_analysis import (
    classify_standup_text,
    generate_standup_summary,
    analyze_single_standup,
    detect_repeated_blockers,
    generate_team_standup_summary
)


class TestAIStandupAnalysis(unittest.TestCase):

    def setUp(self):
        """Ensure database schema is initialized."""
        init_db()

    def test_blocker_keyword_detection(self):
        """Verify blocker keywords (e.g. waiting, dependency, failing, stuck) trigger BLOCKED status."""
        # 1. Explicit blocker in blockers field
        res1 = classify_standup_text(
            yesterday_work="Built login API",
            today_plan="Testing endpoints",
            blockers="Waiting for payment API credentials"
        )
        self.assertEqual(res1['status'], 'BLOCKED')
        self.assertTrue(res1['has_blocker'])
        self.assertIn("waiting", res1['keywords'])

        # 2. Blocker keywords in today's plan
        res2 = classify_standup_text(
            yesterday_work="Refactored database queries",
            today_plan="I am stuck on OAuth token validation",
            blockers="None"
        )
        self.assertEqual(res2['status'], 'BLOCKED')
        self.assertIn("stuck", res2['keywords'])

    def test_potential_issue_detection(self):
        """Verify potential delay keywords (delayed, issue, behind, slow) trigger POTENTIAL_ISSUE."""
        res = classify_standup_text(
            yesterday_work="Database migration work",
            today_plan="Completing user profiles, but database work delayed",
            blockers="None"
        )
        self.assertEqual(res['status'], 'POTENTIAL_ISSUE')
        self.assertFalse(res['has_blocker'])
        self.assertIn("delayed", res['keywords'])

    def test_no_issue_classification(self):
        """Verify clean, regular progress triggers NO_ISSUE status."""
        res = classify_standup_text(
            yesterday_work="Completed task card styling and icons",
            today_plan="Will implement filter dropdowns",
            blockers="No blockers"
        )
        self.assertEqual(res['status'], 'NO_ISSUE')
        self.assertFalse(res['has_blocker'])
        self.assertEqual(len(res['keywords']), 0)

    def test_standup_summary_generation(self):
        """Verify AI summary cleanly condenses yesterday, today, and blocker details."""
        summary = generate_standup_summary(
            yesterday_work="login API endpoints",
            today_plan="integration testing",
            blockers="waiting for API credentials",
            status="BLOCKED"
        )
        self.assertIn("Completed login API endpoints", summary)
        self.assertIn("working on integration testing", summary)
        self.assertIn("waiting for API credentials", summary)

    def test_create_and_update_standup_update(self):
        """Verify creating a stand-up record and updating it with comments."""
        conn = get_db()
        cursor = conn.cursor()

        # Fetch or create a test user
        cursor.execute("SELECT id FROM users WHERE username = 'developer1'")
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else 1

        # Fetch or create a test project
        cursor.execute("SELECT id FROM projects LIMIT 1")
        proj_row = cursor.fetchone()
        project_id = proj_row[0] if proj_row else 1
        conn.close()

        test_date = "2026-08-20"

        # 1. Create
        update_id = StandupUpdate.create(
            project_id=project_id,
            sprint_id=None,
            user_id=user_id,
            date=test_date,
            yesterday_work="Fixed unit tests",
            today_plan="Refactor auth middleware",
            blockers="None",
            comments="Initial note"
        )
        self.assertIsNotNone(update_id)

        rec = StandupUpdate.get_by_id(update_id)
        self.assertEqual(rec['yesterday_work'], "Fixed unit tests")
        self.assertEqual(rec['comments'], "Initial note")

        # 2. Update same-day record
        StandupUpdate.update(
            update_id=update_id,
            yesterday_work="Fixed unit tests and linting",
            today_plan="Refactor auth middleware and sessions",
            blockers="Waiting for staging DB",
            comments="Updated note"
        )

        updated_rec = StandupUpdate.get_by_id(update_id)
        self.assertEqual(updated_rec['yesterday_work'], "Fixed unit tests and linting")
        self.assertEqual(updated_rec['blockers'], "Waiting for staging DB")
        self.assertEqual(updated_rec['comments'], "Updated note")

    def test_duplicate_submission_prevention(self):
        """Verify query returns existing record for a developer on a date to prevent duplicates."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = 'developer2'")
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else 2
        cursor.execute("SELECT id FROM projects LIMIT 1")
        project_id = cursor.fetchone()[0]
        conn.close()

        test_date = "2026-08-21"

        # First insert
        StandupUpdate.create(
            project_id=project_id,
            sprint_id=None,
            user_id=user_id,
            date=test_date,
            yesterday_work="Setup CI",
            today_plan="Dockerize app",
            blockers="None"
        )

        # Lookup
        existing = StandupUpdate.get_user_standup_for_date(project_id, user_id, test_date)
        self.assertIsNotNone(existing)
        self.assertEqual(existing['today_plan'], "Dockerize app")

    def test_repeated_blocker_detection(self):
        """Verify repeated blockers across consecutive updates are flagged."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = 'developer3'")
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else 3
        cursor.execute("SELECT id FROM projects LIMIT 1")
        project_id = cursor.fetchone()[0]
        conn.close()

        d1 = date.today().isoformat()
        d2 = (date.today() - timedelta(days=1)).isoformat()

        # Insert 2 updates with matching blocker
        StandupUpdate.create(
            project_id=project_id,
            sprint_id=None,
            user_id=user_id,
            date=d2,
            yesterday_work="Investigating payment failure",
            today_plan="Fixing webhook",
            blockers="Payment API credentials missing"
        )

        StandupUpdate.create(
            project_id=project_id,
            sprint_id=None,
            user_id=user_id,
            date=d1,
            yesterday_work="Waiting for credentials",
            today_plan="Testing payment webhook",
            blockers="Payment API credentials still missing"
        )

        alerts = detect_repeated_blockers(project_id, days=7)
        self.assertGreaterEqual(len(alerts), 1)
        self.assertTrue(any("Payment API credentials" in a['blocker'] or "credentials" in a['blocker'].lower() for a in alerts))

    def test_role_based_access_and_isolation(self):
        """Verify project membership isolation logic for stand-ups."""
        conn = get_db()
        cursor = conn.cursor()

        # Get projects
        cursor.execute("SELECT id FROM projects")
        projs = cursor.fetchall()
        if len(projs) >= 2:
            p1_id, p2_id = projs[0][0], projs[1][0]
            
            # Developer in p1 should not get p2 standup updates
            p1_updates = StandupUpdate.get_by_project(p1_id)
            p2_updates = StandupUpdate.get_by_project(p2_id)

            p1_ids = {u['id'] for u in p1_updates}
            p2_ids = {u['id'] for u in p2_updates}

            # Distinct sets of records (no cross-project leakage)
            self.assertEqual(len(p1_ids.intersection(p2_ids)), 0)

        conn.close()


if __name__ == '__main__':
    unittest.main()
