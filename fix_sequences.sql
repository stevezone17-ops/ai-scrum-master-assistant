-- Native PostgreSQL Identity Sequence Alignment

SELECT setval(pg_get_serial_sequence('users', 'id'), 9);
SELECT setval(pg_get_serial_sequence('projects', 'id'), 34);
SELECT setval(pg_get_serial_sequence('team_members', 'id'), 38);
SELECT setval(pg_get_serial_sequence('sprints', 'id'), 7);
SELECT setval(pg_get_serial_sequence('user_stories', 'id'), 18);
SELECT setval(pg_get_serial_sequence('tasks', 'id'), 15);
SELECT setval(pg_get_serial_sequence('bugs', 'id'), 3);
SELECT setval(pg_get_serial_sequence('standup_updates', 'id'), 36);
