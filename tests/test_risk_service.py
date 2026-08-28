"""
tests/test_risk_service.py
===========================
Step 12A: Test suite for ai/risk_service.py and Dashboard Integration

Covers:
  - Model loading via risk_service
  - Active sprint feature extraction
  - AI risk prediction output format & probability calculations
  - Graceful handling when project has no active sprint
  - Graceful handling when model file is missing or corrupted
  - Dynamic explanation generation based on real metrics
  - Risk factor formatting and impact assignments
  - Dashboard route integration for Scrum Master, Product Owner, and Developer
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.db import get_db
from ai.risk_service import (
    get_sprint_features_for_active_sprint,
    get_ai_sprint_risk_assessment,
    _generate_explanation,
    _format_risk_factors,
)
from ai.risk_model import FEATURE_COLUMNS, LABEL_ORDER


class TestRiskService(unittest.TestCase):

    def setUp(self):
        self.app_client = app.test_client()
        self.app_client.testing = True

    def _login(self, user_id, role, username):
        with self.app_client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = role
            sess['username'] = username

    def test_get_sprint_features_active_sprint(self):
        """Test feature extraction for project 1 (has active sprint)."""
        active_sprint, features = get_sprint_features_for_active_sprint(1)
        if active_sprint:
            self.assertIsInstance(active_sprint, dict)
            self.assertIsInstance(features, dict)
            for col in FEATURE_COLUMNS:
                self.assertIn(col, features, f"Missing feature: {col}")

    def test_ai_sprint_risk_assessment_active_sprint(self):
        """Test full assessment output for project with active sprint."""
        result = get_ai_sprint_risk_assessment(1)
        self.assertIsInstance(result, dict)
        self.assertIn('has_sprint', result)
        if result['has_sprint']:
            self.assertFalse(result['error'])
            self.assertIn(result['risk_level'], LABEL_ORDER)
            self.assertGreater(result['confidence_pct'], 0)
            self.assertLessEqual(result['confidence_pct'], 100)
            self.assertIn('probabilities', result)
            for label in LABEL_ORDER:
                self.assertIn(label, result['probabilities'])
            self.assertIn('badge_class', result)
            self.assertIsNotNone(result['explanation'])
            self.assertIsInstance(result['risk_factors'], list)

    def test_ai_sprint_risk_assessment_no_active_sprint(self):
        """Test graceful response for non-existent project or project without active sprint."""
        result = get_ai_sprint_risk_assessment(99999)
        self.assertIsInstance(result, dict)
        self.assertFalse(result['has_sprint'])
        self.assertFalse(result['error'])
        self.assertIn("No active sprint", result['message'])
        self.assertIsNone(result['risk_level'])

    @patch('ai.risk_service.get_loaded_model')
    def test_ai_sprint_risk_assessment_missing_model(self, mock_load):
        """Test error handling when model load fails."""
        mock_load.side_effect = FileNotFoundError("Model file missing")
        result = get_ai_sprint_risk_assessment(1)
        self.assertIsInstance(result, dict)
        self.assertTrue(result['has_sprint'])
        self.assertTrue(result['error'])
        self.assertEqual(result['message'], "AI risk analysis is currently unavailable.")
        self.assertIsNone(result['risk_level'])

    def test_generate_explanation_high_risk(self):
        features = {'overdue_tasks': 4, 'days_remaining': 2, 'task_completion_rate': 0.2, 'story_point_completion_rate': 0.15}
        exp = _generate_explanation('HIGH', features)
        self.assertIn("High risk detected", exp)
        self.assertIn("4 task(s) are overdue", exp)

    def test_generate_explanation_low_risk(self):
        features = {'overdue_tasks': 0, 'days_remaining': 7, 'task_completion_rate': 0.85, 'story_point_completion_rate': 0.90}
        exp = _generate_explanation('LOW', features)
        self.assertIn("Low risk detected", exp)

    def test_format_risk_factors(self):
        features = {
            'overdue_tasks': 3,
            'days_remaining': 2,
            'task_completion_rate': 0.25,
            'story_point_completion_rate': 0.3,
            'hours_variance': 15.0,
            'bug_count': 2,
            'high_priority_tasks': 4,
            'pending_tasks': 8,
            'developer_count': 3
        }
        importance = [
            {'feature': 'overdue_tasks', 'importance': 0.2},
            {'feature': 'days_remaining', 'importance': 0.15},
            {'feature': 'task_completion_rate', 'importance': 0.12},
            {'feature': 'hours_variance', 'importance': 0.10},
        ]
        factors = _format_risk_factors(features, importance)
        self.assertIsInstance(factors, list)
        self.assertGreater(len(factors), 0)
        self.assertIn('name', factors[0])
        self.assertIn('value', factors[0])
        self.assertIn('severity', factors[0])

    def test_dashboard_scrum_master_renders_ai_card(self):
        self._login(1, 'Scrum Master', 'scrummaster')
        response = self.app_client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AI Sprint Risk Assessment", html)

    def test_dashboard_product_owner_renders_ai_card(self):
        self._login(3, 'Product Owner', 'productowner')
        response = self.app_client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AI Sprint Risk Assessment", html)

    def test_dashboard_developer_renders_ai_card(self):
        self._login(2, 'Developer', 'developer1')
        response = self.app_client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AI Sprint Risk Assessment", html)


if __name__ == '__main__':
    unittest.main(verbosity=2)
