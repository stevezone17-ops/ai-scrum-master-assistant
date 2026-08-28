"""
tests/test_risk_model.py
=========================
Step 11B: Test suite for ai/risk_model.py

Covers:
  - Model training
  - Model saving / loading
  - Prediction output format & values
  - Prediction probabilities
  - Feature importance
  - Invalid / edge-case input handling
  - Model info function
  - Cross-validation (if applicable)
  - Existing application health (dashboard, kanban, task API)
"""

import unittest
import os
import shutil
import tempfile
import json
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.data_preparation import FEATURE_COLUMNS, TARGET_COLUMN
from ai.risk_model import (
    train_model,
    save_model,
    load_model,
    predict_sprint_risk,
    get_model_info,
    train_and_save,
    LABEL_ORDER,
)


class _BaseModelTest(unittest.TestCase):
    """Shared fixture: train the model once and reuse across tests."""

    _training_result = None
    _temp_dir = None

    @classmethod
    def setUpClass(cls):
        cls._temp_dir = tempfile.mkdtemp(prefix='risk_model_test_')
        cls._model_path = os.path.join(cls._temp_dir, 'model.joblib')
        cls._meta_path  = os.path.join(cls._temp_dir, 'meta.json')
        cls._training_result = train_model(verbose=False)
        save_model(
            cls._training_result,
            model_path=cls._model_path,
            meta_path=cls._meta_path,
        )

    @classmethod
    def tearDownClass(cls):
        if cls._temp_dir and os.path.isdir(cls._temp_dir):
            shutil.rmtree(cls._temp_dir)


# ===========================================================================
class TestModelTraining(_BaseModelTest):

    def test_training_result_is_dict(self):
        self.assertIsInstance(self._training_result, dict)

    def test_result_contains_model(self):
        self.assertIn('model', self._training_result)

    def test_result_contains_scaler(self):
        self.assertIn('scaler', self._training_result)

    def test_result_contains_label_encoder(self):
        self.assertIn('label_encoder', self._training_result)

    def test_result_contains_evaluation(self):
        self.assertIn('evaluation', self._training_result)

    def test_result_contains_feature_importance(self):
        self.assertIn('feature_importance', self._training_result)

    def test_result_contains_model_info(self):
        self.assertIn('model_info', self._training_result)

    def test_model_is_random_forest(self):
        from sklearn.ensemble import RandomForestClassifier
        self.assertIsInstance(self._training_result['model'], RandomForestClassifier)

    def test_accuracy_is_reasonable(self):
        acc = self._training_result['evaluation']['accuracy']
        self.assertGreater(acc, 0.0)
        self.assertLessEqual(acc, 1.0)

    def test_precision_in_range(self):
        p = self._training_result['evaluation']['precision']
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)

    def test_recall_in_range(self):
        r = self._training_result['evaluation']['recall']
        self.assertGreaterEqual(r, 0.0)
        self.assertLessEqual(r, 1.0)

    def test_f1_in_range(self):
        f1 = self._training_result['evaluation']['f1_score']
        self.assertGreaterEqual(f1, 0.0)
        self.assertLessEqual(f1, 1.0)

    def test_confusion_matrix_shape(self):
        cm = self._training_result['evaluation']['confusion_matrix']
        self.assertIsInstance(cm, list)
        self.assertEqual(len(cm), 3)      # 3 classes
        for row in cm:
            self.assertEqual(len(row), 3)

    def test_classification_report_has_all_labels(self):
        report = self._training_result['evaluation']['classification_report']
        for label in LABEL_ORDER:
            self.assertIn(label, report)


# ===========================================================================
class TestModelSaving(_BaseModelTest):

    def test_model_file_exists(self):
        self.assertTrue(os.path.isfile(self._model_path))

    def test_meta_file_exists(self):
        self.assertTrue(os.path.isfile(self._meta_path))

    def test_model_file_not_empty(self):
        self.assertGreater(os.path.getsize(self._model_path), 100)

    def test_meta_is_valid_json(self):
        with open(self._meta_path) as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)
        self.assertIn('model_info', data)
        self.assertIn('evaluation', data)
        self.assertIn('feature_importance', data)


# ===========================================================================
class TestModelLoading(_BaseModelTest):

    def setUp(self):
        self.loaded = load_model(
            model_path=self._model_path,
            meta_path=self._meta_path,
        )

    def test_loaded_is_dict(self):
        self.assertIsInstance(self.loaded, dict)

    def test_loaded_contains_model(self):
        self.assertIn('model', self.loaded)

    def test_loaded_contains_scaler(self):
        self.assertIn('scaler', self.loaded)

    def test_loaded_contains_label_encoder(self):
        self.assertIn('label_encoder', self.loaded)

    def test_loaded_model_can_predict(self):
        """Smoke test: the loaded model produces a prediction."""
        dummy = np.zeros((1, len(FEATURE_COLUMNS)))
        scaled = self.loaded['scaler'].transform(dummy)
        pred = self.loaded['model'].predict(scaled)
        self.assertEqual(len(pred), 1)

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_model(model_path='/nonexistent/path/model.joblib')


# ===========================================================================
class TestPrediction(_BaseModelTest):

    def setUp(self):
        self.loaded = load_model(
            model_path=self._model_path,
            meta_path=self._meta_path,
        )

    def _make_features(self, **overrides):
        base = {col: 0.0 for col in FEATURE_COLUMNS}
        base.update({
            'total_tasks': 10,
            'completed_tasks': 8,
            'pending_tasks': 2,
            'overdue_tasks': 0,
            'total_story_points': 30,
            'completed_story_points': 25,
            'developer_count': 3,
            'estimated_hours': 80,
            'actual_hours': 70,
            'days_allocated': 14,
            'days_remaining': 5,
            'previous_velocity': 20,
            'bug_count': 1,
            'high_priority_tasks': 2,
            'task_completion_rate': 0.8,
            'story_point_completion_rate': 0.83,
            'hours_variance': -10,
        })
        base.update(overrides)
        return base

    def test_prediction_returns_dict(self):
        result = predict_sprint_risk(self._make_features(), self.loaded)
        self.assertIsInstance(result, dict)

    def test_prediction_has_risk_key(self):
        result = predict_sprint_risk(self._make_features(), self.loaded)
        self.assertIn('risk', result)

    def test_prediction_risk_is_valid_label(self):
        result = predict_sprint_risk(self._make_features(), self.loaded)
        self.assertIn(result['risk'], LABEL_ORDER)

    def test_prediction_has_probabilities(self):
        result = predict_sprint_risk(self._make_features(), self.loaded)
        self.assertIn('probabilities', result)

    def test_probabilities_sum_to_one(self):
        result = predict_sprint_risk(self._make_features(), self.loaded)
        prob_sum = sum(result['probabilities'].values())
        self.assertAlmostEqual(prob_sum, 1.0, places=2)

    def test_probabilities_contain_all_labels(self):
        result = predict_sprint_risk(self._make_features(), self.loaded)
        for label in LABEL_ORDER:
            self.assertIn(label, result['probabilities'])

    def test_prediction_has_confidence(self):
        result = predict_sprint_risk(self._make_features(), self.loaded)
        self.assertIn('confidence', result)
        self.assertGreater(result['confidence'], 0.0)
        self.assertLessEqual(result['confidence'], 1.0)

    def test_healthy_sprint_tends_low(self):
        features = self._make_features(
            task_completion_rate=0.95,
            story_point_completion_rate=0.90,
            overdue_tasks=0,
            days_remaining=7,
        )
        result = predict_sprint_risk(features, self.loaded)
        # Should be LOW or at worst MEDIUM (model is probabilistic)
        self.assertIn(result['risk'], ['LOW', 'MEDIUM'])

    def test_risky_sprint_tends_high(self):
        features = self._make_features(
            task_completion_rate=0.1,
            story_point_completion_rate=0.05,
            overdue_tasks=8,
            total_tasks=10,
            days_remaining=0,
            hours_variance=50,
        )
        result = predict_sprint_risk(features, self.loaded)
        self.assertIn(result['risk'], ['MEDIUM', 'HIGH'])


# ===========================================================================
class TestFeatureImportance(_BaseModelTest):

    def test_feature_importance_is_list(self):
        fi = self._training_result['feature_importance']
        self.assertIsInstance(fi, list)

    def test_feature_importance_count(self):
        fi = self._training_result['feature_importance']
        self.assertEqual(len(fi), len(FEATURE_COLUMNS))

    def test_importance_entries_have_keys(self):
        for entry in self._training_result['feature_importance']:
            self.assertIn('feature', entry)
            self.assertIn('importance', entry)

    def test_importance_values_non_negative(self):
        for entry in self._training_result['feature_importance']:
            self.assertGreaterEqual(entry['importance'], 0.0)

    def test_importance_sorted_descending(self):
        fi = self._training_result['feature_importance']
        values = [e['importance'] for e in fi]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_all_feature_names_present(self):
        fi_names = {e['feature'] for e in self._training_result['feature_importance']}
        expected = set(FEATURE_COLUMNS)
        self.assertEqual(fi_names, expected)


# ===========================================================================
class TestInvalidInput(_BaseModelTest):

    def setUp(self):
        self.loaded = load_model(
            model_path=self._model_path,
            meta_path=self._meta_path,
        )

    def test_empty_features_dict(self):
        """All features default to 0; should not crash."""
        result = predict_sprint_risk({}, self.loaded)
        self.assertIn(result['risk'], LABEL_ORDER)

    def test_partial_features(self):
        result = predict_sprint_risk({'total_tasks': 5, 'overdue_tasks': 3}, self.loaded)
        self.assertIn(result['risk'], LABEL_ORDER)

    def test_extra_keys_ignored(self):
        features = {col: 1.0 for col in FEATURE_COLUMNS}
        features['some_unknown_key'] = 999
        result = predict_sprint_risk(features, self.loaded)
        self.assertIn(result['risk'], LABEL_ORDER)

    def test_string_values_coerced(self):
        """Strings that look like numbers should still work via float()."""
        features = {col: '5.0' for col in FEATURE_COLUMNS}
        result = predict_sprint_risk(features, self.loaded)
        self.assertIn(result['risk'], LABEL_ORDER)


# ===========================================================================
class TestModelInfo(_BaseModelTest):

    def test_model_info_returns_dict(self):
        loaded = load_model(
            model_path=self._model_path,
            meta_path=self._meta_path,
        )
        info = get_model_info(loaded)
        self.assertIsInstance(info, dict)

    def test_info_has_required_keys(self):
        loaded = load_model(
            model_path=self._model_path,
            meta_path=self._meta_path,
        )
        info = get_model_info(loaded)
        for key in ['model_name', 'training_samples', 'feature_count',
                     'accuracy', 'important_features', 'training_date']:
            self.assertIn(key, info, f"Missing key: {key}")

    def test_info_model_name(self):
        loaded = load_model(
            model_path=self._model_path,
            meta_path=self._meta_path,
        )
        info = get_model_info(loaded)
        self.assertEqual(info['model_name'], 'RandomForestClassifier')

    def test_info_accuracy_in_range(self):
        loaded = load_model(
            model_path=self._model_path,
            meta_path=self._meta_path,
        )
        info = get_model_info(loaded)
        self.assertGreater(info['accuracy'], 0.0)
        self.assertLessEqual(info['accuracy'], 1.0)


# ===========================================================================
class TestTrainAndSave(unittest.TestCase):

    def setUp(self):
        self._temp_dir = tempfile.mkdtemp(prefix='risk_tas_test_')

    def tearDown(self):
        if os.path.isdir(self._temp_dir):
            shutil.rmtree(self._temp_dir)

    def test_train_and_save_creates_files(self):
        mp = os.path.join(self._temp_dir, 'model.joblib')
        meta = os.path.join(self._temp_dir, 'meta.json')

        # Monkey-patch paths for this test
        import ai.risk_model as rm
        orig_mp, orig_meta = rm._MODEL_PATH, rm._META_PATH
        rm._MODEL_PATH = mp
        rm._META_PATH  = meta
        try:
            result = train_and_save(verbose=False)
            self.assertTrue(os.path.isfile(mp))
            self.assertTrue(os.path.isfile(meta))
            self.assertIn('model', result)
        finally:
            rm._MODEL_PATH = orig_mp
            rm._META_PATH  = orig_meta


# ===========================================================================
class TestExistingAppHealth(unittest.TestCase):
    """Verify that Steps 1-10 still work after Step 11B changes."""

    def setUp(self):
        from app import app
        self.client = app.test_client()
        self.client.testing = True

    def _login(self, uid, role, uname):
        with self.client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['role']    = role
            sess['username'] = uname

    def test_dashboard_scrum_master(self):
        self._login(1, 'Scrum Master', 'scrummaster')
        r = self.client.get('/dashboard')
        self.assertEqual(r.status_code, 200)

    def test_dashboard_developer(self):
        self._login(2, 'Developer', 'developer1')
        r = self.client.get('/dashboard')
        self.assertEqual(r.status_code, 200)

    def test_kanban_board(self):
        self._login(1, 'Scrum Master', 'scrummaster')
        r = self.client.get('/projects/1/kanban')
        self.assertEqual(r.status_code, 200)


# ===========================================================================
if __name__ == '__main__':
    unittest.main(verbosity=2)
