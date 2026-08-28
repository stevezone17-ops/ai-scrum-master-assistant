from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth_routes import login_required
from models.project import Project
from models.story import UserStory, VALID_PRIORITIES, VALID_POINTS, VALID_STATUSES
from models.sprint import Sprint

backlog_bp = Blueprint('backlog', __name__)

ALLOWED_ROLES = ['Scrum Master', 'Product Owner']


def _get_project_or_abort(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return None
    return project


def _get_team_devs(project_id):
    """Return all team members for a project (used in assignee dropdowns)."""
    members = Project.get_members(project_id)
    return members


@backlog_bp.route('/projects/<int:project_id>/backlog', methods=['GET', 'POST'])
@login_required
def backlog_view(project_id):
    project = _get_project_or_abort(project_id)
    if not project:
        return redirect(url_for('project.projects_list'))

    role = session.get('role')

    if request.method == 'POST':
        if role not in ALLOWED_ROLES:
            flash("Only Scrum Masters and Product Owners can create user stories.", "danger")
            return redirect(url_for('backlog.backlog_view', project_id=project_id))

        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Medium')
        story_points = request.form.get('story_points', type=int, default=3)
        status = request.form.get('status', 'Backlog')
        assigned_to = request.form.get('assigned_to', type=int)
        sprint_id = request.form.get('sprint_id', type=int)

        # Validation
        errors = []
        if not title:
            errors.append("User story title is required.")
        if priority not in VALID_PRIORITIES:
            errors.append(f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")
        if story_points not in VALID_POINTS:
            errors.append(f"Invalid story points. Must be one of: {', '.join(str(p) for p in VALID_POINTS)}")
        if status not in VALID_STATUSES:
            errors.append(f"Invalid status.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            UserStory.create(
                project_id, title, description, priority,
                story_points, status, assigned_to, sprint_id
            )
            flash(f"User story '{title}' added to Product Backlog.", "success")
            return redirect(url_for('backlog.backlog_view', project_id=project_id))

    sort_by = request.args.get('sort', 'priority')
    stories = UserStory.get_by_project(project_id, sort_by=sort_by)
    stats = UserStory.get_backlog_stats(project_id)
    sprints = Sprint.get_by_project(project_id)
    team_members = _get_team_devs(project_id)

    return render_template(
        'backlog.html',
        project=project,
        stories=stories,
        stats=stats,
        sprints=sprints,
        team_members=team_members,
        sort_by=sort_by,
        valid_priorities=VALID_PRIORITIES,
        valid_points=VALID_POINTS,
        valid_statuses=VALID_STATUSES,
    )


@backlog_bp.route('/stories/<int:story_id>/edit', methods=['POST'])
@login_required
def edit_story(story_id):
    story = UserStory.get_by_id(story_id)
    if not story:
        flash("User story not found.", "danger")
        return redirect(url_for('project.dashboard'))

    role = session.get('role')
    user_id = session.get('user_id')

    # Developers can only update status of their own assigned stories
    if role == 'Developer':
        if story['assigned_to'] != user_id:
            flash("You can only update the status of stories assigned to you.", "danger")
            return redirect(url_for('backlog.backlog_view', project_id=story['project_id']))
        status = request.form.get('status', story['status'])
        UserStory.update_status(story_id, status)
        flash("Story status updated.", "success")
        return redirect(url_for('backlog.backlog_view', project_id=story['project_id']))

    if role not in ALLOWED_ROLES:
        flash("You are not authorized to edit user stories.", "danger")
        return redirect(url_for('backlog.backlog_view', project_id=story['project_id']))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'Medium')
    story_points = request.form.get('story_points', type=int, default=3)
    status = request.form.get('status', 'Backlog')
    assigned_to = request.form.get('assigned_to', type=int)
    sprint_id = request.form.get('sprint_id', type=int)

    if not title:
        flash("User story title is required.", "danger")
        return redirect(url_for('backlog.backlog_view', project_id=story['project_id']))

    UserStory.update(story_id, title, description, priority, story_points,
                     status, assigned_to, sprint_id)
    flash(f"User story '{title}' updated successfully.", "success")
    return redirect(url_for('backlog.backlog_view', project_id=story['project_id']))


@backlog_bp.route('/stories/<int:story_id>/delete', methods=['POST'])
@login_required
def delete_story(story_id):
    story = UserStory.get_by_id(story_id)
    if not story:
        flash("User story not found.", "danger")
        return redirect(url_for('project.dashboard'))

    role = session.get('role')
    if role not in ALLOWED_ROLES:
        flash("Only Scrum Masters and Product Owners can delete user stories.", "danger")
        return redirect(url_for('backlog.backlog_view', project_id=story['project_id']))

    project_id = story['project_id']
    UserStory.delete(story_id)
    flash("User story removed from backlog.", "info")
    return redirect(url_for('backlog.backlog_view', project_id=project_id))
