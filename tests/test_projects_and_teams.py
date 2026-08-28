"""
tests/test_projects_and_teams.py
=================================
Step 14: Project CRUD, Team Assignments, and Data Isolation Tests
"""

import unittest
from app import app
from database.db import init_db
from models.project import Project

class TestProjectsAndTeams(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = app.test_client()
        self.client.testing = True

    def login_client(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def test_project_creation_scrum_master(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.post('/projects', data={
            'name': 'New Test Project Step 14',
            'description': 'Description for step 14 test',
            'start_date': '2026-09-01',
            'end_date': '2026-10-30',
            'status': 'Active'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("New Test Project Step 14", html)

    def test_project_list_view(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.get('/projects', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Projects", html)

    def test_team_management_add_member(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.post('/projects/1/team', data={
            'user_id': 3, # developer2
            'role_in_project': 'Developer'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_cross_project_isolation_deny_unassigned_developer(self):
        self.login_client('developer1', 'password123')
        # Accessing non-existent or unassigned project standup
        response = self.client.get('/projects/999/standup', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("do not have access", html)


if __name__ == '__main__':
    unittest.main()
