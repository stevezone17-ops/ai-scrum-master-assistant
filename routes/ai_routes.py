from flask import Blueprint, jsonify, request
from routes.auth_routes import login_required
from ai.analyzer import SprintAnalyzer
from models.project import Project

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/projects/<int:project_id>/ai-analysis')
@login_required
def get_ai_analysis(project_id):
    sprint_id = request.args.get('sprint_id', type=int)
    analysis = SprintAnalyzer.analyze_project_sprint(project_id, sprint_id)
    return jsonify(analysis)

@ai_bp.route('/projects/<int:project_id>/ai-recommendations')
@login_required
def get_ai_recommendations_endpoint(project_id):
    from ai.recommendations import get_recommendations
    recs = get_recommendations(project_id)
    return jsonify(recs)

@ai_bp.route('/projects/<int:project_id>/assistant')
@login_required
def assistant_view(project_id):
    from flask import session, render_template, redirect, url_for, flash
    user_id = session.get('user_id')
    user_role = session.get('role')

    user_projects = Project.get_user_projects(user_id, user_role)
    if not user_projects:
        flash("You do not have access to any projects.", "warning")
        return redirect(url_for('project.projects_list'))

    target_project = next((p for p in user_projects if p['id'] == project_id), None)
    if not target_project:
        flash("Access Denied: You are not authorized to view this project.", "danger")
        return redirect(url_for('project.dashboard'))

    # Load session-based conversation history
    chat_history_key = f"chat_history_{project_id}"
    history = session.get(chat_history_key, [])

    return render_template(
        'assistant.html',
        projects=user_projects,
        current_project=target_project,
        chat_history=history
    )

@ai_bp.route('/projects/<int:project_id>/assistant/chat', methods=['POST'])
@login_required
def assistant_chat(project_id):
    from flask import session
    from ai.assistant import ask_assistant

    user_id = session.get('user_id')
    user_role = session.get('role')

    data = request.get_json(silent=True) or request.form
    question = data.get('question', '').strip()

    if not question:
        return jsonify({
            'error': True,
            'response': 'Please provide a valid question.'
        }), 400

    result = ask_assistant(project_id, user_id, user_role, question)

    # Save to session history if valid authorization
    if not result.get('error') or result.get('response', '').startswith("⚠️"):
        chat_history_key = f"chat_history_{project_id}"
        history = session.get(chat_history_key, [])
        history.append({
            'question': question,
            'response': result.get('response'),
            'intent': result.get('intent')
        })
        # Keep last 20 messages per session
        session[chat_history_key] = history[-20:]

    return jsonify(result)

