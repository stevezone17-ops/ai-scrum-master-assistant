import sqlite3
import os
import logging
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(DB_DIR, "database.db")
SCHEMA_PATH = os.path.join(os.path.dirname(DB_DIR), "schema.sql")

def get_db():
    """
    Returns the appropriate database connection/adapter based on DATABASE_BACKEND setting.
    - DATABASE_BACKEND=supabase: Uses Supabase PostgreSQL client via SupabaseDatabaseAdapter.
    - DATABASE_BACKEND=sqlite: Uses local SQLite database.
    """
    backend = os.environ.get('DATABASE_BACKEND', '').strip().lower()

    if not backend:
        url = os.environ.get('SUPABASE_URL', '').strip()
        key = os.environ.get('SUPABASE_KEY', '').strip()
        backend = 'supabase' if (url and key) else 'sqlite'

    if backend == 'supabase':
        from utils.supabase_client import get_supabase_client
        from database.supabase_adapter import SupabaseDatabaseAdapter

        client = get_supabase_client()
        if not client:
            raise RuntimeError("Database backend 'supabase' is configured, but Supabase credentials (SUPABASE_URL / SUPABASE_KEY) are missing or invalid.")
        return SupabaseDatabaseAdapter(client)
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def init_db():
    """Initialize SQLite database schema and seed initial demo data if empty."""
    os.makedirs(DB_DIR, exist_ok=True)

    # Always initialize SQLite if SQLite backend is active or missing
    backend = os.environ.get('DATABASE_BACKEND', '').strip().lower()
    if backend == 'supabase':
        logger.info("[+] Supabase PostgreSQL active as primary database backend.")
        return

    conn = get_db()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
        
    conn.commit()

    # Ensure comments column exists in standup_updates for existing databases
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(standup_updates)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'comments' not in columns:
        cursor.execute("ALTER TABLE standup_updates ADD COLUMN comments TEXT")
        conn.commit()
    
    # Check if users exist; if not, seed data
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    
    if count == 0:
        seed_demo_data(conn)
        
    conn.close()

def seed_demo_data(conn):
    cursor = conn.cursor()
    
    # Seed Users
    default_pass = generate_password_hash("password123")
    users_data = [
        ("scrummaster", "sm@agilescrum.io", default_pass, "Scrum Master"),
        ("developer1", "alex.rivera@agilescrum.io", default_pass, "Developer"),
        ("developer2", "sarah.chen@agilescrum.io", default_pass, "Developer"),
        ("developer3", "jordan.lee@agilescrum.io", default_pass, "Developer"),
        ("productowner", "po@agilescrum.io", default_pass, "Product Owner")
    ]
    
    cursor.executemany(
        "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
        users_data
    )
    
    # Seed Projects
    cursor.execute(
        """INSERT INTO projects (name, description, start_date, end_date, status, created_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("NextGen Enterprise Portal", "AI-driven customer relationship and agile task automation suite.", "2026-08-01", "2026-10-30", "Active", 1)
    )
    project_id = cursor.lastrowid
    
    cursor.execute(
        """INSERT INTO projects (name, description, start_date, end_date, status, created_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("FinTech Mobile App v2", "Next generation mobile banking frontend with biometric auth.", "2026-07-15", "2026-11-15", "Active", 5)
    )
    
    # Seed Team Members
    team_data = [
        (project_id, 1, "Scrum Master"),
        (project_id, 2, "Developer"),
        (project_id, 3, "Developer"),
        (project_id, 4, "Developer"),
        (project_id, 5, "Product Owner")
    ]
    cursor.executemany(
        "INSERT INTO team_members (project_id, user_id, role_in_project) VALUES (?, ?, ?)",
        team_data
    )
    
    # Seed Sprints
    sprints_data = [
        (project_id, "Sprint 1: Core Architecture", "Set up OAuth authentication and database schema", "2026-08-01", "2026-08-14", "Completed"),
        (project_id, "Sprint 2: Dashboard & AI Analytics", "Implement real-time velocity metrics and risk predictor", "2026-08-15", "2026-08-31", "Active"),
        (project_id, "Sprint 3: CI/CD Pipeline & Export", "Automate testing and report export tools", "2026-09-01", "2026-09-14", "Planned")
    ]
    cursor.executemany(
        "INSERT INTO sprints (project_id, name, goal, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, ?)",
        sprints_data
    )
    
    sprint_active_id = 2
    
    # Seed User Stories
    stories_data = [
        (project_id, 1, "As a user, I can log in with MFA", "Secure authentication mechanism", "High", 5, "Completed"),
        (project_id, sprint_active_id, "As a Scrum Master, I want AI sprint risk evaluation", "Analyze task completion rate and suggest workload adjustments", "Urgent", 8, "In Sprint"),
        (project_id, sprint_active_id, "As a Dev, I want an interactive Kanban board", "Drag and drop or update task status in real time", "High", 5, "In Sprint"),
        (project_id, sprint_active_id, "As a PO, I want team workload analytics", "Visual chart showing hour distribution across developers", "Medium", 3, "In Sprint"),
        (project_id, None, "As a user, I want custom notification settings", "Configure email and in-app alerts", "Low", 2, "Backlog")
    ]
    cursor.executemany(
        "INSERT INTO user_stories (project_id, sprint_id, title, description, priority, story_points, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        stories_data
    )
    
    # Seed Tasks
    tasks_data = [
        # Active Sprint tasks
        (project_id, sprint_active_id, 2, "Train Scikit-Learn Sprint Risk Classifier", "Build ML model for sprint completion prediction", 2, "High", 12.0, 10.0, "2026-08-28", "In Progress"),
        (project_id, sprint_active_id, 2, "Integrate AI Risk Card into Dashboard", "Display risk badges and recommendations", 1, "High", 6.0, 6.0, "2026-08-27", "Done"),
        (project_id, sprint_active_id, 3, "Implement Kanban Board HTML/JS Interface", "Kanban board columns with status drop target", 3, "Medium", 8.0, 6.5, "2026-08-29", "In Progress"),
        (project_id, sprint_active_id, 3, "Kanban API Route & Status Endpoint", "Flask endpoints for instant task status changes", 2, "Medium", 4.0, 4.0, "2026-08-26", "Done"),
        (project_id, sprint_active_id, 4, "Chart.js Team Capacity Graph", "Bar chart displaying estimated vs actual hours per developer", 4, "Low", 6.0, 2.0, "2026-08-30", "Testing"),
        (project_id, sprint_active_id, 2, "Fix Velocity Calculator Edge Cases", "Handle zero sprint scenario in calculation", 2, "Urgent", 5.0, 0.0, "2026-08-27", "To Do"),
        (project_id, sprint_active_id, None, "Database Performance Tuning", "Add indices to sprint and task FKs", 3, "Medium", 4.0, 0.0, "2026-08-31", "To Do"),
        
        # Sprint 1 completed tasks
        (project_id, 1, 1, "Design User Table & Schema", "SQLite table creation script", 1, "High", 5.0, 4.0, "2026-08-05", "Done"),
        (project_id, 1, 1, "Flask Password Hashing Service", "Integrate werkzeug.security generate_password_hash", 2, "High", 4.0, 4.0, "2026-08-08", "Done")
    ]
    cursor.executemany(
        """INSERT INTO tasks (project_id, sprint_id, story_id, title, description, assigned_to, priority, estimated_hours, actual_hours, due_date, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        tasks_data
    )
    
    # Seed Bugs
    bugs_data = [
        (project_id, sprint_active_id, "Kanban column state mismatch on slow network", "Task stays in old column until page reload if API returns timeout", "High", "In Progress", 2, 3),
        (project_id, sprint_active_id, "Chart tooltip formatting error for zero-hour developers", "Null value handling in Chart.js dataset", "Medium", "Open", 3, 4),
        (project_id, 1, "Session expiry redirect loses flash message", "Redirecting to /login loses query parameters", "Low", "Closed", 1, 2)
    ]
    cursor.executemany(
        "INSERT INTO bugs (project_id, sprint_id, title, description, severity, status, reported_by, assigned_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        bugs_data
    )
    
    # Seed Standup Updates
    standups_data = [
        (project_id, sprint_active_id, 2, "2026-08-27", "Completed Kanban API routes. Started training scikit-learn ML model.", "Finalize model evaluation metrics and integrate with Flask route.", "Awaiting test dataset validation."),
        (project_id, sprint_active_id, 3, "2026-08-27", "Designed UI layout for modern SaaS sidebar and card components.", "Build interactive drag-and-drop Kanban columns.", "None"),
        (project_id, sprint_active_id, 4, "2026-08-27", "Reviewed user stories and updated backlog story points.", "Create team workload summary chart using Chart.js.", "None")
    ]
    cursor.executemany(
        "INSERT INTO standup_updates (project_id, sprint_id, user_id, date, yesterday_work, today_plan, blockers) VALUES (?, ?, ?, ?, ?, ?, ?)",
        standups_data
    )
    
    conn.commit()
