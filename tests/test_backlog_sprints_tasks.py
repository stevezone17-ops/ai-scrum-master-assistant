"""
tests/test_backlog_sprints_tasks.py
====================================
Step 14: Product Backlog, Sprint Management, Task Management, and Kanban Tests
"""

import unittest
from app import app
from database.db import init_db
from models.task import Task
from models.story import UserStory

class TestBacklogSprintsTasks(unittest.TestCase):
    def setUp(self):
        init_db()
        self.client = app.test_client()
        self.client.testing = True

    def login_client(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def test_user_story_creation_valid(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.post('/projects/1/backlog', data={
            'title': 'As a user I want export features',
            'description': 'Export project details',
            'priority': 'High',
            'story_points': 5,
            'status': 'Backlog'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("As a user I want export features", html)

    def test_user_story_invalid_points(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.post('/projects/1/backlog', data={
            'title': 'Invalid Story Points',
            'description': 'Test',
            'priority': 'High',
            'story_points': 999, # Invalid story points
            'status': 'Backlog'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Invalid story points", html)

    def test_sprint_creation_invalid_dates(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.post('/projects/1/sprints', data={
            'name': 'Bad Date Sprint',
            'goal': 'Goal',
            'start_date': '2026-05-10',
            'end_date': '2026-05-01' # End before start
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("End date cannot be before start date", html)

    def test_task_creation_invalid_hours(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.post('/tasks/create', data={
            'project_id': 1,
            'title': 'Invalid Hours Task',
            'estimated_hours': 0, # Invalid estimated hours <= 0
            'priority': 'Medium'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Estimated hours must be greater than 0", html)

    def test_kanban_board_view(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.get('/projects/1/kanban', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Kanban Board", html)

    def test_kanban_update_task_status_post(self):
        self.login_client('scrummaster', 'password123')
        response = self.client.post('/tasks/1/update_progress', data={
            'status': 'In Progress',
            'actual_hours': 5.0
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
