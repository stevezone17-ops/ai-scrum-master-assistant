"""
tests/test_assistant.py
========================
Unit and Integration Tests for Step 12D: AI Scrum Master Assistant
"""

import unittest
from unittest.mock import patch
from app import app
from database.db import init_db, get_db
from models.project import Project
from models.sprint import Sprint
from models.task import Task
from models.story import UserStory
from ai.assistant import (
    detect_intent,
    answer_question,
    get_project_context,
    generate_response_from_context,
    INTENT_SPRINT_STATUS,
    INTENT_RISK,
    INTENT_OVERDUE_TASKS,
    INTENT_TEAM_WORKLOAD,
    INTENT_BLOCKERS,
    INTENT_RECOMMENDATIONS,
    INTENT_TASK_STATUS,
    INTENT_BACKLOG_STATUS,
    INTENT_UNKNOWN
)

class TestAIAssistant(unittest.TestCase):
    def setUp(self):
        init_db()
        self.app_client = app.test_client()
        self.app_client.testing = True

    def login_client(self, username, password):
        return self.app_client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    # -------------------------------------------------------------------------
    # 1. Intent Detection Tests
    # -------------------------------------------------------------------------
    def test_intent_detection_patterns(self):
        # Sprint Status
        self.assertEqual(detect_intent("How is the sprint doing?"), INTENT_SPRINT_STATUS)
        self.assertEqual(detect_intent("What is the current sprint progress?"), INTENT_SPRINT_STATUS)
        self.assertEqual(detect_intent("How is the current sprint?"), INTENT_SPRINT_STATUS)

        # Sprint Risk
        self.assertEqual(detect_intent("Is the sprint at risk?"), INTENT_RISK)
        self.assertEqual(detect_intent("What is the sprint risk?"), INTENT_RISK)
        self.assertEqual(detect_intent("How risky is the current sprint?"), INTENT_RISK)

        # Overdue Tasks
        self.assertEqual(detect_intent("Which tasks are overdue?"), INTENT_OVERDUE_TASKS)
        self.assertEqual(detect_intent("What tasks are late?"), INTENT_OVERDUE_TASKS)
        self.assertEqual(detect_intent("Show me overdue tasks."), INTENT_OVERDUE_TASKS)

        # Team Workload
        self.assertEqual(detect_intent("Who has the highest workload?"), INTENT_TEAM_WORKLOAD)
        self.assertEqual(detect_intent("Who is overloaded?"), INTENT_TEAM_WORKLOAD)
        self.assertEqual(detect_intent("Which developer has the most work?"), INTENT_TEAM_WORKLOAD)

        # Stand-up Blockers
        self.assertEqual(detect_intent("What blockers were reported today?"), INTENT_BLOCKERS)
        self.assertEqual(detect_intent("Are there any blockers?"), INTENT_BLOCKERS)
        self.assertEqual(detect_intent("What is blocking the team?"), INTENT_BLOCKERS)

        # Recommendations
        self.assertEqual(detect_intent("What should I focus on?"), INTENT_RECOMMENDATIONS)
        self.assertEqual(detect_intent("What should the Scrum Master do?"), INTENT_RECOMMENDATIONS)
        self.assertEqual(detect_intent("What should we do next?"), INTENT_RECOMMENDATIONS)

        # Backlog Status
        self.assertEqual(detect_intent("How many backlog items are there?"), INTENT_BACKLOG_STATUS)
        self.assertEqual(detect_intent("How many story points remain?"), INTENT_BACKLOG_STATUS)
        self.assertEqual(detect_intent("What is the backlog status?"), INTENT_BACKLOG_STATUS)

        # Task Status
        self.assertEqual(detect_intent("How many tasks are completed?"), INTENT_TASK_STATUS)
        self.assertEqual(detect_intent("How many tasks are in progress?"), INTENT_TASK_STATUS)
        self.assertEqual(detect_intent("What is the task status?"), INTENT_TASK_STATUS)

    def test_intent_detection_unknown_and_empty(self):
        self.assertEqual(detect_intent(""), INTENT_UNKNOWN)
        self.assertEqual(detect_intent("   "), INTENT_UNKNOWN)
        self.assertEqual(detect_intent("What is the weather outside?"), INTENT_UNKNOWN)
        self.assertEqual(detect_intent("Tell me a funny joke!"), INTENT_UNKNOWN)

    # -------------------------------------------------------------------------
    # 2. Database-Driven Response Tests
    # -------------------------------------------------------------------------
    def test_answer_sprint_status(self):
        res = answer_question("How is the sprint doing?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_SPRINT_STATUS)
        self.assertIn("Sprint", res['response'])

    def test_answer_sprint_risk(self):
        res = answer_question("Is the sprint at risk?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_RISK)
        self.assertIn("Risk", res['response'])

    def test_answer_overdue_tasks(self):
        res = answer_question("Which tasks are overdue?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_OVERDUE_TASKS)
        self.assertTrue("Overdue Tasks" in res['response'] or "overdue tasks" in res['response'])

    def test_answer_team_workload(self):
        res = answer_question("Who has the highest workload?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_TEAM_WORKLOAD)
        self.assertIn("Workload", res['response'])

    def test_answer_blockers(self):
        res = answer_question("What blockers were reported today?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_BLOCKERS)
        self.assertIn("Blockers", res['response'])

    def test_answer_recommendations(self):
        res = answer_question("What should I focus on?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_RECOMMENDATIONS)
        self.assertTrue("Recommendations" in res['response'] or "Action Items" in res['response'] or "progressing normally" in res['response'])

    def test_answer_backlog_status(self):
        res = answer_question("What is the backlog status?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_BACKLOG_STATUS)
        self.assertIn("Product Backlog", res['response'])

    def test_answer_task_status(self):
        res = answer_question("What is the task status?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_TASK_STATUS)
        self.assertIn("Task Status Breakdown", res['response'])

    def test_unknown_question_fallback(self):
        res = answer_question("What is your favorite color?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertEqual(res['intent'], INTENT_UNKNOWN)
        self.assertEqual(res['response'], "I can help with sprint progress, risk, overdue tasks, team workload, blockers, backlog, task status, and Scrum recommendations.")

    def test_empty_question(self):
        res = answer_question("", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertTrue(res['error'])
        self.assertEqual(res['response'], "Please provide a valid question.")

    # -------------------------------------------------------------------------
    # 3. Security, Project Isolation & Role Permission Tests
    # -------------------------------------------------------------------------
    def test_project_isolation_access_denied(self):
        # User 2 (developer1) is assigned to Project 1, but not Project 999
        res = answer_question("How is the sprint doing?", project_id=999, user_id=2, user_role="Developer")
        self.assertTrue(res['error'])
        self.assertIn("Access Denied", res['response'])

    def test_invalid_project_id(self):
        # Scrum master accessing non-existent project
        res = answer_question("How is the sprint doing?", project_id=99999, user_id=1, user_role="Scrum Master")
        self.assertTrue(res['error'])
        self.assertTrue("Access Denied" in res['response'] or "Project not found" in res['response'])

    # -------------------------------------------------------------------------
    # 4. Fallback / Edge Case Handling
    # -------------------------------------------------------------------------
    def test_no_active_sprint(self):
        # Create temporary project with 0 sprints using model method
        p_id = Project.create('Empty Test Project', 'Test', '2026-01-01', '2026-12-31', 'Planning', 1)

        res = answer_question("How is the sprint doing?", project_id=p_id, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertIn("No Active Sprint Found", res['response'])

    @patch('ai.assistant.get_ai_sprint_risk_assessment')
    def test_missing_ml_model_fallback(self, mock_risk):
        mock_risk.return_value = {'error': True, 'message': 'Model file missing'}
        res = answer_question("Is the sprint at risk?", project_id=1, user_id=1, user_role="Scrum Master")
        self.assertFalse(res['error'])
        self.assertIn("Unable to calculate risk assessment", res['response'])

    # -------------------------------------------------------------------------
    # 5. HTTP Flask Endpoint & Chat Session Integration Tests
    # -------------------------------------------------------------------------
    def test_assistant_http_get_view(self):
        self.login_client('scrummaster', 'password123')
        resp = self.app_client.get('/projects/1/assistant', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("AI Scrum Master Assistant", html)
        self.assertIn("Suggested Questions", html)

    def test_assistant_http_post_chat(self):
        self.login_client('scrummaster', 'password123')
        resp = self.app_client.post('/projects/1/assistant/chat', json={
            'question': 'How is the current sprint doing?'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['error'])
        self.assertEqual(data['intent'], INTENT_SPRINT_STATUS)
        self.assertIn("Sprint", data['response'])

    def test_assistant_http_post_chat_unauthorized(self):
        self.login_client('developer1', 'password123')
        # developer1 belongs to project 1, but not project 999
        resp = self.app_client.post('/projects/999/assistant/chat', json={
            'question': 'How is the current sprint doing?'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['error'])
        self.assertIn("Access Denied", data['response'])


if __name__ == '__main__':
    unittest.main()
