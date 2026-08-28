"""
tests/test_data_preparation.py
===============================
Step 11A: Test suite for ai/data_preparation.py

Tests cover:
  - Data extraction from SQLite
  - Feature calculations (rates, variance, dates)
  - Missing-value / division-by-zero handling
  - Risk label generation (classify_risk_label)
  - DataFrame creation (extract_sprint_dataset)
  - Synthetic dataset generator
  - X/y preparation (prepare_for_ml)
  - Validation report (validate_dataset)
  - Existing application health (imports, dashboard route)
"""

import unittest
import pandas as pd
import numpy as np

# Make sure the app context can resolve models
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.data_preparation import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    classify_risk_label,
    extract_sprint_dataset,
    generate_synthetic_dataset,
    get_combined_dataset,
    prepare_for_ml,
    validate_dataset,
)


# ---------------------------------------------------------------------------
# Helper: build a minimal row dict for classify_risk_label tests
# ---------------------------------------------------------------------------
def _row(
    task_completion_rate=0.8,
    story_point_completion_rate=0.8,
    overdue_tasks=0,
    total_tasks=10,
    days_remaining=5,
    days_allocated=14,
    hours_variance=0.0,
    estimated_hours=40.0,
):
    return {
        'task_completion_rate':        task_completion_rate,
        'story_point_completion_rate': story_point_completion_rate,
        'overdue_tasks':               overdue_tasks,
        'total_tasks':                 total_tasks,
        'days_remaining':              days_remaining,
        'days_allocated':              days_allocated,
        'hours_variance':              hours_variance,
        'estimated_hours':             estimated_hours,
    }


# ===========================================================================
class TestRiskLabelClassification(unittest.TestCase):
    """Tests for classify_risk_label() — the standalone rule engine."""

    def test_low_risk_healthy_sprint(self):
        label = classify_risk_label(pd.Series(_row(
            task_completion_rate=0.90,
            story_point_completion_rate=0.85,
            overdue_tasks=0,
            days_remaining=6,
            days_allocated=14,
        )))
        self.assertEqual(label, 'LOW')

    def test_high_risk_very_behind_no_time(self):
        label = classify_risk_label(pd.Series(_row(
            task_completion_rate=0.10,
            story_point_completion_rate=0.05,
            overdue_tasks=1,
            total_tasks=10,
            days_remaining=1,
            days_allocated=14,
        )))
        self.assertEqual(label, 'HIGH')

    def test_high_risk_massive_overdue(self):
        label = classify_risk_label(pd.Series(_row(
            task_completion_rate=0.50,
            overdue_tasks=5,
            total_tasks=10,   # 50% overdue
            days_remaining=3,
            days_allocated=14,
        )))
        self.assertEqual(label, 'HIGH')

    def test_medium_risk_moderate_completion_some_overdue(self):
        label = classify_risk_label(pd.Series(_row(
            task_completion_rate=0.40,
            story_point_completion_rate=0.35,
            overdue_tasks=2,
            total_tasks=10,
            days_remaining=5,
            days_allocated=14,
        )))
        self.assertEqual(label, 'MEDIUM')

    def test_zero_tasks_returns_low(self):
        """Zero-division guard: total_tasks=0 should not crash and → LOW."""
        label = classify_risk_label(pd.Series(_row(
            task_completion_rate=0.0,
            total_tasks=0,
            overdue_tasks=0,
        )))
        self.assertEqual(label, 'LOW')

    def test_all_labels_are_valid(self):
        valid = {'LOW', 'MEDIUM', 'HIGH'}
        cases = [
            _row(task_completion_rate=0.95, overdue_tasks=0),
            _row(task_completion_rate=0.45, overdue_tasks=1, days_remaining=3, days_allocated=14),
            _row(task_completion_rate=0.10, overdue_tasks=5, total_tasks=10, days_remaining=1, days_allocated=14),
        ]
        for c in cases:
            label = classify_risk_label(pd.Series(c))
            self.assertIn(label, valid, f"Unexpected label '{label}' for case {c}")


# ===========================================================================
class TestSyntheticDatasetGenerator(unittest.TestCase):

    def setUp(self):
        self.df = generate_synthetic_dataset(n_samples=100, random_seed=7)

    def test_row_count(self):
        self.assertEqual(len(self.df), 100)

    def test_all_feature_columns_present(self):
        for col in FEATURE_COLUMNS:
            self.assertIn(col, self.df.columns, f"Missing feature column: {col}")

    def test_target_column_present(self):
        self.assertIn(TARGET_COLUMN, self.df.columns)

    def test_target_labels_are_valid(self):
        valid = {'LOW', 'MEDIUM', 'HIGH'}
        actual = set(self.df[TARGET_COLUMN].unique())
        self.assertTrue(actual.issubset(valid), f"Unexpected labels: {actual - valid}")

    def test_all_three_labels_appear(self):
        """With 100 samples, all three risk levels should appear."""
        labels = set(self.df[TARGET_COLUMN].unique())
        self.assertEqual(labels, {'LOW', 'MEDIUM', 'HIGH'})

    def test_no_nulls_in_features(self):
        null_counts = self.df[FEATURE_COLUMNS].isnull().sum()
        self.assertTrue(
            (null_counts == 0).all(),
            f"Null values found: {null_counts[null_counts > 0].to_dict()}"
        )

    def test_rates_in_range(self):
        self.assertTrue((self.df['task_completion_rate'] >= 0).all())
        self.assertTrue((self.df['task_completion_rate'] <= 1).all())
        self.assertTrue((self.df['story_point_completion_rate'] >= 0).all())
        self.assertTrue((self.df['story_point_completion_rate'] <= 1).all())

    def test_no_negative_hours(self):
        self.assertTrue((self.df['estimated_hours'] >= 0).all())
        self.assertTrue((self.df['actual_hours'] >= 0).all())

    def test_deterministic_with_same_seed(self):
        df1 = generate_synthetic_dataset(n_samples=50, random_seed=42)
        df2 = generate_synthetic_dataset(n_samples=50, random_seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seed_gives_different_data(self):
        df1 = generate_synthetic_dataset(n_samples=50, random_seed=1)
        df2 = generate_synthetic_dataset(n_samples=50, random_seed=2)
        self.assertFalse(df1['task_completion_rate'].equals(df2['task_completion_rate']))


# ===========================================================================
class TestRealDataExtraction(unittest.TestCase):

    def setUp(self):
        self.df = extract_sprint_dataset()

    def test_returns_dataframe(self):
        self.assertIsInstance(self.df, pd.DataFrame)

    def test_feature_columns_present(self):
        for col in FEATURE_COLUMNS:
            self.assertIn(col, self.df.columns, f"Missing: {col}")

    def test_target_column_present(self):
        self.assertIn(TARGET_COLUMN, self.df.columns)

    def test_no_null_in_numeric_features(self):
        null_counts = self.df[FEATURE_COLUMNS].isnull().sum()
        self.assertTrue(
            (null_counts == 0).all(),
            f"Null values found: {null_counts[null_counts > 0].to_dict()}"
        )

    def test_completion_rates_in_range(self):
        if len(self.df) == 0:
            return
        self.assertTrue((self.df['task_completion_rate'] >= 0).all())
        self.assertTrue((self.df['task_completion_rate'] <= 1).all())
        self.assertTrue((self.df['story_point_completion_rate'] >= 0).all())
        self.assertTrue((self.df['story_point_completion_rate'] <= 1).all())

    def test_no_negative_hours_after_cleaning(self):
        if len(self.df) == 0:
            return
        self.assertTrue((self.df['estimated_hours'] >= 0).all())
        self.assertTrue((self.df['actual_hours'] >= 0).all())

    def test_days_allocated_positive(self):
        if len(self.df) == 0:
            return
        self.assertTrue((self.df['days_allocated'] >= 1).all())

    def test_risk_labels_valid(self):
        if len(self.df) == 0:
            return
        valid = {'LOW', 'MEDIUM', 'HIGH'}
        actual = set(self.df[TARGET_COLUMN].unique())
        self.assertTrue(actual.issubset(valid))


# ===========================================================================
class TestFeatureCalculations(unittest.TestCase):

    def test_task_completion_rate_calculation(self):
        df = generate_synthetic_dataset(n_samples=50, random_seed=99)
        # task_completion_rate == completed_tasks / total_tasks  (where total > 0)
        mask = df['total_tasks'] > 0
        expected = (df.loc[mask, 'completed_tasks'] / df.loc[mask, 'total_tasks']).round(4)
        actual   = df.loc[mask, 'task_completion_rate'].round(4)
        pd.testing.assert_series_equal(expected.reset_index(drop=True),
                                       actual.reset_index(drop=True),
                                       check_names=False)

    def test_hours_variance_calculation(self):
        df = generate_synthetic_dataset(n_samples=50, random_seed=99)
        expected = (df['actual_hours'] - df['estimated_hours']).round(2)
        actual   = df['hours_variance'].round(2)
        pd.testing.assert_series_equal(expected.reset_index(drop=True),
                                       actual.reset_index(drop=True),
                                       check_names=False)

    def test_sp_completion_rate_zero_when_no_points(self):
        """story_point_completion_rate must be 0 when total_story_points == 0."""
        df = generate_synthetic_dataset(n_samples=200, random_seed=5)
        zero_sp = df[df['total_story_points'] == 0]
        if not zero_sp.empty:
            self.assertTrue((zero_sp['story_point_completion_rate'] == 0.0).all())


# ===========================================================================
class TestMissingValueHandling(unittest.TestCase):

    def test_nulls_filled_in_real_data(self):
        df = extract_sprint_dataset()
        null_counts = df[FEATURE_COLUMNS].isnull().sum()
        total_nulls = null_counts.sum()
        self.assertEqual(total_nulls, 0, f"Unexpected nulls: {null_counts[null_counts>0].to_dict()}")

    def test_nulls_filled_in_synthetic_data(self):
        df = generate_synthetic_dataset(n_samples=100)
        null_counts = df[FEATURE_COLUMNS].isnull().sum()
        total_nulls = null_counts.sum()
        self.assertEqual(total_nulls, 0)


# ===========================================================================
class TestCombinedDataset(unittest.TestCase):

    def test_returns_at_least_min_records(self):
        min_records = 10
        df = get_combined_dataset(min_real_records=min_records)
        self.assertGreaterEqual(len(df), min_records)

    def test_all_feature_columns_present(self):
        df = get_combined_dataset()
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df.columns)

    def test_target_column_present(self):
        df = get_combined_dataset()
        self.assertIn(TARGET_COLUMN, df.columns)


# ===========================================================================
class TestMLPreparation(unittest.TestCase):

    def setUp(self):
        self.df = get_combined_dataset()
        self.X, self.y = prepare_for_ml(self.df)

    def test_X_is_dataframe(self):
        self.assertIsInstance(self.X, pd.DataFrame)

    def test_y_is_series(self):
        self.assertIsInstance(self.y, pd.Series)

    def test_X_has_feature_columns(self):
        for col in FEATURE_COLUMNS:
            self.assertIn(col, self.X.columns, f"Feature missing from X: {col}")

    def test_X_and_y_same_length(self):
        self.assertEqual(len(self.X), len(self.y))

    def test_X_all_numeric(self):
        for col in self.X.columns:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(self.X[col]),
                f"Non-numeric column in X: {col}"
            )

    def test_y_contains_valid_labels(self):
        valid = {'LOW', 'MEDIUM', 'HIGH'}
        actual = set(self.y.unique())
        self.assertTrue(actual.issubset(valid))

    def test_no_nans_in_X(self):
        self.assertFalse(self.X.isnull().any().any(), "NaN values found in X")

    def test_prepare_for_ml_without_args_works(self):
        X, y = prepare_for_ml()
        self.assertGreater(len(X), 0)
        self.assertEqual(len(X), len(y))


# ===========================================================================
class TestValidationReport(unittest.TestCase):

    def test_returns_dict(self):
        report = validate_dataset(generate_synthetic_dataset(n_samples=60))
        self.assertIsInstance(report, dict)

    def test_report_keys_present(self):
        report = validate_dataset(generate_synthetic_dataset(n_samples=60))
        for key in ['n_records', 'n_features', 'missing_values', 'risk_distribution', 'statistics']:
            self.assertIn(key, report)

    def test_n_records_correct(self):
        df = generate_synthetic_dataset(n_samples=75)
        report = validate_dataset(df)
        self.assertEqual(report['n_records'], 75)

    def test_n_features_correct(self):
        df = generate_synthetic_dataset(n_samples=50)
        report = validate_dataset(df)
        self.assertEqual(report['n_features'], len(FEATURE_COLUMNS))

    def test_no_missing_in_synthetic(self):
        df = generate_synthetic_dataset(n_samples=50)
        report = validate_dataset(df)
        self.assertEqual(report['missing_values'], {})


# ===========================================================================
class TestExistingAppHealth(unittest.TestCase):
    """Smoke-test the existing Flask application is still functional."""

    def setUp(self):
        from app import app
        self.client = app.test_client()
        self.client.testing = True

    def _login(self, user_id, role, username):
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role']    = role
            sess['username'] = username

    def test_dashboard_scrum_master_200(self):
        self._login(1, 'Scrum Master', 'scrummaster')
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)

    def test_dashboard_developer_200(self):
        self._login(2, 'Developer', 'developer1')
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)

    def test_kanban_board_200(self):
        self._login(1, 'Scrum Master', 'scrummaster')
        res = self.client.get('/projects/1/kanban')
        self.assertEqual(res.status_code, 200)

    def test_task_status_api_still_works(self):
        self._login(1, 'Scrum Master', 'scrummaster')
        res = self.client.post('/tasks/1/status', json={'status': 'In Progress'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])


# ===========================================================================
if __name__ == '__main__':
    unittest.main(verbosity=2)
