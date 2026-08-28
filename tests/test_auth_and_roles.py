"""
tests/test_auth_and_roles.py
=============================
Step 14: Authentication, Password Hashing, Session, and Role-Based Permissions Tests
"""

import unittest
from app import app
from database.db import init_db
from models.user import User
from werkzeug.security import check_password_hash

class TestAuthAndRoles(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = app.test_client()
        self.client.testing = True

    def test_password_hashing_security(self):
        user = User.get_by_username('scrummaster')
        self.assertIsNotNone(user)
        self.assertTrue(check_password_hash(user['password_hash'], 'password123'))
        self.assertFalse(check_password_hash(user['password_hash'], 'wrongpassword'))

    def test_login_success(self):
        response = self.client.post('/login', data={
            'username': 'scrummaster',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Dashboard", html)

    def test_login_invalid_password(self):
        response = self.client.post('/login', data={
            'username': 'scrummaster',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Invalid email/username or password", html)

    def test_logout(self):
        self.client.post('/login', data={'username': 'scrummaster', 'password': 'password123'})
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("logged out successfully", html)

    def test_role_restriction_developer_cannot_create_project(self):
        self.client.post('/login', data={'username': 'developer1', 'password': 'password123'})
        response = self.client.post('/projects', data={
            'name': 'Unauthorized Project',
            'description': 'Test',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Only Scrum Masters are authorized to create new projects", html)

    def test_role_restriction_developer_cannot_create_sprint(self):
        self.client.post('/login', data={'username': 'developer1', 'password': 'password123'})
        response = self.client.post('/projects/1/sprints', data={
            'name': 'Unauthorized Sprint',
            'goal': 'Test Goal',
            'start_date': '2026-01-01',
            'end_date': '2026-01-14'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Only Scrum Masters can perform this action", html)


if __name__ == '__main__':
    unittest.main()
