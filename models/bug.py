from database.db import get_db

class Bug:
    @staticmethod
    def create(project_id, sprint_id, title, description, severity, status, reported_by, assigned_to=None):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bugs (project_id, sprint_id, title, description, severity, status, reported_by, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, sprint_id if sprint_id else None, title, description, severity, status, reported_by, assigned_to if assigned_to else None))
        bug_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return bug_id

    @staticmethod
    def get_by_project(project_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*, reporter.username as reporter_name, assignee.username as assignee_name, s.name as sprint_name
            FROM bugs b
            LEFT JOIN users reporter ON b.reported_by = reporter.id
            LEFT JOIN users assignee ON b.assigned_to = assignee.id
            LEFT JOIN sprints s ON b.sprint_id = s.id
            WHERE b.project_id = ?
            ORDER BY b.created_at DESC
        """, (project_id,))
        bugs = cursor.fetchall()
        conn.close()
        return bugs

    @staticmethod
    def get_by_sprint(sprint_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*, reporter.username as reporter_name, assignee.username as assignee_name
            FROM bugs b
            LEFT JOIN users reporter ON b.reported_by = reporter.id
            LEFT JOIN users assignee ON b.assigned_to = assignee.id
            WHERE b.sprint_id = ?
            ORDER BY b.created_at DESC
        """, (sprint_id,))
        bugs = cursor.fetchall()
        conn.close()
        return bugs

    @staticmethod
    def update_status(bug_id, status):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE bugs SET status = ? WHERE id = ?", (status, bug_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(bug_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
        conn.commit()
        conn.close()
