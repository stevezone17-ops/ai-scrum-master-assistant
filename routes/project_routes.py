from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from routes.auth_routes import login_required, role_required
from models.project import Project
from models.user import User
from models.sprint import Sprint
from models.task import Task
from models.bug import Bug
from models.story import UserStory
from ai.analyzer import SprintAnalyzer
from datetime import datetime

project_bp = Blueprint('project', __name__)

@project_bp.route('/')
@project_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    role = session['role']
    projects = Project.get_user_projects(user_id, role)
    db_counts = Project.get_dashboard_counts()

    selected_project_id = request.args.get('project_id', type=int)
    if not selected_project_id and projects:
        selected_project_id = projects[0]['id']

    current_project = None
    if selected_project_id:
        current_project = Project.get_by_id(selected_project_id)

    # Initial defaults
    active_sprint = None
    active_sprint_stats = None
    velocity_history = []
    sprint_db_stats = {'completed_sprints': 0, 'total_sprints': 0, 'average_velocity': 0}
    backlog_stats = {'total_stories': 0, 'completed_stories': 0, 'total_points': 0, 'completed_points': 0}
    tasks = []
    bugs = []
    team_members = []
    workload = []
    days_remaining = 0

    if selected_project_id:
        active_sprint = Sprint.get_active_sprint(selected_project_id)
        if active_sprint:
            active_sprint_stats = Sprint.get_sprint_stats(active_sprint['id'])
            sprint_dict = dict(active_sprint)
            if sprint_dict.get('end_date'):
                try:
                    end_dt = datetime.strptime(str(sprint_dict['end_date']), '%Y-%m-%d')
                    delta = (end_dt - datetime.now()).days
                    days_remaining = max(0, delta)
                except ValueError:
                    days_remaining = 0

        velocity_history = Sprint.get_velocity_history(selected_project_id)
        sprint_db_stats = Sprint.get_dashboard_sprint_stats(selected_project_id)
        tasks_raw = Task.get_by_project(selected_project_id)
        tasks = [dict(t) for t in tasks_raw]
        bugs = Bug.get_by_project(selected_project_id)
        team_members = Project.get_members(selected_project_id)
        workload_raw = Task.get_workload(selected_project_id)
        workload = [dict(w) for w in workload_raw]
        backlog_stats = UserStory.get_backlog_stats(selected_project_id)

    total_tasks = len(tasks)
    todo_count = sum(1 for t in tasks if t['status'] == 'To Do')
    in_progress_count = sum(1 for t in tasks if t['status'] == 'In Progress')
    testing_count = sum(1 for t in tasks if t['status'] == 'Testing')
    completed_tasks = sum(1 for t in tasks if t['status'] == 'Done')
    pending_tasks = total_tasks - completed_tasks

    today_str = datetime.now().strftime('%Y-%m-%d')
    overdue_tasks_list = [t for t in tasks if t['status'] != 'Done' and t.get('due_date') and str(t['due_date']) < today_str]
    overdue_count = len(overdue_tasks_list)
    overdue_tasks_list.sort(key=lambda x: str(x['due_date']))

    total_estimated_hours = round(sum(t.get('estimated_hours') or 0 for t in tasks), 1)
    total_actual_hours = round(sum(t.get('actual_hours') or 0 for t in tasks), 1)

    sprint_completion_pct = active_sprint_stats['progress_pct'] if (active_sprint_stats and active_sprint_stats['total_points'] > 0) else (round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0)

    # Health Indicator Calculation (Requirement 6)
    overloaded_devs = sum(1 for w in workload if w.get('workload_pct', 0) > 100)
    if overdue_count >= 3 or overloaded_devs >= 2:
        health_status = 'CRITICAL'
        health_badge_class = 'badge-urgent'
        health_explanation = f"Project is CRITICAL because {overdue_count} task(s) are overdue and {overloaded_devs} developer(s) exceed 100% capacity."
    elif overdue_count > 0 or overloaded_devs > 0 or (active_sprint_stats and active_sprint_stats['progress_pct'] < 40 and days_remaining < 3):
        health_status = 'AT RISK'
        health_badge_class = 'badge-high'
        health_explanation = f"Project is AT RISK because {overdue_count} task(s) are overdue and sprint completion pace is lagging."
    else:
        health_status = 'HEALTHY'
        health_badge_class = 'badge-active'
        health_explanation = "Project is HEALTHY with zero overdue tasks and steady development velocity."

    # Developer Specific Context (Requirement 10)
    dev_assigned_tasks = [t for t in tasks if t.get('assigned_to') == user_id]
    dev_pending_tasks = [t for t in dev_assigned_tasks if t['status'] != 'Done']
    dev_completed_tasks = [t for t in dev_assigned_tasks if t['status'] == 'Done']
    dev_overdue_tasks = [t for t in dev_assigned_tasks if t.get('is_overdue')]
    dev_workload_info = next((w for w in workload if w.get('user_id') == user_id), None)

    # Recent Activity Feed
    recent_activities = []
    for t in sorted(tasks, key=lambda x: str(x.get('created_at', '')), reverse=True)[:5]:
        recent_activities.append({
            'type': 'task',
            'title': t['title'],
            'action': f"Status is '{t['status']}'",
            'user': t.get('assignee_name') or 'Unassigned',
            'time': t.get('created_at', '')[:10] if t.get('created_at') else ''
        })

    # AI Sprint Risk Assessment (Step 12A), AI Recommendations (Step 12B) & Stand-up Summary (Step 12C)
    ai_risk_assessment = None
    ai_recommendations = None
    ai_standup_summary = None
    if selected_project_id:
        try:
            from ai.risk_service import get_ai_sprint_risk_assessment
            ai_risk_assessment = get_ai_sprint_risk_assessment(selected_project_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to compute AI risk assessment: {e}")

        try:
            from ai.recommendations import get_recommendations
            ai_recommendations = get_recommendations(selected_project_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to compute AI recommendations: {e}")

        try:
            from ai.standup_analysis import generate_team_standup_summary
            ai_standup_summary = generate_team_standup_summary(selected_project_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to compute AI stand-up summary: {e}")

    return render_template(
        'dashboard.html',
        projects=projects,
        current_project=current_project,
        active_sprint=active_sprint,
        active_sprint_stats=active_sprint_stats,
        days_remaining=days_remaining,
        velocity_history=velocity_history,
        sprint_db_stats=sprint_db_stats,
        total_projects=db_counts['total_projects'],
        active_projects=db_counts['active_projects'],
        planning_projects=db_counts['planning_projects'],
        completed_projects=db_counts['completed_projects'],
        on_hold_projects=db_counts['on_hold_projects'],
        total_tasks=total_tasks,
        todo_count=todo_count,
        in_progress_count=in_progress_count,
        testing_count=testing_count,
        completed_tasks=completed_tasks,
        pending_tasks=pending_tasks,
        overdue_count=overdue_count,
        overdue_tasks_list=overdue_tasks_list[:5],
        total_estimated_hours=total_estimated_hours,
        total_actual_hours=total_actual_hours,
        sprint_completion_pct=sprint_completion_pct,
        team_members=team_members,
        workload=workload,
        bugs_count=len(bugs),
        backlog_stats=backlog_stats,
        health_status=health_status,
        health_badge_class=health_badge_class,
        health_explanation=health_explanation,
        dev_assigned_tasks=dev_assigned_tasks,
        dev_pending_tasks=dev_pending_tasks,
        dev_completed_tasks=dev_completed_tasks,
        dev_overdue_tasks=dev_overdue_tasks,
        dev_workload_info=dev_workload_info,
        recent_activities=recent_activities,
        ai_risk_assessment=ai_risk_assessment,
        ai_recommendations=ai_recommendations,
        ai_standup_summary=ai_standup_summary
    )

@project_bp.route('/projects', methods=['GET', 'POST'])
@login_required
def projects_list():
    user_id = session['user_id']
    role = session['role']

    if request.method == 'POST':
        # Ensure only Scrum Master can create projects
        if role != 'Scrum Master':
            flash("Only Scrum Masters are authorized to create new projects.", "danger")
            return redirect(url_for('project.projects_list'))

        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        status = request.form.get('status', 'Active')

        if not name or not start_date or not end_date:
            flash("Project name, start date, and end date are required.", "danger")
        elif end_date < start_date:
            flash("End date cannot be earlier than start date.", "danger")
        else:
            project_id = Project.create(name, description, start_date, end_date, status, user_id)
            flash(f"Project '{name}' created successfully!", "success")
            return redirect(url_for('project.project_detail', project_id=project_id))

    projects = Project.get_user_projects(user_id, role)
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('projects.html', projects=projects, today=today)

@project_bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found or invalid ID.", "danger")
        return redirect(url_for('project.projects_list'))

    stats = Project.get_project_stats(project_id)
    members = Project.get_members(project_id)
    sprints = Sprint.get_by_project(project_id)
    tasks = Task.get_by_project(project_id)
    all_users = User.get_all()

    return render_template(
        'project_details.html',
        project=project,
        stats=stats,
        members=members,
        sprints=sprints,
        tasks=tasks,
        all_users=all_users
    )

@project_bp.route('/projects/<int:project_id>/edit', methods=['POST'])
@login_required
def edit_project(project_id):
    if session.get('role') != 'Scrum Master':
        flash("Only Scrum Masters are authorized to edit projects.", "danger")
        return redirect(url_for('project.project_detail', project_id=project_id))

    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    status = request.form.get('status')

    if not name or not start_date or not end_date:
        flash("Project name, start date, and end date are required.", "danger")
    elif end_date < start_date:
        flash("End date cannot be earlier than start date.", "danger")
    else:
        Project.update(project_id, name, description, start_date, end_date, status)
        flash(f"Project '{name}' updated successfully.", "success")

    return redirect(url_for('project.project_detail', project_id=project_id))

@project_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    if session.get('role') != 'Scrum Master':
        flash("Only Scrum Masters are authorized to delete projects.", "danger")
        return redirect(url_for('project.project_detail', project_id=project_id))

    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('project.projects_list'))

    Project.delete(project_id)
    flash(f"Project '{project['name']}' deleted successfully.", "info")
    return redirect(url_for('project.projects_list'))

@project_bp.route('/projects/<int:project_id>/team', methods=['GET', 'POST'])
@login_required
def team_management(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('project.projects_list'))

    if request.method == 'POST':
        if session.get('role') != 'Scrum Master':
            flash("Only Scrum Masters can add team members.", "danger")
            return redirect(url_for('project.team_management', project_id=project_id))

        user_id = request.form.get('user_id', type=int)
        role_in_project = request.form.get('role_in_project', 'Developer')
        
        success, error = Project.add_member(project_id, user_id, role_in_project)
        if success:
            flash("Team member added successfully.", "success")
        else:
            flash(error or "Could not add team member.", "danger")
        return redirect(url_for('project.team_management', project_id=project_id))

    members = Project.get_members(project_id)
    all_users = User.get_all()
    workload = Task.get_workload(project_id)
    team_stats = Project.get_dashboard_counts(project_id=project_id)

    return render_template(
        'team.html',
        project=project,
        members=members,
        all_users=all_users,
        workload=workload,
        team_stats=team_stats
    )

@project_bp.route('/projects/<int:project_id>/team/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_team_member(project_id, user_id):
    if session.get('role') != 'Scrum Master':
        flash("Only Scrum Masters can remove team members.", "danger")
        return redirect(url_for('project.team_management', project_id=project_id))

    Project.remove_member(project_id, user_id)
    flash("Team member removed from project.", "info")
    return redirect(url_for('project.team_management', project_id=project_id))
