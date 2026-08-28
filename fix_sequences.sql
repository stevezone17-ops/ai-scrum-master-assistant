-- Fix PostgreSQL Identity Sequences after SQLite Data Migration
-- Run this in the Supabase SQL Editor to align sequence counters above MAX(id)

SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1));
SELECT setval(pg_get_serial_sequence('projects', 'id'), COALESCE((SELECT MAX(id) FROM projects), 1));
SELECT setval(pg_get_serial_sequence('team_members', 'id'), COALESCE((SELECT MAX(id) FROM team_members), 1));
SELECT setval(pg_get_serial_sequence('sprints', 'id'), COALESCE((SELECT MAX(id) FROM sprints), 1));
SELECT setval(pg_get_serial_sequence('user_stories', 'id'), COALESCE((SELECT MAX(id) FROM user_stories), 1));
SELECT setval(pg_get_serial_sequence('tasks', 'id'), COALESCE((SELECT MAX(id) FROM tasks), 1));
SELECT setval(pg_get_serial_sequence('bugs', 'id'), COALESCE((SELECT MAX(id) FROM bugs), 1));
SELECT setval(pg_get_serial_sequence('standup_updates', 'id'), COALESCE((SELECT MAX(id) FROM standup_updates), 1));
