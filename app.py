import os
from flask import Flask, render_template, session, jsonify
from database.db import init_db
from datetime import date
from utils.supabase_client import test_supabase_connection

# Import Blueprints
from routes.auth_routes import auth_bp
from routes.project_routes import project_bp
from routes.backlog_routes import backlog_bp
from routes.sprint_routes import sprint_bp
from routes.task_routes import task_bp
from routes.standup_routes import standup_bp
from routes.ai_routes import ai_bp
from routes.report_routes import report_bp

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'scrum_master_ai_secret_key_2026_super_secure')

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(project_bp)
app.register_blueprint(backlog_bp)
app.register_blueprint(sprint_bp)
app.register_blueprint(task_bp)
app.register_blueprint(standup_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(report_bp)

@app.route('/health/supabase')
def supabase_health_check():
    """Health check route verifying Supabase connectivity without exposing secrets."""
    from utils.supabase_client import test_supabase_connection
    success, message = test_supabase_connection()
    status_code = 200 if success else 503
    return jsonify({
        'supabase': 'Connected' if success else 'Disconnected',
        'message': message
    }), status_code

@app.context_processor
def inject_global_vars():
    """Inject useful context variables into all Jinja templates."""
    return {
        'today': date.today().isoformat(),
        'current_user': {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role'),
            'email': session.get('email')
        }
    }

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_title="Page Not Found", error_message="The page or resource you requested could not be found."), 404

@app.errorhandler(403)
def access_forbidden(e):
    return render_template('error.html', error_code=403, error_title="Access Forbidden", error_message="You do not have authorization or permissions to access this project resource."), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_code=500, error_title="Server Issue", error_message="An unexpected server condition occurred. Please try again or return to the dashboard."), 500

if __name__ == '__main__':
    print("[+] Initializing AI Scrum Master Assistant Database...")
    init_db()
    print("[+] System Ready! Launching Web Server on http://127.0.0.1:5000")
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
