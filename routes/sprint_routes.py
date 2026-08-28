from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth_routes import login_required
from models.project import Project
from models.sprint import Sprint
from models.story import UserStory

sprint_bp = Blueprint('sprint', __name__)


def _require_scrum_master(redirect_url):
    if session.get('role') != 'Scrum Master':
        flash("Only Scrum Masters can perform this action.", "danger")
        return redirect(redirect_url)
    return None


@sprint_bp.route('/projects/<int:project_id>/sprints', methods=['GET', 'POST'])
@login_required
def sprints_view(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('project.projects_list'))

    if request.method == 'POST':
        deny = _require_scrum_master(url_for('sprint.sprints_view', project_id=project_id))
        if deny:
            return deny

        name = request.form.get('name', '').strip()
        goal = request.form.get('goal', '').strip()
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if not name or not goal:
            flash("Sprint name and sprint goal are required.", "danger")
        elif not start_date or not end_date:
            flash("Start date and end date are required.", "danger")
        elif end_date < start_date:
            flash("End date cannot be before start date.", "danger")
        else:
            sprint_id = Sprint.create(project_id, name, goal, start_date, end_date, "Planned")
            flash(f"Sprint '{name}' created successfully!", "success")
            return redirect(url_for('sprint.sprint_detail', sprint_id=sprint_id))

    sprints = Sprint.get_by_project(project_id)
    velocity_history = Sprint.get_velocity_history(project_id)

    return render_template(
        'sprints.html',
        project=project,
        sprints=sprints,
        velocity_history=velocity_history,
    )


@sprint_bp.route('/sprints/<int:sprint_id>')
@login_required
def sprint_detail(sprint_id):
    sprint = Sprint.get_by_id(sprint_id)
    if not sprint:
        flash("Sprint not found.", "danger")
        return redirect(url_for('project.dashboard'))

    project = Project.get_by_id(sprint['project_id'])
    stats = Sprint.get_sprint_stats(sprint_id)
    task_stats = Task.get_task_stats(sprint['project_id'], sprint_id=sprint_id)
    sprint_stories = Sprint.get_sprint_stories(sprint_id)
    available_stories = Sprint.get_available_stories(sprint['project_id'], sprint_id)

    return render_template(
        'sprint_detail.html',
        project=project,
        sprint=sprint,
        stats=stats,
        task_stats=task_stats,
        sprint_stories=sprint_stories,
        available_stories=available_stories,
    )


@sprint_bp.route('/sprints/<int:sprint_id>/edit', methods=['POST'])
@login_required
def edit_sprint(sprint_id):
    sprint = Sprint.get_by_id(sprint_id)
    if not sprint:
        flash("Sprint not found.", "danger")
        return redirect(url_for('project.dashboard'))

    deny = _require_scrum_master(url_for('sprint.sprint_detail', sprint_id=sprint_id))
    if deny:
        return deny

    name = request.form.get('name', '').strip()
    goal = request.form.get('goal', '').strip()
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    status = request.form.get('status', sprint['status'])

    if not name or not start_date or not end_date:
        flash("Sprint name, start date, and end date are required.", "danger")
    elif end_date < start_date:
        flash("End date cannot be before start date.", "danger")
    else:
        Sprint.update(sprint_id, name, goal, start_date, end_date, status)
        flash(f"Sprint '{name}' updated.", "success")

    return redirect(url_for('sprint.sprint_detail', sprint_id=sprint_id))


@sprint_bp.route('/sprints/<int:sprint_id>/delete', methods=['POST'])
@login_required
def delete_sprint(sprint_id):
    sprint = Sprint.get_by_id(sprint_id)
    if not sprint:
        flash("Sprint not found.", "danger")
        return redirect(url_for('project.dashboard'))

    deny = _require_scrum_master(url_for('sprint.sprint_detail', sprint_id=sprint_id))
    if deny:
        return deny

    project_id = sprint['project_id']
    Sprint.delete(sprint_id)
    flash("Sprint deleted. Stories returned to backlog.", "info")
    return redirect(url_for('sprint.sprints_view', project_id=project_id))


@sprint_bp.route('/sprints/<int:sprint_id>/start', methods=['POST'])
@login_required
def start_sprint(sprint_id):
    sprint = Sprint.get_by_id(sprint_id)
    if not sprint:
        flash("Sprint not found.", "danger")
        return redirect(url_for('project.dashboard'))

    deny = _require_scrum_master(url_for('sprint.sprint_detail', sprint_id=sprint_id))
    if deny:
        return deny

    success, error = Sprint.start_sprint(sprint_id)
    if success:
        flash(f"Sprint '{sprint['name']}' is now ACTIVE!", "success")
    else:
        flash(error, "danger")

    return redirect(url_for('sprint.sprint_detail', sprint_id=sprint_id))


@sprint_bp.route('/sprints/<int:sprint_id>/complete', methods=['POST'])
@login_required
def complete_sprint(sprint_id):
    sprint = Sprint.get_by_id(sprint_id)
    if not sprint:
        flash("Sprint not found.", "danger")
        return redirect(url_for('project.dashboard'))

    deny = _require_scrum_master(url_for('sprint.sprint_detail', sprint_id=sprint_id))
    if deny:
        return deny

    success, error, velocity = Sprint.complete_sprint(sprint_id)
    if success:
        flash(f"Sprint '{sprint['name']}' completed! Velocity: {velocity} story points. Incomplete stories returned to backlog.", "success")
    else:
        flash(error, "danger")

    return redirect(url_for('sprint.sprint_detail', sprint_id=sprint_id))


@sprint_bp.route('/sprints/<int:sprint_id>/add_story', methods=['POST'])
@login_required
def add_story_to_sprint(sprint_id):
    deny = _require_scrum_master(url_for('sprint.sprint_detail', sprint_id=sprint_id))
    if deny:
        return deny

    story_id = request.form.get('story_id', type=int)
    if not story_id:
        flash("Please select a user story.", "danger")
    else:
        success, error = Sprint.add_story(sprint_id, story_id)
        if success:
            flash("User story added to sprint.", "success")
        else:
            flash(error, "danger")

    return redirect(url_for('sprint.sprint_detail', sprint_id=sprint_id))


@sprint_bp.route('/sprints/<int:sprint_id>/remove_story/<int:story_id>', methods=['POST'])
@login_required
def remove_story_from_sprint(sprint_id, story_id):
    deny = _require_scrum_master(url_for('sprint.sprint_detail', sprint_id=sprint_id))
    if deny:
        return deny

    Sprint.remove_story(sprint_id, story_id)
    flash("Story removed from sprint and returned to Product Backlog.", "info")
    return redirect(url_for('sprint.sprint_detail', sprint_id=sprint_id))
