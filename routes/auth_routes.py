from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models.user import User
import re

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles:
                flash(f"Access denied: '{session.get('role')}' role cannot perform this action.", "danger")
                return redirect(url_for('project.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('project.dashboard'))
        
    if request.method == 'POST':
        login_input = request.form.get('username', '').strip() or request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not login_input or not password:
            flash("Please enter your email/username and password.", "danger")
            return render_template('login.html')

        user = User.authenticate(login_input, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['email'] = user['email']
            flash(f"Welcome back, {user['username']}! Logged in as {user['role']}.", "success")
            return redirect(url_for('project.dashboard'))
        else:
            flash("Invalid email/username or password. Please try again.", "danger")

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('project.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        role = request.form.get('role', 'Developer').strip()

        # Validation Checks
        if not username or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template('register.html')

        if not re.match(EMAIL_REGEX, email):
            flash("Please enter a valid email address.", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter passwords.", "danger")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html')

        if role not in ['Scrum Master', 'Developer', 'Product Owner']:
            flash("Invalid role selected.", "danger")
            return render_template('register.html')

        # Create User
        user_id, error = User.create(username, email, password, role)
        if error:
            flash(error, "danger")
        else:
            flash("Registration successful! You can now log in with your credentials.", "success")
            return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))
