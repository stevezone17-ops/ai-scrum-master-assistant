from database.db import get_db
from datetime import datetime

VALID_PRIORITIES = ['Critical', 'High', 'Medium', 'Low']
VALID_STATUSES = ['To Do', 'In Progress', 'Testing', 'Done']


class Task:
    @staticmethod
    def create(project_id, sprint_id, story_id, title, description, assigned_to, priority, estimated_hours, actual_hours, due_date, status="To Do"):
        conn = get_db()
        cursor = conn.cursor()

        # If sprint_id is not specified, inherit from story_id if available
        if story_id and not sprint_id:
            cursor.execute("SELECT sprint_id FROM user_stories WHERE id = ?", (story_id,))
            st = cursor.fetchone()
            if st and st['sprint_id']:
                sprint_id = st['sprint_id']

        cursor.execute("""
            INSERT INTO tasks (project_id, sprint_id, story_id, title, description, assigned_to, priority, estimated_hours, actual_hours, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            sprint_id if sprint_id else None,
            story_id if story_id else None,
            title,
            description,
            assigned_to if assigned_to else None,
            priority,
            estimated_hours,
            actual_hours,
            due_date if due_date else None,
            status
        ))
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id

    @staticmethod
    def get_by_project(project_id, assigned_to=None):
        conn = get_db()
        cursor = conn.cursor()
        today_str = datetime.now().strftime('%Y-%m-%d')

        query = """
            SELECT t.*,
                   u.username as assignee_name,
                   u.email as assignee_email,
                   s.name as sprint_name,
                   us.title as story_title,
                   (t.actual_hours - t.estimated_hours) as hours_variance,
                   CASE
                       WHEN t.due_date IS NOT NULL AND t.due_date < ? AND t.status != 'Done' THEN 1
                       ELSE 0
                   END as is_overdue
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN sprints s ON t.sprint_id = s.id
            LEFT JOIN user_stories us ON t.story_id = us.id
            WHERE t.project_id = ?
        """
        params = [today_str, project_id]

        if assigned_to:
            query += " AND t.assigned_to = ?"
            params.append(assigned_to)

        query += " ORDER BY is_overdue DESC, CASE t.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 END, t.created_at DESC"

        cursor.execute(query, params)
        tasks = cursor.fetchall()
        conn.close()
        return tasks

    @staticmethod
    def get_by_sprint(sprint_id):
        conn = get_db()
        cursor = conn.cursor()
        today_str = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT t.*, u.username as assignee_name, us.title as story_title,
                   (t.actual_hours - t.estimated_hours) as hours_variance,
                   CASE
                       WHEN t.due_date IS NOT NULL AND t.due_date < ? AND t.status != 'Done' THEN 1
                       ELSE 0
                   END as is_overdue
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN user_stories us ON t.story_id = us.id
            WHERE t.sprint_id = ?
            ORDER BY is_overdue DESC, CASE t.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 END, t.id ASC
        """, (today_str, sprint_id))
        tasks = cursor.fetchall()
        conn.close()
        return tasks

    @staticmethod
    def get_by_id(task_id):
        conn = get_db()
        cursor = conn.cursor()
        today_str = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT t.*, u.username as assignee_name, s.name as sprint_name, us.title as story_title,
                   (t.actual_hours - t.estimated_hours) as hours_variance,
                   CASE
                       WHEN t.due_date IS NOT NULL AND t.due_date < ? AND t.status != 'Done' THEN 1
                       ELSE 0
                   END as is_overdue
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            LEFT JOIN sprints s ON t.sprint_id = s.id
            LEFT JOIN user_stories us ON t.story_id = us.id
            WHERE t.id = ?
        """, (today_str, task_id))
        task = cursor.fetchone()
        conn.close()
        return task

    @staticmethod
    def update(task_id, title, description, assigned_to, priority, estimated_hours, actual_hours, due_date, status, sprint_id=None, story_id=None):
        conn = get_db()
        cursor = conn.cursor()

        # Sync sprint_id from story if not explicitly set
        if story_id and not sprint_id:
            cursor.execute("SELECT sprint_id FROM user_stories WHERE id = ?", (story_id,))
            st = cursor.fetchone()
            if st and st['sprint_id']:
                sprint_id = st['sprint_id']

        cursor.execute("""
            UPDATE tasks
            SET title = ?, description = ?, assigned_to = ?, priority = ?, estimated_hours = ?,
                actual_hours = ?, due_date = ?, status = ?, sprint_id = ?, story_id = ?
            WHERE id = ?
        """, (
            title,
            description,
            assigned_to if assigned_to else None,
            priority,
            estimated_hours,
            actual_hours,
            due_date if due_date else None,
            status,
            sprint_id if sprint_id else None,
            story_id if story_id else None,
            task_id
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def update_actual_hours_and_status(task_id, actual_hours, status=None):
        conn = get_db()
        cursor = conn.cursor()
        if status:
            cursor.execute("UPDATE tasks SET actual_hours = ?, status = ? WHERE id = ?", (actual_hours, status, task_id))
        else:
            cursor.execute("UPDATE tasks SET actual_hours = ? WHERE id = ?", (actual_hours, task_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update_status(task_id, status):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(task_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_task_stats(project_id, sprint_id=None):
        """Compute aggregate statistics for tasks."""
        conn = get_db()
        cursor = conn.cursor()
        today_str = datetime.now().strftime('%Y-%m-%d')

        query = """
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'To Do' THEN 1 ELSE 0 END) as todo_count,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress_count,
                SUM(CASE WHEN status = 'Testing' THEN 1 ELSE 0 END) as testing_count,
                SUM(CASE WHEN status = 'Done' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE WHEN due_date IS NOT NULL AND due_date < ? AND status != 'Done' THEN 1 ELSE 0 END) as overdue_count,
                COALESCE(SUM(estimated_hours), 0) as total_estimated_hours,
                COALESCE(SUM(actual_hours), 0) as total_actual_hours
            FROM tasks
            WHERE project_id = ?
        """
        params = [today_str, project_id]

        if sprint_id:
            query += " AND sprint_id = ?"
            params.append(sprint_id)

        cursor.execute(query, params)
        res = cursor.fetchone()
        conn.close()

        total = res['total_tasks'] or 0
        completed = res['completed_count'] or 0
        total_est = res['total_estimated_hours'] or 0.0
        total_act = res['total_actual_hours'] or 0.0

        return {
            'total_tasks': total,
            'todo_count': res['todo_count'] or 0,
            'in_progress_count': res['in_progress_count'] or 0,
            'testing_count': res['testing_count'] or 0,
            'completed_count': completed,
            'pending_count': total - completed,
            'overdue_count': res['overdue_count'] or 0,
            'total_estimated_hours': round(total_est, 1),
            'total_actual_hours': round(total_act, 1),
            'hours_variance': round(total_act - total_est, 1),
            'completion_pct': round((completed / total * 100), 1) if total > 0 else 0.0
        }

    @staticmethod
    def get_workload(project_id, sprint_id=None):
        conn = get_db()
        cursor = conn.cursor()
        query = """
            SELECT u.id as user_id, u.username, u.email, tm.role_in_project,
                   COUNT(t.id) as total_tasks,
                   SUM(CASE WHEN t.status = 'Done' THEN 1 ELSE 0 END) as completed_tasks,
                   SUM(CASE WHEN t.status != 'Done' THEN 1 ELSE 0 END) as pending_tasks,
                   COALESCE(SUM(t.estimated_hours), 0) as assigned_hours,
                   COALESCE(SUM(t.actual_hours), 0) as actual_hours
            FROM team_members tm
            JOIN users u ON tm.user_id = u.id
            LEFT JOIN tasks t ON t.assigned_to = u.id AND t.project_id = tm.project_id
        """
        params = []
        if sprint_id:
            query += " AND (t.sprint_id = ? OR t.sprint_id IS NULL)"
            params.append(sprint_id)

        query += " WHERE tm.project_id = ? GROUP BY u.id, u.username ORDER BY pending_tasks DESC"
        params.append(project_id)

        cursor.execute(query, params)
        members = cursor.fetchall()
        conn.close()

        result = []
        for m in members:
            m_dict = dict(m)
            assigned_hrs = m_dict.get('assigned_hours', 0) or 0
            m_dict['workload_pct'] = round((assigned_hrs / 40.0) * 100, 1)
            result.append(m_dict)
        return result
