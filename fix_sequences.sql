-- Native PostgreSQL Identity Sequence Alignment

SELECT setval(pg_get_serial_sequence('users', 'id'), 11);
SELECT setval(pg_get_serial_sequence('projects', 'id'), 34);
SELECT setval(pg_get_serial_sequence('team_members', 'id'), 41);
SELECT setval(pg_get_serial_sequence('sprints', 'id'), 7);
SELECT setval(pg_get_serial_sequence('user_stories', 'id'), 20);
SELECT setval(pg_get_serial_sequence('tasks', 'id'), 15);
SELECT setval(pg_get_serial_sequence('bugs', 'id'), 3);
SELECT setval(pg_get_serial_sequence('standup_updates', 'id'), 36);
