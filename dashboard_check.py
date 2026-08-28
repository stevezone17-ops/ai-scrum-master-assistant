import sys
from app import app

client = app.test_client()
client.testing = True

roles = [
    {'user_id': 1, 'role': 'Scrum Master', 'username': 'scrummaster'},
    {'user_id': 3, 'role': 'Product Owner', 'username': 'productowner'},
    {'user_id': 2, 'role': 'Developer', 'username': 'developer1'},
]

checks = {
    'Scrum Master': [
        (b'Agile Workspace Overview', 'Page title'),
        (b'Project Health', 'Health indicator'),
        (b'Active Sprint Metrics', 'Active sprint section'),
        (b'Task Status Distribution', 'Task chart'),
        (b'Team Workload Capacity', 'Workload table'),
        (b'Overdue Tasks', 'Overdue tasks section'),
        (b'Sprint Velocity', 'Velocity chart'),
        (b'Recent Activity Feed', 'Recent activity'),
        (b'Kanban Board', 'Quick action - Kanban'),
        (b'Reports', 'Quick action - Reports'),
        (b'New Project', 'Quick action - New Project visible'),
        (b'New Sprint', 'Quick action - New Sprint visible'),
    ],
    'Product Owner': [
        (b'Agile Workspace Overview', 'Page title'),
        (b'Project Health', 'Health indicator'),
        (b'Product Backlog', 'Backlog stats'),
        (b'Task Status Distribution', 'Task chart'),
        (b'Kanban Board', 'Kanban button'),
        (b'New User Story', 'New User Story visible'),
        (b'New Task', 'New Task visible'),
    ],
    'Developer': [
        (b'Agile Workspace Overview', 'Page title'),
        (b'My Assigned Developer Workspace', 'Developer workspace panel'),
        (b'Welcome back, developer1', 'Personalized greeting'),
        (b'(Developer)', 'Role badge'),
        (b'Assigned Tasks', 'Assigned tasks metric'),
        (b'Pending Tasks', 'Pending tasks metric'),
        (b'My Workload Allocation', 'Workload allocation metric'),
        (b'My Assigned Tasks List:', 'Tasks table'),
        (b'View My Kanban Tasks', 'Kanban link for developer'),
    ],
}

hidden_checks = {
    'Developer': [
        (b'New Project', 'New Project should be HIDDEN'),
        (b'New Sprint', 'New Sprint should be HIDDEN'),
    ]
}

total_pass = 0
total_fail = 0

for r in roles:
    with client.session_transaction() as sess:
        sess['user_id'] = r['user_id']
        sess['role'] = r['role']
        sess['username'] = r['username']

    res = client.get('/dashboard')
    print(f'\n=== {r["role"]} Dashboard (HTTP {res.status_code}) ===')

    role_checks = checks.get(r['role'], [])
    for text, label in role_checks:
        found = text in res.data
        status = 'PASS' if found else 'FAIL'
        if found:
            total_pass += 1
        else:
            total_fail += 1
        print(f'  [{status}] {label}')

    if r['role'] in hidden_checks:
        print('  --- Hidden controls (should NOT appear) ---')
        for text, label in hidden_checks[r['role']]:
            found = text in res.data
            status = 'PASS' if not found else 'FAIL'
            if not found:
                total_pass += 1
            else:
                total_fail += 1
            print(f'  [{status}] {label}')

print(f'\n===== SUMMARY =====')
print(f'PASSED: {total_pass}')
print(f'FAILED: {total_fail}')
print(f'RESULT: {"ALL PASS" if total_fail == 0 else "FAILURES FOUND"}')
sys.exit(0 if total_fail == 0 else 1)
