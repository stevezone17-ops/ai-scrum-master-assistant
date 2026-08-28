"""
tests/test_recommendations.py
==============================
Step 11 & 12B: Test suite for ai/recommendations.py

Covers:
  - Overdue task recommendation
  - Low completion recommendation
  - Low days remaining recommendation
  - High workload recommendation
  - High actual-vs-estimated hours recommendation
  - High bug count recommendation
  - High risk recommendation
  - Medium risk recommendation
  - Low risk recommendation
  - No-issue state
  - Recommendation priority ordering
  - Maximum 5 recommendations limit
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.recommendations import generate_recommendations_from_features


class TestAIRecommendations(unittest.TestCase):

    def setUp(self):
        """Baseline features representing a normal, issue-free sprint."""
        self.base_features = {
            'total_tasks': 10,
            'completed_tasks': 8,
            'pending_tasks': 2,
            'overdue_tasks': 0,
            'total_story_points': 30,
            'completed_story_points': 25,
            'developer_count': 3,
            'estimated_hours': 40.0,
            'actual_hours': 35.0,
            'days_allocated': 14,
            'days_remaining': 7,
            'previous_velocity': 25.0,
            'bug_count': 0,
            'high_priority_tasks': 1,
            'task_completion_rate': 0.8,
            'story_point_completion_rate': 0.83,
            'hours_variance': -5.0
        }

    def test_overdue_task_recommendation(self):
        """Verify overdue task recommendation is generated with HIGH priority."""
        features = self.base_features.copy()
        features['overdue_tasks'] = 2
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')

        titles = [r['title'] for r in recs]
        descriptions = [r['description'] for r in recs]

        self.assertTrue(any("overdue" in t.lower() or "overdue" in d.lower() for t, d in zip(titles, descriptions)))
        overdue_rec = next(r for r in recs if "overdue" in r['title'].lower() or "overdue" in r['description'].lower())
        self.assertEqual(overdue_rec['priority'], 'HIGH')

    def test_low_completion_recommendation(self):
        """Verify low task completion rate generates scope reduction recommendation."""
        features = self.base_features.copy()
        features['completed_tasks'] = 2
        features['pending_tasks'] = 8
        features['task_completion_rate'] = 0.2
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')

        descriptions = [r['description'] for r in recs]
        self.assertTrue(any("scope" in d.lower() or "completion" in d.lower() for d in descriptions))

    def test_low_days_remaining_recommendation(self):
        """Verify low days remaining with pending tasks generates deadline recommendation."""
        features = self.base_features.copy()
        features['days_remaining'] = 2
        features['pending_tasks'] = 5
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')

        descriptions = [r['description'] for r in recs]
        self.assertTrue(any("deadline" in d.lower() or "next sprint" in d.lower() for d in descriptions))
        deadline_rec = next(r for r in recs if "deadline" in r['description'].lower())
        self.assertEqual(deadline_rec['priority'], 'HIGH')

    def test_high_workload_recommendation(self):
        """Verify overloaded developer triggers workload redistribution recommendation."""
        features = self.base_features.copy()
        workloads = [
            {'username': 'Alice', 'workload_pct': 120.0, 'assigned_hours': 48.0},
            {'username': 'Bob', 'workload_pct': 50.0, 'assigned_hours': 20.0}
        ]
        recs = generate_recommendations_from_features(features, predicted_risk='LOW', workloads=workloads)

        titles = [r['title'] for r in recs]
        descriptions = [r['description'] for r in recs]

        self.assertTrue(any("Alice" in t for t in titles))
        self.assertTrue(any("redistributing" in d.lower() for d in descriptions))

    def test_high_actual_vs_estimated_hours_recommendation(self):
        """Verify actual_hours > estimated_hours triggers estimate review recommendation."""
        features = self.base_features.copy()
        features['estimated_hours'] = 30.0
        features['actual_hours'] = 45.0
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')

        descriptions = [r['description'] for r in recs]
        self.assertTrue(any("longer than estimated" in d.lower() for d in descriptions))

    def test_high_bug_count_recommendation(self):
        """Verify high bug count triggers bug prioritization recommendation."""
        features = self.base_features.copy()
        features['bug_count'] = 4
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')

        descriptions = [r['description'] for r in recs]
        self.assertTrue(any("critical bugs" in d.lower() or "bugs" in d.lower() for d in descriptions))

    def test_high_risk_recommendation(self):
        """Verify HIGH predicted risk triggers immediate sprint review recommendation."""
        features = self.base_features.copy()
        recs = generate_recommendations_from_features(features, predicted_risk='HIGH')

        descriptions = [r['description'] for r in recs]
        self.assertTrue(any("immediate sprint review" in d.lower() for d in descriptions))
        high_risk_rec = next(r for r in recs if "immediate sprint review" in r['description'].lower())
        self.assertEqual(high_risk_rec['priority'], 'HIGH')

    def test_medium_risk_recommendation(self):
        """Verify MEDIUM predicted risk triggers progress monitoring recommendation."""
        features = self.base_features.copy()
        recs = generate_recommendations_from_features(features, predicted_risk='MEDIUM')

        descriptions = [r['description'] for r in recs]
        self.assertTrue(any("closely" in d.lower() or "medium sprint risk" in d.lower() for d in descriptions))

    def test_low_risk_recommendation(self):
        """Verify LOW predicted risk returns positive progress recommendation."""
        features = self.base_features.copy()
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')

        descriptions = [r['description'] for r in recs]
        self.assertTrue(any("progressing well" in d.lower() for d in descriptions))
        low_rec = next(r for r in recs if "progressing well" in r['description'].lower())
        self.assertEqual(low_rec['priority'], 'LOW')

    def test_no_issue_state(self):
        """Verify baseline healthy sprint produces no critical warnings or empty recommendation list logic."""
        features = self.base_features.copy()
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')
        # LOW risk recommendation is returned, but no HIGH priority issues exist
        high_prio_recs = [r for r in recs if r['priority'] == 'HIGH']
        self.assertEqual(len(high_prio_recs), 0)

    def test_recommendation_priority_ordering(self):
        """Verify recommendations are sorted with HIGH priority first, then MEDIUM, then LOW."""
        features = self.base_features.copy()
        features['overdue_tasks'] = 3  # HIGH
        features['bug_count'] = 4       # MEDIUM
        features['actual_hours'] = 50   # MEDIUM
        features['estimated_hours'] = 30
        recs = generate_recommendations_from_features(features, predicted_risk='LOW')

        priorities = [r['priority'] for r in recs]
        priority_map = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        order_indices = [priority_map[p] for p in priorities]
        self.assertEqual(order_indices, sorted(order_indices))

    def test_maximum_5_recommendations(self):
        """Verify that at most 5 recommendations are returned even when many triggers occur."""
        features = self.base_features.copy()
        features['overdue_tasks'] = 5
        features['days_remaining'] = 1
        features['pending_tasks'] = 10
        features['estimated_hours'] = 20.0
        features['actual_hours'] = 50.0
        features['task_completion_rate'] = 0.1
        features['bug_count'] = 6
        workloads = [
            {'username': 'Dev1', 'workload_pct': 150.0, 'assigned_hours': 60.0},
            {'username': 'Dev2', 'workload_pct': 140.0, 'assigned_hours': 56.0}
        ]

        recs = generate_recommendations_from_features(features, predicted_risk='HIGH', workloads=workloads)
        self.assertLessEqual(len(recs), 5)


if __name__ == '__main__':
    unittest.main()
