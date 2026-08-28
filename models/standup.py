from database.db import get_db

class StandupUpdate:
    @staticmethod
    def create(project_id, sprint_id, user_id, date, yesterday_work, today_plan, blockers="None", comments=""):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO standup_updates (project_id, sprint_id, user_id, date, yesterday_work, today_plan, blockers, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, sprint_id if sprint_id else None, user_id, date, yesterday_work, today_plan, blockers, comments or ""))
        update_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return update_id

    @staticmethod
    def update(update_id, yesterday_work, today_plan, blockers="None", comments="", sprint_id=None):
        conn = get_db()
        cursor = conn.cursor()
        if sprint_id:
            cursor.execute("""
                UPDATE standup_updates
                SET yesterday_work = ?, today_plan = ?, blockers = ?, comments = ?, sprint_id = ?, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (yesterday_work, today_plan, blockers, comments or "", sprint_id, update_id))
        else:
            cursor.execute("""
                UPDATE standup_updates
                SET yesterday_work = ?, today_plan = ?, blockers = ?, comments = ?, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (yesterday_work, today_plan, blockers, comments or "", update_id))
        conn.commit()
        conn.close()
        return update_id

    @staticmethod
    def get_by_id(update_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT su.*, u.username, u.role as user_role, s.name as sprint_name
            FROM standup_updates su
            JOIN users u ON su.user_id = u.id
            LEFT JOIN sprints s ON su.sprint_id = s.id
            WHERE su.id = ?
        """, (update_id,))
        update = cursor.fetchone()
        conn.close()
        return update

    @staticmethod
    def get_user_standup_for_date(project_id, user_id, date):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT su.*, u.username, u.role as user_role, s.name as sprint_name
            FROM standup_updates su
            JOIN users u ON su.user_id = u.id
            LEFT JOIN sprints s ON su.sprint_id = s.id
            WHERE su.project_id = ? AND su.user_id = ? AND su.date = ?
            ORDER BY su.created_at DESC
            LIMIT 1
        """, (project_id, user_id, date))
        update = cursor.fetchone()
        conn.close()
        return update

    @staticmethod
    def get_user_standup_history(project_id, user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT su.*, u.username, u.role as user_role, s.name as sprint_name
            FROM standup_updates su
            JOIN users u ON su.user_id = u.id
            LEFT JOIN sprints s ON su.sprint_id = s.id
            WHERE su.project_id = ? AND su.user_id = ?
            ORDER BY su.date DESC, su.created_at DESC
        """, (project_id, user_id))
        updates = cursor.fetchall()
        conn.close()
        return updates

    @staticmethod
    def get_recent_standups(project_id, days=7):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT su.*, u.username, u.role as user_role, s.name as sprint_name
            FROM standup_updates su
            JOIN users u ON su.user_id = u.id
            LEFT JOIN sprints s ON su.sprint_id = s.id
            WHERE su.project_id = ? AND su.date >= date('now', '-' || ? || ' days')
            ORDER BY su.date DESC, su.created_at DESC
        """, (project_id, str(days)))
        updates = cursor.fetchall()
        conn.close()
        return updates

    @staticmethod
    def get_by_project(project_id, date=None):
        conn = get_db()
        cursor = conn.cursor()
        if date:
            cursor.execute("""
                SELECT su.*, u.username, u.role as user_role, s.name as sprint_name
                FROM standup_updates su
                JOIN users u ON su.user_id = u.id
                LEFT JOIN sprints s ON su.sprint_id = s.id
                WHERE su.project_id = ? AND su.date = ?
                ORDER BY su.created_at DESC
            """, (project_id, date))
        else:
            cursor.execute("""
                SELECT su.*, u.username, u.role as user_role, s.name as sprint_name
                FROM standup_updates su
                JOIN users u ON su.user_id = u.id
                LEFT JOIN sprints s ON su.sprint_id = s.id
                WHERE su.project_id = ?
                ORDER BY su.date DESC, su.created_at DESC
            """, (project_id,))
        updates = cursor.fetchall()
        conn.close()
        return updates

    @staticmethod
    def get_by_sprint(sprint_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT su.*, u.username, u.role as user_role
            FROM standup_updates su
            JOIN users u ON su.user_id = u.id
            WHERE su.sprint_id = ?
            ORDER BY su.date DESC, su.created_at DESC
        """, (sprint_id,))
        updates = cursor.fetchall()
        conn.close()
        return updates
