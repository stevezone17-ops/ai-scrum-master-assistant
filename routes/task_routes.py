from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from routes.auth_routes import login_required
from models.project import Project
from models.sprint import Sprint
from models.story import UserStory
from models.task import Task
from models.user import User

task_bp = Blueprint('task', __name__)


@task_bp.route('/projects/<int:project_id>/tasks')
@login_required
def tasks_view(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('project.projects_list'))

    user_id = session.get('user_id')
    role = session.get('role')

    filter_assigned = request.args.get('assigned_to', type=int)
    sprint_id = request.args.get('sprint_id', type=int)

    # Developers can toggle viewing only their tasks
    if role == 'Developer' and request.args.get('my_tasks') == '1':
        filter_assigned = user_id

    tasks = Task.get_by_project(project_id, assigned_to=filter_assigned)
    if sprint_id:
        tasks = [t for t in tasks if t['sprint_id'] == sprint_id]

    task_stats = Task.get_task_stats(project_id, sprint_id=sprint_id)
    workload = Task.get_workload(project_id, sprint_id=sprint_id)
    team_members = Project.get_members(project_id)
    user_stories = UserStory.get_by_project(project_id)
    sprints = Sprint.get_by_project(project_id)

    return render_template(
        'tasks.html',
        project=project,
        tasks=tasks,
        task_stats=task_stats,
        workload=workload,
        team_members=team_members,
        user_stories=user_stories,
        sprints=sprints,
        selected_sprint_id=sprint_id,
        filter_assigned=filter_assigned
    )


@task_bp.route('/projects/<int:project_id>/kanban')
@login_required
def kanban_board(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('project.projects_list'))

    sprint_id = request.args.get('sprint_id', type=int)
    sprints = Sprint.get_by_project(project_id)

    if sprint_id and sprint_id > 0:
        tasks = Task.get_by_sprint(sprint_id)
        current_sprint = Sprint.get_by_id(sprint_id)
    else:
        tasks = Task.get_by_project(project_id)
        current_sprint = None

    task_stats = Task.get_task_stats(project_id, sprint_id=sprint_id if (sprint_id and sprint_id > 0) else None)

    kanban_tasks = {
        'To Do': [t for t in tasks if t['status'] == 'To Do'],
        'In Progress': [t for t in tasks if t['status'] == 'In Progress'],
        'Testing': [t for t in tasks if t['status'] == 'Testing'],
        'Done': [t for t in tasks if t['status'] == 'Done']
    }

    team_members = Project.get_members(project_id)
    user_stories = UserStory.get_by_project(project_id)

    return render_template(
        'kanban.html',
        project=project,
        sprints=sprints,
        current_sprint=current_sprint,
        selected_sprint_id=sprint_id or 0,
        kanban_tasks=kanban_tasks,
        task_stats=task_stats,
        team_members=team_members,
        user_stories=user_stories
    )


@task_bp.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for('project.dashboard'))

    project = Project.get_by_id(task['project_id'])
    user_story = UserStory.get_by_id(task['story_id']) if task['story_id'] else None
    return render_template('task_detail.html', task=task, project=project, user_story=user_story)


@task_bp.route('/tasks/create', methods=['POST'])
@login_required
def create_task():
    role = session.get('role')
    if role not in ['Scrum Master', 'Product Owner']:
        flash("Only Scrum Masters and Product Owners can create tasks.", "danger")
        return redirect(request.referrer or url_for('project.dashboard'))

    project_id = request.form.get('project_id', type=int)
    sprint_id = request.form.get('sprint_id', type=int)
    story_id = request.form.get('story_id', type=int)
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    assigned_to = request.form.get('assigned_to', type=int)
    priority = request.form.get('priority', 'Medium')
    estimated_hours = request.form.get('estimated_hours', type=float, default=0.0)
    actual_hours = request.form.get('actual_hours', type=float, default=0.0)
    due_date = request.form.get('due_date')
    status = request.form.get('status', 'To Do')

    # Validations
    if not title:
        flash("Task title is required.", "danger")
    elif not project_id:
        flash("Project ID is missing.", "danger")
    elif estimated_hours <= 0:
        flash("Estimated hours must be greater than 0.", "danger")
    else:
        # Validate assigned developer belongs to project team
        if assigned_to:
            team_members = Project.get_members(project_id)
            member_ids = [m['id'] for m in team_members]
            if assigned_to not in member_ids:
                flash("Selected developer does not belong to this project team.", "danger")
                return redirect(request.referrer or url_for('task.tasks_view', project_id=project_id))

        # Validate story belongs to current project
        if story_id:
            story = UserStory.get_by_id(story_id)
            if not story or story['project_id'] != project_id:
                flash("Selected user story does not belong to this project.", "danger")
                return redirect(request.referrer or url_for('task.tasks_view', project_id=project_id))
            if story['sprint_id'] and not sprint_id:
                sprint_id = story['sprint_id']

        Task.create(
            project_id, sprint_id, story_id, title, description,
            assigned_to, priority, estimated_hours, actual_hours, due_date, status
        )
        flash(f"Task '{title}' created successfully.", "success")

    redirect_url = request.referrer or url_for('task.tasks_view', project_id=project_id)
    return redirect(redirect_url)


@task_bp.route('/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def edit_task(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for('project.dashboard'))

    role = session.get('role')
    user_id = session.get('user_id')

    # Developer role check: can only update their own assigned tasks
    if role == 'Developer':
        if task['assigned_to'] != user_id:
            flash("You can only edit tasks assigned to you.", "danger")
            return redirect(request.referrer or url_for('task.tasks_view', project_id=task['project_id']))

        actual_hours = request.form.get('actual_hours', type=float, default=task['actual_hours'])
        status = request.form.get('status', task['status'])
        Task.update_actual_hours_and_status(task_id, actual_hours, status)
        flash("Task progress updated.", "success")
        return redirect(request.referrer or url_for('task.tasks_view', project_id=task['project_id']))

    # Scrum Master / PO edit
    title = request.form.get('title', task['title']).strip()
    description = request.form.get('description', task['description']).strip()
    assigned_to = request.form.get('assigned_to', type=int)
    priority = request.form.get('priority', task['priority'])
    estimated_hours = request.form.get('estimated_hours', type=float, default=task['estimated_hours'])
    actual_hours = request.form.get('actual_hours', type=float, default=task['actual_hours'])
    due_date = request.form.get('due_date', task['due_date'])
    status = request.form.get('status', task['status'])
    sprint_id = request.form.get('sprint_id', type=int)
    story_id = request.form.get('story_id', type=int)

    if estimated_hours <= 0:
        flash("Estimated hours must be greater than 0.", "danger")
        return redirect(request.referrer or url_for('task.tasks_view', project_id=task['project_id']))

    if assigned_to:
        team_members = Project.get_members(task['project_id'])
        member_ids = [m['id'] for m in team_members]
        if assigned_to not in member_ids:
            flash("Assigned user must belong to the project team.", "danger")
            return redirect(request.referrer or url_for('task.tasks_view', project_id=task['project_id']))

    Task.update(
        task_id, title, description, assigned_to, priority,
        estimated_hours, actual_hours, due_date, status, sprint_id, story_id
    )
    flash("Task updated successfully.", "success")
    redirect_url = request.referrer or url_for('task.tasks_view', project_id=task['project_id'])
    return redirect(redirect_url)


@task_bp.route('/tasks/<int:task_id>/update_progress', methods=['POST'])
@login_required
def update_task_progress(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for('project.dashboard'))

    role = session.get('role')
    user_id = session.get('user_id')

    if role == 'Developer' and task['assigned_to'] != user_id:
        flash("You can only update actual hours and status for your assigned tasks.", "danger")
        return redirect(request.referrer or url_for('task.tasks_view', project_id=task['project_id']))

    actual_hours = request.form.get('actual_hours', type=float, default=task['actual_hours'])
    status = request.form.get('status', task['status'])

    Task.update_actual_hours_and_status(task_id, actual_hours, status)
    flash(f"Updated task '{task['title']}': Status='{status}', Actual Hours={actual_hours}h.", "success")
    return redirect(request.referrer or url_for('task.tasks_view', project_id=task['project_id']))


@task_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def update_task_status(task_id):
    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    data = request.get_json(silent=True) or request.form
    new_status = data.get('status')
    if not new_status or new_status not in ['To Do', 'In Progress', 'Testing', 'Done']:
        return jsonify({'success': False, 'error': 'Invalid task status'}), 400

    role = session.get('role')
    user_id = session.get('user_id')

    # RBAC Enforcement (Requirement 4)
    if role == 'Product Owner':
        return jsonify({'success': False, 'error': 'Product Owners have read-only access to Kanban tasks'}), 403
    elif role == 'Developer':
        if task['assigned_to'] != user_id:
            return jsonify({'success': False, 'error': 'Developers can only move tasks assigned to themselves'}), 403

    # Project Security Validation (Requirement 7)
    req_project_id = data.get('project_id')
    if req_project_id:
        try:
            if int(req_project_id) != task['project_id']:
                return jsonify({'success': False, 'error': 'Project security validation failed'}), 403
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid project identifier'}), 400

    Task.update_status(task_id, new_status)
    updated_stats = Task.get_task_stats(task['project_id'], sprint_id=task['sprint_id'])

    return jsonify({
        'success': True,
        'task_id': task_id,
        'old_status': task['status'],
        'new_status': new_status,
        'task_stats': updated_stats
    })


@task_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    role = session.get('role')
    if role != 'Scrum Master':
        flash("Only Scrum Masters can delete tasks.", "danger")
        return redirect(request.referrer or url_for('project.dashboard'))

    task = Task.get_by_id(task_id)
    if task:
        project_id = task['project_id']
        Task.delete(task_id)
        flash("Task deleted.", "info")
        return redirect(request.referrer or url_for('task.tasks_view', project_id=project_id))

    return redirect(url_for('project.dashboard'))
