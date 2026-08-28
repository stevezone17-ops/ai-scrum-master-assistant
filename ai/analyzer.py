import pandas as pd
import numpy as np
from datetime import datetime, date
from database.db import get_db
from ai.predictor import predictor

class SprintAnalyzer:
    @staticmethod
    def analyze_project_sprint(project_id, sprint_id=None):
        conn = get_db()
        
        # 1. Fetch Sprint Info
        if not sprint_id:
            sprint_query = "SELECT * FROM sprints WHERE project_id = ? AND status = 'Active' ORDER BY id DESC LIMIT 1"
            sprint = conn.execute(sprint_query, (project_id,)).fetchone()
            if not sprint:
                sprint = conn.execute("SELECT * FROM sprints WHERE project_id = ? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()
        else:
            sprint = conn.execute("SELECT * FROM sprints WHERE id = ?", (sprint_id,)).fetchone()

        if not sprint:
            conn.close()
            return {
                'has_sprint': False,
                'message': 'No sprint found for this project.'
            }

        sprint_id = sprint['id']

        # 2. Load Tasks into Pandas DataFrame
        tasks_df = pd.read_sql_query(
            "SELECT * FROM tasks WHERE sprint_id = ?",
            conn,
            params=(sprint_id,)
        )

        # 3. Load Bugs into Pandas DataFrame
        bugs_df = pd.read_sql_query(
            "SELECT * FROM bugs WHERE sprint_id = ?",
            conn,
            params=(sprint_id,)
        )

        # 4. Load Team Workload into Pandas DataFrame
        workload_df = pd.read_sql_query(
            """SELECT u.username, COUNT(t.id) as task_count,
                      SUM(t.estimated_hours) as est_hours,
                      SUM(t.actual_hours) as act_hours
               FROM team_members tm
               JOIN users u ON tm.user_id = u.id
               LEFT JOIN tasks t ON t.assigned_to = u.id AND t.sprint_id = ?
               WHERE tm.project_id = ?
               GROUP BY u.username""",
            conn,
            params=(sprint_id, project_id)
        )

        conn.close()

        # Calculate metrics using Pandas
        total_tasks = len(tasks_df)
        completed_tasks = len(tasks_df[tasks_df['status'] == 'Done']) if total_tasks > 0 else 0
        pending_tasks = total_tasks - completed_tasks
        
        # Calculate overdue tasks
        today_str = date.today().isoformat()
        if total_tasks > 0 and 'due_date' in tasks_df.columns:
            overdue_df = tasks_df[
                (tasks_df['status'] != 'Done') &
                (tasks_df['due_date'].notna()) &
                (tasks_df['due_date'] < today_str)
            ]
            overdue_tasks = len(overdue_df)
        else:
            overdue_tasks = 0

        # Calculate Days Remaining
        try:
            start = datetime.strptime(sprint['start_date'], '%Y-%m-%d').date()
            end = datetime.strptime(sprint['end_date'], '%Y-%m-%d').date()
            today = date.today()
            
            days_total = max((end - start).days, 1)
            days_remaining = (end - today).days
            days_remaining = max(days_remaining, 0)
        except Exception:
            days_total = 14
            days_remaining = 5

        # Workload metrics
        if not workload_df.empty and 'task_count' in workload_df.columns:
            max_dev_tasks = int(workload_df['task_count'].max()) if len(workload_df) > 0 else 0
            avg_dev_tasks = float(workload_df['task_count'].mean()) if len(workload_df) > 0 else 0.0
        else:
            max_dev_tasks = 0
            avg_dev_tasks = 0.0

        open_bugs = len(bugs_df[bugs_df['status'] != 'Closed']) if not bugs_df.empty else 0

        # Compute Sprint Velocity (Historical vs Current)
        current_velocity = completed_tasks * 3.5 # story points equivalent estimate
        previous_velocity = 15.0 # default baseline velocity

        metrics = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'overdue_tasks': overdue_tasks,
            'days_total': days_total,
            'days_remaining': days_remaining,
            'max_dev_tasks': max_dev_tasks,
            'avg_dev_tasks': avg_dev_tasks,
            'open_bugs': open_bugs,
            'previous_velocity': previous_velocity,
            'current_velocity': current_velocity
        }

        # Call Scikit-Learn Predictor
        ai_result = predictor.predict_sprint_risk(metrics)

        # Workload breakdown formatted for response & Chart.js
        workload_list = []
        if not workload_df.empty:
            workload_df['est_hours'] = workload_df['est_hours'].fillna(0)
            workload_df['act_hours'] = workload_df['act_hours'].fillna(0)
            workload_list = workload_df.to_dict(orient='records')

        return {
            'has_sprint': True,
            'sprint': dict(sprint),
            'metrics': metrics,
            'ai_analysis': ai_result,
            'workload': workload_list
        }
