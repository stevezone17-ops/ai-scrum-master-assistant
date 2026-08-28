from database.db import get_db

class Project:
    @staticmethod
    def create(name, description, start_date, end_date, status, created_by):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO projects (name, description, start_date, end_date, status, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, description, start_date, end_date, status, created_by)
        )
        project_id = cursor.lastrowid
        # Automatically add creator as team member
        cursor.execute(
            "INSERT INTO team_members (project_id, user_id, role_in_project) VALUES (?, ?, ?)",
            (project_id, created_by, "Scrum Master")
        )
        conn.commit()
        conn.close()
        return project_id

    @staticmethod
    def get_all():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, u.username as creator_name,
                   (SELECT COUNT(*) FROM team_members tm WHERE tm.project_id = p.id) as member_count,
                   (SELECT COUNT(*) FROM sprints s WHERE s.project_id = p.id) as sprint_count,
                   (SELECT COUNT(*) FROM user_stories us WHERE us.project_id = p.id) as story_count,
                   (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as task_count,
                   (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'Done') as completed_task_count
            FROM projects p
            LEFT JOIN users u ON p.created_by = u.id
            ORDER BY p.created_at DESC
        """)
        projects = cursor.fetchall()
        conn.close()
        return projects

    @staticmethod
    def get_user_projects(user_id, role):
        """Return projects accessible by user role."""
        conn = get_db()
        cursor = conn.cursor()
        if role == 'Scrum Master':
            cursor.execute("""
                SELECT p.*, u.username as creator_name,
                       (SELECT COUNT(*) FROM team_members tm WHERE tm.project_id = p.id) as member_count,
                       (SELECT COUNT(*) FROM sprints s WHERE s.project_id = p.id) as sprint_count,
                       (SELECT COUNT(*) FROM user_stories us WHERE us.project_id = p.id) as story_count,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as task_count,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'Done') as completed_task_count
                FROM projects p
                LEFT JOIN users u ON p.created_by = u.id
                ORDER BY p.created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT DISTINCT p.*, u.username as creator_name,
                       (SELECT COUNT(*) FROM team_members tm WHERE tm.project_id = p.id) as member_count,
                       (SELECT COUNT(*) FROM sprints s WHERE s.project_id = p.id) as sprint_count,
                       (SELECT COUNT(*) FROM user_stories us WHERE us.project_id = p.id) as story_count,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as task_count,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'Done') as completed_task_count
                FROM projects p
                LEFT JOIN users u ON p.created_by = u.id
                JOIN team_members tm ON p.id = tm.project_id
                WHERE tm.user_id = ? OR p.created_by = ?
                ORDER BY p.created_at DESC
            """, (user_id, user_id))
        projects = cursor.fetchall()
        conn.close()
        return projects

    @staticmethod
    def get_by_id(project_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, u.username as creator_name
            FROM projects p
            LEFT JOIN users u ON p.created_by = u.id
            WHERE p.id = ?
        """, (project_id,))
        project = cursor.fetchone()
        conn.close()
        return project

    @staticmethod
    def get_project_stats(project_id):
        """Calculate member, sprint, story, and task statistics for a project."""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM team_members WHERE project_id = ?", (project_id,))
        member_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sprints WHERE project_id = ?", (project_id,))
        sprint_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_stories WHERE project_id = ?", (project_id,))
        story_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,))
        total_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE project_id = ? AND status = 'Done'", (project_id,))
        completed_tasks = cursor.fetchone()[0]

        pending_tasks = total_tasks - completed_tasks
        progress_pct = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

        conn.close()
        return {
            'member_count': member_count,
            'sprint_count': sprint_count,
            'story_count': story_count,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'progress_pct': progress_pct
        }

    @staticmethod
    def get_dashboard_counts(project_id=None):
        """Retrieve real project and team metrics for dashboard."""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM projects")
        total_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
        active_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Planning'")
        planning_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'Completed'")
        completed_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'On Hold'")
        on_hold_projects = cursor.fetchone()[0]

        # Team Member breakdown query
        if project_id:
            cursor.execute("SELECT COUNT(*) FROM team_members WHERE project_id = ?", (project_id,))
            total_team_members = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM team_members WHERE project_id = ? AND role_in_project = 'Developer'", (project_id,))
            developer_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM team_members WHERE project_id = ? AND role_in_project = 'Scrum Master'", (project_id,))
            scrum_master_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM team_members WHERE project_id = ? AND role_in_project = 'Product Owner'", (project_id,))
            product_owner_count = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM team_members")
            total_team_members = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM team_members WHERE role_in_project = 'Developer'")
            developer_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM team_members WHERE role_in_project = 'Scrum Master'")
            scrum_master_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM team_members WHERE role_in_project = 'Product Owner'")
            product_owner_count = cursor.fetchone()[0]

        # Calculate average workload percentage across assigned developer tasks
        workload_query = """
            SELECT COALESCE(SUM(t.estimated_hours), 0.0) as total_est
            FROM team_members tm
            LEFT JOIN tasks t ON t.assigned_to = tm.user_id AND t.project_id = tm.project_id
        """
        if project_id:
            workload_query += " WHERE tm.project_id = ?"
            cursor.execute(workload_query, (project_id,))
        else:
            cursor.execute(workload_query)

        tot_est = cursor.fetchone()[0]
        base_capacity = (developer_count or 1) * 40.0
        avg_workload_pct = round((tot_est / base_capacity) * 100, 1)

        conn.close()
        return {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'planning_projects': planning_projects,
            'completed_projects': completed_projects,
            'on_hold_projects': on_hold_projects,
            'total_team_members': total_team_members,
            'developer_count': developer_count,
            'scrum_master_count': scrum_master_count,
            'product_owner_count': product_owner_count,
            'avg_workload_pct': avg_workload_pct
        }

    @staticmethod
    def update(project_id, name, description, start_date, end_date, status):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE projects
            SET name = ?, description = ?, start_date = ?, end_date = ?, status = ?
            WHERE id = ?
        """, (name, description, start_date, end_date, status, project_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete(project_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_members(project_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tm.*, u.username, u.email, u.role as system_role,
                   (SELECT COUNT(*) FROM tasks t WHERE t.assigned_to = u.id AND t.project_id = tm.project_id) as total_tasks,
                   (SELECT COUNT(*) FROM tasks t WHERE t.assigned_to = u.id AND t.project_id = tm.project_id AND t.status = 'Done') as completed_tasks,
                   (SELECT COUNT(*) FROM tasks t WHERE t.assigned_to = u.id AND t.project_id = tm.project_id AND t.status != 'Done') as pending_tasks,
                   COALESCE((SELECT SUM(t.estimated_hours) FROM tasks t WHERE t.assigned_to = u.id AND t.project_id = tm.project_id), 0.0) as assigned_hours
            FROM team_members tm
            JOIN users u ON tm.user_id = u.id
            WHERE tm.project_id = ?
            ORDER BY u.username ASC
        """, (project_id,))
        rows = cursor.fetchall()
        members = []
        for r in rows:
            m = dict(r)
            assigned_hours = m['assigned_hours'] or 0.0
            available_hours = 40.0
            workload_pct = round((assigned_hours / available_hours) * 100, 1)
            m['assigned_hours'] = assigned_hours
            m['available_hours'] = available_hours
            m['workload_pct'] = workload_pct
            members.append(m)
        conn.close()
        return members

    @staticmethod
    def add_member(project_id, user_id, role_in_project):
        conn = get_db()
        cursor = conn.cursor()
        # Verify user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return False, "Selected user does not exist."

        # Check if already added
        cursor.execute("SELECT id FROM team_members WHERE project_id = ? AND user_id = ?", (project_id, user_id))
        if cursor.fetchone():
            conn.close()
            return False, "User is already a team member in this project."

        try:
            cursor.execute(
                "INSERT INTO team_members (project_id, user_id, role_in_project) VALUES (?, ?, ?)",
                (project_id, user_id, role_in_project)
            )
            conn.commit()
            conn.close()
            return True, None
        except Exception as e:
            conn.close()
            return False, f"Could not add team member: {str(e)}"

    @staticmethod
    def remove_member(project_id, user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM team_members WHERE project_id = ? AND user_id = ?", (project_id, user_id))
        conn.commit()
        conn.close()
