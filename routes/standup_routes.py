from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import date
from routes.auth_routes import login_required
from models.project import Project
from models.sprint import Sprint
from models.standup import StandupUpdate
from ai.standup_analysis import (
    generate_team_standup_summary,
    analyze_single_standup
)

standup_bp = Blueprint('standup', __name__)

@standup_bp.route('/projects/<int:project_id>/standup', methods=['GET', 'POST'])
@login_required
def standup_view(project_id):
    user_id = session['user_id']
    user_role = session['role']

    # Project access & isolation check
    user_projects = Project.get_user_projects(user_id, user_role)
    if not any(p['id'] == project_id for p in user_projects):
        flash("You do not have access to this project's stand-up updates.", "danger")
        return redirect(url_for('project.dashboard'))

    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "danger")
        return redirect(url_for('project.projects_list'))

    active_sprint = Sprint.get_active_sprint(project_id)
    today_date = date.today().isoformat()

    if request.method == 'POST':
        yesterday_work = request.form.get('yesterday_work', '').strip()
        today_plan = request.form.get('today_plan', '').strip()
        blockers = request.form.get('blockers', 'None').strip()
        comments = request.form.get('comments', '').strip()

        if not yesterday_work or not today_plan:
            flash("Please fill in both 'Yesterday's Progress' and 'Today's Plan'.", "danger")
            return redirect(url_for('standup.standup_view', project_id=project_id))

        # Check for existing submission today to prevent duplicate daily submissions
        existing_standup = StandupUpdate.get_user_standup_for_date(project_id, user_id, today_date)

        if existing_standup:
            # Update existing record
            StandupUpdate.update(
                existing_standup['id'],
                yesterday_work,
                today_plan,
                blockers,
                comments,
                sprint_id=active_sprint['id'] if active_sprint else None
            )
            flash("Today's stand-up update has been updated successfully!", "success")
        else:
            # Create new record
            StandupUpdate.create(
                project_id,
                active_sprint['id'] if active_sprint else None,
                user_id,
                today_date,
                yesterday_work,
                today_plan,
                blockers,
                comments
            )
            flash("Daily stand-up update submitted successfully!", "success")

        return redirect(url_for('standup.standup_view', project_id=project_id))

    # GET Request Handling
    filter_date = request.args.get('date', today_date)
    raw_standups = StandupUpdate.get_by_project(project_id, date=filter_date if filter_date != 'all' else None)
    
    # Enrich standups with AI analysis
    analyzed_standups = [analyze_single_standup(dict(s)) for s in raw_standups]

    # Generate AI Team Standup Summary
    ai_team_summary = generate_team_standup_summary(project_id, target_date=today_date)

    # Fetch current user's today standup for prefilling form
    user_today_standup = StandupUpdate.get_user_standup_for_date(project_id, user_id, today_date)
    user_history = StandupUpdate.get_user_standup_history(project_id, user_id)
    analyzed_history = [analyze_single_standup(dict(h)) for h in user_history]

    return render_template(
        'standup.html',
        project=project,
        active_sprint=active_sprint,
        standups=analyzed_standups,
        ai_team_summary=ai_team_summary,
        user_today_standup=dict(user_today_standup) if user_today_standup else None,
        user_history=analyzed_history,
        today_date=today_date,
        filter_date=filter_date
    )
