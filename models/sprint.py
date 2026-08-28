from database.db import get_db

VALID_STATUSES = ['Planned', 'Active', 'Completed']

class Sprint:
    @staticmethod
    def create(project_id, name, goal, start_date, end_date, status="Planned"):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO sprints (project_id, name, goal, start_date, end_date, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, name, goal, start_date, end_date, status)
        )
        sprint_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return sprint_id

    @staticmethod
    def get_by_project(project_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*,
                   (SELECT COUNT(*) FROM user_stories us WHERE us.sprint_id = s.id) as total_stories,
                   (SELECT COALESCE(SUM(us.story_points), 0) FROM user_stories us WHERE us.sprint_id = s.id) as total_points,
                   (SELECT COUNT(*) FROM user_stories us WHERE us.sprint_id = s.id AND us.status = 'Done') as completed_stories,
                   (SELECT COALESCE(SUM(us.story_points), 0) FROM user_stories us WHERE us.sprint_id = s.id AND us.status = 'Done') as completed_points,
                   (SELECT COUNT(*) FROM tasks t WHERE t.sprint_id = s.id) as total_tasks,
                   (SELECT COUNT(*) FROM tasks t WHERE t.sprint_id = s.id AND t.status = 'Done') as completed_tasks
            FROM sprints s
            WHERE s.project_id = ?
            ORDER BY
                CASE s.status WHEN 'Active' THEN 0 WHEN 'Planned' THEN 1 WHEN 'Completed' THEN 2 END,
                s.start_date DESC
        """, (project_id,))
        sprints = cursor.fetchall()
        conn.close()
        return sprints

    @staticmethod
    def get_active_sprint(project_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*
            FROM sprints s
            WHERE s.project_id = ? AND s.status = 'Active'
            LIMIT 1
        """, (project_id,))
        sprint = cursor.fetchone()
        if not sprint:
            cursor.execute("""
                SELECT s.* FROM sprints s WHERE s.project_id = ? ORDER BY s.id DESC LIMIT 1
            """, (project_id,))
            sprint = cursor.fetchone()
        conn.close()
        return sprint

    @staticmethod
    def get_by_id(sprint_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,))
        sprint = cursor.fetchone()
        conn.close()
        return sprint

    @staticmethod
    def get_sprint_stats(sprint_id):
        """Compute story-point-level statistics for a sprint."""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user_stories WHERE sprint_id = ?", (sprint_id,))
        total_stories = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(story_points), 0) FROM user_stories WHERE sprint_id = ?", (sprint_id,))
        total_points = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_stories WHERE sprint_id = ? AND status = 'Done'", (sprint_id,))
        completed_stories = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(story_points), 0) FROM user_stories WHERE sprint_id = ? AND status = 'Done'", (sprint_id,))
        completed_points = cursor.fetchone()[0]

        pending_stories = total_stories - completed_stories
        remaining_points = total_points - completed_points
        progress_pct = round((completed_points / total_points * 100), 1) if total_points > 0 else 0.0

        conn.close()
        return {
            'total_stories': total_stories,
            'total_points': total_points,
            'completed_stories': completed_stories,
            'completed_points': completed_points,
            'pending_stories': pending_stories,
            'remaining_points': remaining_points,
            'progress_pct': progress_pct,
        }

    @staticmethod
    def has_active_sprint(project_id, exclude_sprint_id=None):
        """Return True if project already has an active sprint."""
        conn = get_db()
        cursor = conn.cursor()
        if exclude_sprint_id:
            cursor.execute("SELECT id FROM sprints WHERE project_id = ? AND status = 'Active' AND id != ?",
                           (project_id, exclude_sprint_id))
        else:
            cursor.execute("SELECT id FROM sprints WHERE project_id = ? AND status = 'Active'", (project_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    @staticmethod
    def start_sprint(sprint_id):
        """Transition a Planned sprint to Active (only if no other Active sprint exists)."""
        sprint = Sprint.get_by_id(sprint_id)
        if not sprint:
            return False, "Sprint not found."
        if sprint['status'] == 'Active':
            return False, "Sprint is already active."
        if sprint['status'] == 'Completed':
            return False, "Cannot restart a completed sprint."
        if Sprint.has_active_sprint(sprint['project_id'], exclude_sprint_id=sprint_id):
            return False, "Another sprint is already active in this project. Complete it first."

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE sprints SET status = 'Active' WHERE id = ?", (sprint_id,))
        conn.commit()
        conn.close()
        return True, None

    @staticmethod
    def complete_sprint(sprint_id):
        """Transition an Active sprint to Completed and compute velocity."""
        sprint = Sprint.get_by_id(sprint_id)
        if not sprint:
            return False, "Sprint not found.", None
        if sprint['status'] != 'Active':
            return False, "Only active sprints can be completed.", None

        stats = Sprint.get_sprint_stats(sprint_id)
        velocity = stats['completed_points']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE sprints SET status = 'Completed' WHERE id = ?", (sprint_id,))
        # Incomplete stories: unlink from sprint (return to backlog) but don't delete
        cursor.execute("""
            UPDATE user_stories SET sprint_id = NULL, status = 'Backlog'
            WHERE sprint_id = ? AND status != 'Done'
        """, (sprint_id,))
        conn.commit()
        conn.close()

        return True, None, velocity

    @staticmethod
    def update(sprint_id, name, goal, start_date, end_date, status):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sprints
            SET name = ?, goal = ?, start_date = ?, end_date = ?, status = ?
            WHERE id = ?
        """, (name, goal, start_date, end_date, status, sprint_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(sprint_id):
        conn = get_db()
        cursor = conn.cursor()
        # Return stories to backlog before deleting sprint
        cursor.execute("UPDATE user_stories SET sprint_id = NULL WHERE sprint_id = ?", (sprint_id,))
        cursor.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_velocity_history(project_id, limit=5):
        """Return completed sprint velocities for velocity trend display."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.name,
                   COALESCE(SUM(CASE WHEN us.status = 'Done' THEN us.story_points ELSE 0 END), 0) as velocity
            FROM sprints s
            LEFT JOIN user_stories us ON us.sprint_id = s.id
            WHERE s.project_id = ? AND s.status = 'Completed'
            GROUP BY s.id, s.name
            ORDER BY s.end_date DESC
            LIMIT ?
        """, (project_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_sprint_stories(sprint_id):
        """Return all user stories assigned to a sprint."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT us.*, u.username as assignee_name
            FROM user_stories us
            LEFT JOIN users u ON us.assigned_to = u.id
            WHERE us.sprint_id = ?
            ORDER BY CASE us.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 END
        """, (sprint_id,))
        stories = cursor.fetchall()
        conn.close()
        return stories

    @staticmethod
    def get_available_stories(project_id, sprint_id):
        """Return backlog stories not yet assigned to any Active/Planned sprint."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT us.*, u.username as assignee_name
            FROM user_stories us
            LEFT JOIN users u ON us.assigned_to = u.id
            WHERE us.project_id = ?
              AND (us.sprint_id IS NULL OR us.sprint_id = ?)
              AND us.status != 'Done'
            ORDER BY CASE us.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 END
        """, (project_id, sprint_id))
        stories = cursor.fetchall()
        conn.close()
        return stories

    @staticmethod
    def add_story(sprint_id, story_id):
        """Assign a backlog story to a sprint."""
        conn = get_db()
        cursor = conn.cursor()
        # Check if story is already in another active/planned sprint
        cursor.execute("""
            SELECT s.id, s.name FROM user_stories us
            JOIN sprints s ON us.sprint_id = s.id
            WHERE us.id = ? AND us.sprint_id IS NOT NULL AND us.sprint_id != ? AND s.status IN ('Active', 'Planned')
        """, (story_id, sprint_id))
        conflict = cursor.fetchone()
        if conflict:
            conn.close()
            return False, f"Story is already in sprint '{conflict['name']}'."

        cursor.execute("UPDATE user_stories SET sprint_id = ?, status = 'Ready' WHERE id = ?",
                       (sprint_id, story_id))
        conn.commit()
        conn.close()
        return True, None

    @staticmethod
    def remove_story(sprint_id, story_id):
        """Remove a story from a sprint and return it to the product backlog."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE user_stories SET sprint_id = NULL, status = 'Backlog' WHERE id = ? AND sprint_id = ?",
                       (story_id, sprint_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_metrics(sprint_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'Done' THEN 1 ELSE 0 END) as completed_tasks,
                SUM(CASE WHEN status = 'To Do' THEN 1 ELSE 0 END) as todo_tasks,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress_tasks,
                SUM(CASE WHEN status = 'Testing' THEN 1 ELSE 0 END) as testing_tasks,
                SUM(estimated_hours) as total_est_hours,
                SUM(actual_hours) as total_act_hours
            FROM tasks
            WHERE sprint_id = ?
        """, (sprint_id,))
        metrics = cursor.fetchone()
        conn.close()
        return metrics

    @staticmethod
    def get_dashboard_sprint_stats(project_id):
        """Compute sprint-level dashboard metrics."""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM sprints WHERE project_id = ? AND status = 'Completed'", (project_id,))
        completed_sprints = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sprints WHERE project_id = ?", (project_id,))
        total_sprints = cursor.fetchone()[0]

        conn.close()
        return {
            'completed_sprints': completed_sprints,
            'total_sprints': total_sprints,
        }
