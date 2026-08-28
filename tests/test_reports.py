"""
tests/test_reports.py
======================
Unit and Integration Tests for Step 13: Project and Sprint Reports
"""

import unittest
from app import app
from database.db import init_db, get_db
from models.project import Project
from models.sprint import Sprint
from models.task import Task
from routes.report_routes import _calculate_project_report_data, _calculate_sprint_report_data

class TestReportModule(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = app.test_client()
        self.client.testing = True

    def login_client(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Calculation Helper Tests (Real Database Metrics)
    # -------------------------------------------------------------------------
    def test_sprint_report_data_calculation(self):
        sprint, data = _calculate_sprint_report_data(project_id=1, sprint_id=1)
        self.assertIsNotNone(sprint)
        self.assertIsNotNone(data)
        metrics = data['metrics']
        self.assertIn('total_tasks', metrics)
        self.assertIn('completed_tasks', metrics)
        self.assertIn('velocity', metrics)
        self.assertIn('estimated_hours', metrics)

    def test_project_report_data_calculation(self):
        metrics, ai_risk, recs = _calculate_project_report_data(project_id=1)
        self.assertIsNotNone(metrics)
        self.assertIn('team_size', metrics)
        self.assertIn('progress_pct', metrics)
        self.assertIn('health', metrics)

    # -------------------------------------------------------------------------
    # 2. HTTP Routes Tests
    # -------------------------------------------------------------------------
    def test_sprint_report_view_scrum_master(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.get('/projects/1/reports?report_type=sprint')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AGILE SPRINT SUMMARY REPORT", html)

    def test_project_report_view_product_owner(self):
        self.login_client('productowner', 'password123')
        response = self.client.get('/projects/1/reports?report_type=project')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("PROJECT OVERVIEW REPORT", html)

    def test_dedicated_sprint_report_route(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.get('/projects/1/reports/sprint/1', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AGILE SPRINT SUMMARY REPORT", html)

    def test_developer_report_view(self):
        self.login_client('developer1', 'password123')
        response = self.client.get('/projects/1/reports')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Export PDF", html)

    # -------------------------------------------------------------------------
    # 3. PDF Export Route Tests
    # -------------------------------------------------------------------------
    def test_pdf_export_sprint_report(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.get('/projects/1/reports/export/pdf?report_type=sprint&sprint_id=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.get_data().startswith(b'%PDF'))

    def test_pdf_export_project_report(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.get('/projects/1/reports/export/pdf?report_type=project')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.get_data().startswith(b'%PDF'))

    # -------------------------------------------------------------------------
    # 4. Security & Error Handling Tests
    # -------------------------------------------------------------------------
    def test_unauthorized_project_report_access(self):
        self.login_client('developer1', 'password123')
        # developer1 does not belong to project 999
        response = self.client.get('/projects/999/reports', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Access Denied", html)

    def test_unauthorized_pdf_export_access(self):
        self.login_client('developer1', 'password123')
        response = self.client.get('/projects/999/reports/export/pdf', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Access Denied", html)

    def test_invalid_sprint_id(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.get('/projects/1/reports/sprint/99999', follow_redirects=True)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
