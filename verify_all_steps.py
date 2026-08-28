"""
verify_all_steps.py
===================
Programmatic verification script for Step 12B (AI Recommendations) and Step 12C (AI Stand-up Analysis)
"""
import sys
import os
from datetime import date, timedelta

from app import app
from database.db import get_db, init_db
from models.task import Task
from models.standup import StandupUpdate
from ai.recommendations import get_recommendations
from ai.standup_analysis import generate_team_standup_summary, classify_standup_text

def run_verification():
    print("=" * 70)
    print(" PROGRAMMATIC VERIFICATION FOR STEP 12B & STEP 12C")
    print("=" * 70)
    
    client = app.test_client()
    client.testing = True

    # 1. Login as Scrum Master
    print("\n[Step 1] Logging in as Scrum Master (scrummaster)...")
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'scrummaster'
        sess['role'] = 'Scrum Master'
        sess['email'] = 'scrummaster@example.com'

    # 2. View Dashboard as Scrum Master
    print("[Step 2] Fetching Dashboard for Scrum Master...")
    resp = client.get('/dashboard')
    assert resp.status_code == 200, f"Dashboard failed with status {resp.status_code}"
    html = resp.get_data(as_text=True)
    assert 'AI Sprint Risk Assessment' in html, "AI Risk Assessment card missing"
    assert 'AI Scrum Master Recommendations' in html, "AI Recommendations card missing"
    assert 'AI Daily Stand-up Summary' in html, "AI Stand-up Summary card missing"
    print("  [OK] Dashboard rendered cleanly with all 3 AI cards!")

    # 3. Create an overdue task condition
    print("\n[Step 3] Creating overdue task condition in Project 1...")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (project_id, sprint_id, title, description, assigned_to, priority, estimated_hours, actual_hours, due_date, status)
        VALUES (1, 1, 'Overdue Critical API Task', 'Overdue task for verification', 1, 'High', 10, 5, '2026-08-01', 'In Progress')
    """)
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"  [OK] Inserted task ID {task_id} with due_date='2026-08-01' (Overdue).")

    # 4. Verify AI Recommendations picks up Overdue Task with HIGH priority
    print("\n[Step 4] Re-fetching Dashboard to verify AI Recommendations...")
    resp = client.get('/dashboard')
    html = resp.get_data(as_text=True)
    recs_data = get_recommendations(1)
    recs = recs_data.get('recommendations', [])
    print(f"  Generated {len(recs)} recommendation(s):")
    for r in recs:
        print(f"    - [{r['priority']}] {r['title']}: {r['description']}")
    
    overdue_rec = next((r for r in recs if 'overdue' in r['title'].lower() or 'overdue' in r['description'].lower()), None)
    assert overdue_rec is not None, "Overdue task recommendation was not generated!"
    assert overdue_rec['priority'] == 'HIGH', "Overdue recommendation priority is not HIGH!"
    print("  [OK] Overdue recommendation correctly triggered with HIGH priority!")

    # 5. Login as Product Owner & Verify Access
    print("\n[Step 5] Logging in as Product Owner (productowner)...")
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['username'] = 'productowner'
        sess['role'] = 'Product Owner'

    resp = client.get('/dashboard')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'AI Scrum Master Recommendations' in html
    assert 'AI Daily Stand-up Summary' in html
    print("  [OK] Product Owner view verified with read access to AI cards!")

    # 6. Login as Developer & Submit Stand-up with Blocker
    print("\n[Step 6] Logging in as Developer (developer1)...")
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['username'] = 'developer1'
        sess['role'] = 'Developer'

    today_str = date.today().isoformat()
    print(f"[Step 7] Submitting Daily Stand-up update for today ({today_str})...")
    post_data = {
        'yesterday_work': 'Worked on payment gateway integration code.',
        'today_plan': 'Testing payment webhook callbacks.',
        'blockers': 'Waiting for payment API credentials.',
        'comments': 'Cannot complete testing until credentials provided.'
    }
    resp = client.post('/projects/1/standup', data=post_data, follow_redirects=True)
    assert resp.status_code == 200
    print("  [OK] Stand-up update submitted successfully.")

    # 7. Verify AI Stand-up Classification
    print("\n[Step 8] Checking AI Stand-up analysis on Stand-up view...")
    resp = client.get('/projects/1/standup')
    html = resp.get_data(as_text=True)
    assert 'BLOCKED' in html, "Status 'BLOCKED' not found in stand-up HTML"
    print("  [OK] AI Analysis correctly classified update as 'BLOCKED'!")

    # 8. Edit same day stand-up update and check duplicate prevention
    print("\n[Step 9] Editing today's stand-up update to test duplicate prevention...")
    edit_data = {
        'yesterday_work': 'Completed payment gateway integration code and unit tests.',
        'today_plan': 'Testing payment webhook callbacks.',
        'blockers': 'Waiting for payment API credentials.',
        'comments': 'Updated note for verification.'
    }
    resp = client.post('/projects/1/standup', data=edit_data, follow_redirects=True)
    assert resp.status_code == 200

    user_standups = StandupUpdate.get_by_project(1, date=today_str)
    dev_standups = [s for s in user_standups if s['user_id'] == 2]
    assert len(dev_standups) == 1, f"Expected 1 record for developer today, found {len(dev_standups)}"
    assert dev_standups[0]['yesterday_work'] == edit_data['yesterday_work']
    print(f"  [OK] Record updated in place. Single record count confirmed ({len(dev_standups)}) - No duplicates created!")

    # 9. Clean up test task
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    print("  [OK] Cleaned up test overdue task.")

    # 10. Verify Step 12D AI Scrum Master Assistant Chat Endpoint
    print("\n[Step 10] Testing AI Scrum Master Assistant (Step 12D)...")
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'scrummaster'
        sess['role'] = 'Scrum Master'

    # Test assistant page load
    resp = client.get('/projects/1/assistant')
    assert resp.status_code == 200
    assert 'AI Scrum Master Assistant' in resp.get_data(as_text=True)
    print("  [OK] Assistant page rendered successfully.")

    questions_to_test = [
        ("How is the current sprint doing?", "SPRINT_STATUS"),
        ("Is the sprint at risk?", "RISK"),
        ("Which tasks are overdue?", "OVERDUE_TASKS"),
        ("Who has the highest workload?", "TEAM_WORKLOAD"),
        ("What blockers were reported today?", "BLOCKERS"),
        ("What should the Scrum Master focus on?", "RECOMMENDATIONS")
    ]

    for q_text, expected_intent in questions_to_test:
        resp = client.post(
            '/projects/1/assistant/chat',
            json={'question': q_text},
            content_type='application/json'
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['intent'] == expected_intent
        assert not data.get('error')
        assert len(data.get('response', '')) > 10
        print(f"  [OK] Question: '{q_text}' -> Intent: {data['intent']} | Response length: {len(data['response'])}")

    print("\n" + "=" * 70)
    print(" ALL VERIFICATION STEPS (12A, 12B, 12C, 12D) PASSED SUCCESSFULLY! (100% VERIFIED)")
    print("=" * 70)

if __name__ == '__main__':
    run_verification()
