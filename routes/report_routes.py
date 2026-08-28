"""
routes/report_routes.py
========================
Step 13: Project and Sprint Reports Controller

Provides real database-driven project and sprint reporting, PDF export,
AI evaluation integration, and strict project isolation security.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from routes.auth_routes import login_required
from models.project import Project
from models.sprint import Sprint
from models.task import Task
from models.story import UserStory
from models.bug import Bug
from models.standup import StandupUpdate
from database.db import get_db
from ai.risk_service import get_ai_sprint_risk_assessment
from ai.recommendations import get_recommendations
from ai.standup_analysis import generate_team_standup_summary
from utils.pdf_generator import generate_sprint_report_pdf, generate_project_report_pdf

report_bp = Blueprint('report', __name__)


def _check_project_access(project_id: int, user_id: int, user_role: str):
    user_projects = Project.get_user_projects(user_id, user_role)
    if not any(p['id'] == project_id for p in user_projects):
        return None
    return Project.get_by_id(project_id)


def _calculate_sprint_report_data(project_id: int, sprint_id: int):
    raw_sprint = Sprint.get_by_id(sprint_id)
    if not raw_sprint:
        return None, None
    
    current_sprint = dict(raw_sprint)
    if current_sprint.get('project_id') != project_id:
        return None, None

    sprint = dict(current_sprint)
    tasks = [dict(t) for t in Task.get_by_sprint(sprint_id)]
    
    completed_tasks = [t for t in tasks if t.get('status') == 'Done']
    incomplete_tasks = [t for t in tasks if t.get('status') != 'Done']
    pending_tasks = [t for t in tasks if t.get('status') in ['To Do', 'In Progress', 'Testing']]
    overdue_tasks = [t for t in tasks if t.get('is_overdue') == 1]

    # Calculate hours
    est_hours = sum(t.get('estimated_hours', 0) or 0 for t in tasks)
    act_hours = sum(t.get('actual_hours', 0) or 0 for t in tasks)

    # Get User Stories in Sprint
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stories WHERE sprint_id = ?", (sprint_id,))
    stories = [dict(s) for s in cursor.fetchall()]
    conn.close()

    completed_stories = [s for s in stories if s.get('status') == 'Completed']
    total_sp = sum(s.get('story_points', 0) or 0 for s in stories)
    completed_sp = sum(s.get('story_points', 0) or 0 for s in completed_stories)
    velocity = completed_sp

    tot_tasks = len(tasks)
    comp_tasks = len(completed_tasks)
    task_pct = round(comp_tasks / tot_tasks * 100, 1) if tot_tasks > 0 else 0.0

    tot_stories = len(stories)
    comp_stories_cnt = len(completed_stories)
    sp_pct = round(completed_sp / total_sp * 100, 1) if total_sp > 0 else 0.0

    metrics = {
        'total_tasks': tot_tasks,
        'completed_tasks': comp_tasks,
        'incomplete_tasks': len(incomplete_tasks),
        'pending_tasks': len(pending_tasks),
        'overdue_tasks': len(overdue_tasks),
        'task_pct': task_pct,
        'total_stories': tot_stories,
        'completed_stories': comp_stories_cnt,
        'total_sp': total_sp,
        'completed_sp': completed_sp,
        'sp_pct': sp_pct,
        'velocity': velocity,
        'estimated_hours': est_hours,
        'actual_hours': act_hours
    }

    # AI Data
    ai_risk = get_ai_sprint_risk_assessment(project_id)
    recs_data = get_recommendations(project_id)
    recs = recs_data.get('recommendations', [])

    standup_summary = generate_team_standup_summary(project_id)
    blockers = []
    if standup_summary and not standup_summary.get('error'):
        for b in standup_summary.get('high_priority_blockers', []):
            blockers.append(f"{b['developer']}: {b['blocker']}")

    return sprint, {
        'metrics': metrics,
        'tasks': tasks,
        'completed_tasks': completed_tasks,
        'incomplete_tasks': incomplete_tasks,
        'overdue_tasks': overdue_tasks,
        'ai_risk': ai_risk,
        'recommendations': recs,
        'blockers': blockers
    }


def _calculate_project_report_data(project_id: int):
    conn = get_db()
    cursor = conn.cursor()

    # Team size
    cursor.execute("SELECT COUNT(*) FROM team_members WHERE project_id = ?", (project_id,))
    team_size = cursor.fetchone()[0]

    # Sprints
    cursor.execute("SELECT * FROM sprints WHERE project_id = ?", (project_id,))
    sprints = [dict(s) for s in cursor.fetchall()]
    total_sprints = len(sprints)
    completed_sprints = sum(1 for s in sprints if s.get('status') == 'Completed')

    # Stories
    cursor.execute("SELECT * FROM user_stories WHERE project_id = ?", (project_id,))
    stories = [dict(s) for s in cursor.fetchall()]
    total_stories = len(stories)
    total_sp = sum(s.get('story_points', 0) or 0 for s in stories)

    # Tasks
    all_tasks = [dict(t) for t in Task.get_by_project(project_id)]
    total_tasks = len(all_tasks)
    completed_tasks = sum(1 for t in all_tasks if t.get('status') == 'Done')
    overdue_tasks = sum(1 for t in all_tasks if t.get('is_overdue') == 1)

    conn.close()

    progress_pct = round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0.0

    # Health evaluation
    ai_risk = get_ai_sprint_risk_assessment(project_id)
    risk_level = ai_risk.get('risk_level') or ai_risk.get('predicted_risk') or 'LOW' if ai_risk else 'LOW'

    if overdue_tasks > 3 or risk_level == 'HIGH':
        health = "At Risk"
    elif overdue_tasks > 0 or risk_level == 'MEDIUM':
        health = "Needs Attention"
    else:
        health = "Healthy"

    recs_data = get_recommendations(project_id)
    recs = recs_data.get('recommendations', [])

    metrics = {
        'team_size': team_size,
        'total_sprints': total_sprints,
        'completed_sprints': completed_sprints,
        'total_stories': total_stories,
        'total_sp': total_sp,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'progress_pct': progress_pct,
        'health': health
    }

    return metrics, ai_risk, recs


@report_bp.route('/projects/<int:project_id>/reports')
@login_required
def reports_view(project_id):
    user_id = session.get('user_id')
    user_role = session.get('role')

    project = _check_project_access(project_id, user_id, user_role)
    if not project:
        flash("Access Denied: You do not have permission to view reports for this project.", "danger")
        return redirect(url_for('project.projects_list'))

    report_type = request.args.get('report_type', 'sprint')
    sprints = Sprint.get_by_project(project_id)

    sprint_id = request.args.get('sprint_id', type=int)
    if not sprint_id:
        active_sprint = Sprint.get_active_sprint(project_id)
        sprint_id = active_sprint['id'] if active_sprint else (sprints[0]['id'] if sprints else None)

    sprint_data = None
    project_metrics = None
    ai_risk = None
    recs = []

    if report_type == 'project':
        project_metrics, ai_risk, recs = _calculate_project_report_data(project_id)
    else:
        if sprint_id:
            sprint, sprint_data = _calculate_sprint_report_data(project_id, sprint_id)
            current_sprint = sprint
        else:
            current_sprint = None

    current_sprint = Sprint.get_by_id(sprint_id) if sprint_id else None

    return render_template(
        'reports.html',
        project=project,
        sprints=sprints,
        current_sprint=current_sprint,
        report_type=report_type,
        sprint_data=sprint_data,
        project_metrics=project_metrics,
        ai_risk=ai_risk,
        recommendations=recs
    )


@report_bp.route('/projects/<int:project_id>/reports/sprint/<int:sprint_id>')
@login_required
def dedicated_sprint_report(project_id, sprint_id):
    user_id = session.get('user_id')
    user_role = session.get('role')

    project = _check_project_access(project_id, user_id, user_role)
    if not project:
        flash("Access Denied: You do not have permission to view reports for this project.", "danger")
        return redirect(url_for('project.projects_list'))

    sprint_row = Sprint.get_by_id(sprint_id)
    sprint = dict(sprint_row) if sprint_row else None
    if not sprint or sprint.get('project_id') != project_id:
        flash("Sprint not found.", "warning")
        return redirect(url_for('report.reports_view', project_id=project_id))

    return redirect(url_for('report.reports_view', project_id=project_id, report_type='sprint', sprint_id=sprint_id))


@report_bp.route('/projects/<int:project_id>/reports/export/pdf')
@login_required
def export_pdf_report(project_id):
    user_id = session.get('user_id')
    user_role = session.get('role')

    project = _check_project_access(project_id, user_id, user_role)
    if not project:
        flash("Access Denied: You do not have permission to export reports for this project.", "danger")
        return redirect(url_for('project.projects_list'))

    report_type = request.args.get('report_type', 'sprint')
    sprint_id = request.args.get('sprint_id', type=int)

    if report_type == 'project':
        project_metrics, ai_risk, recs = _calculate_project_report_data(project_id)
        pdf_bytes = generate_project_report_pdf(project, project_metrics, ai_risk, recs)
        filename = f"Project_Report_{project['name'].replace(' ', '_')}.pdf"
    else:
        sprints = Sprint.get_by_project(project_id)
        if not sprint_id:
            active_sprint = Sprint.get_active_sprint(project_id)
            sprint_id = active_sprint['id'] if active_sprint else (sprints[0]['id'] if sprints else None)

        if not sprint_id:
            flash("No sprint available for PDF export.", "warning")
            return redirect(url_for('report.reports_view', project_id=project_id))

        sprint, sprint_data = _calculate_sprint_report_data(project_id, sprint_id)
        if not sprint or not sprint_data:
            flash("Invalid sprint for export.", "danger")
            return redirect(url_for('report.reports_view', project_id=project_id))

        pdf_bytes = generate_sprint_report_pdf(
            project,
            sprint,
            sprint_data['metrics'],
            sprint_data['ai_risk'],
            sprint_data['recommendations'],
            sprint_data['blockers']
        )
        filename = f"Sprint_Report_{sprint['name'].replace(' ', '_')}.pdf"

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )
