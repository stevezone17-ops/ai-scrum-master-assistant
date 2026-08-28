from database.db import get_db

PRIORITY_ORDER = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
VALID_PRIORITIES = ['Critical', 'High', 'Medium', 'Low']
VALID_POINTS = [1, 2, 3, 5, 8, 13]
VALID_STATUSES = ['Backlog', 'Ready', 'In Progress', 'Done']

class UserStory:
    @staticmethod
    def create(project_id, title, description, priority, story_points, status, assigned_to=None, sprint_id=None):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO user_stories
               (project_id, sprint_id, title, description, priority, story_points, status, assigned_to)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, sprint_id if sprint_id else None, title, description,
             priority, story_points, status, assigned_to if assigned_to else None)
        )
        story_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return story_id

    @staticmethod
    def get_by_project(project_id, sort_by='priority'):
        conn = get_db()
        cursor = conn.cursor()

        order_map = {
            'priority': "CASE us.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 END ASC, us.created_at DESC",
            'story_points': "us.story_points DESC, us.created_at DESC",
            'status': "us.status ASC, us.created_at DESC",
            'created_at': "us.created_at DESC",
        }
        order_clause = order_map.get(sort_by, order_map['priority'])

        cursor.execute(f"""
            SELECT us.*,
                   s.name as sprint_name,
                   u.username as assignee_name,
                   u.email as assignee_email,
                   (SELECT COUNT(*) FROM tasks t WHERE t.story_id = us.id) as task_count,
                   (SELECT COUNT(*) FROM tasks t WHERE t.story_id = us.id AND t.status = 'Done') as completed_task_count
            FROM user_stories us
            LEFT JOIN sprints s ON us.sprint_id = s.id
            LEFT JOIN users u ON us.assigned_to = u.id
            WHERE us.project_id = ?
            ORDER BY {order_clause}
        """, (project_id,))
        stories = cursor.fetchall()
        conn.close()
        return stories

    @staticmethod
    def get_by_id(story_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT us.*, s.name as sprint_name, u.username as assignee_name
            FROM user_stories us
            LEFT JOIN sprints s ON us.sprint_id = s.id
            LEFT JOIN users u ON us.assigned_to = u.id
            WHERE us.id = ?
        """, (story_id,))
        story = cursor.fetchone()
        conn.close()
        return story

    @staticmethod
    def get_by_assignee(project_id, user_id):
        """Return stories assigned to a specific developer within a project."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT us.*, u.username as assignee_name
            FROM user_stories us
            LEFT JOIN users u ON us.assigned_to = u.id
            WHERE us.project_id = ? AND us.assigned_to = ?
            ORDER BY CASE us.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 END
        """, (project_id, user_id))
        stories = cursor.fetchall()
        conn.close()
        return stories

    @staticmethod
    def update(story_id, title, description, priority, story_points, status, assigned_to=None, sprint_id=None):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_stories
            SET title = ?, description = ?, priority = ?, story_points = ?,
                status = ?, assigned_to = ?, sprint_id = ?
            WHERE id = ?
        """, (title, description, priority, story_points, status,
              assigned_to if assigned_to else None,
              sprint_id if sprint_id else None,
              story_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update_status(story_id, status):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE user_stories SET status = ? WHERE id = ?", (status, story_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(story_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_stories WHERE id = ?", (story_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_backlog_stats(project_id):
        """Compute backlog summary statistics for the project."""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user_stories WHERE project_id = ?", (project_id,))
        total_stories = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(story_points), 0) FROM user_stories WHERE project_id = ?", (project_id,))
        total_points = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_stories WHERE project_id = ? AND status = 'Done'", (project_id,))
        completed_stories = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(story_points), 0) FROM user_stories WHERE project_id = ? AND status = 'Done'", (project_id,))
        completed_points = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_stories WHERE project_id = ? AND status != 'Done'", (project_id,))
        pending_stories = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_stories WHERE project_id = ? AND priority IN ('Critical', 'High')", (project_id,))
        high_priority_count = cursor.fetchone()[0]

        conn.close()
        return {
            'total_stories': total_stories,
            'total_points': total_points,
            'completed_stories': completed_stories,
            'completed_points': completed_points,
            'pending_stories': pending_stories,
            'high_priority_count': high_priority_count,
        }
