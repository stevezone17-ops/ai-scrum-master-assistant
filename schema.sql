-- AI-Based Scrum Master Assistant Database Schema

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Scrum Master', 'Developer', 'Product Owner')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'Active' CHECK(status IN ('Planning', 'Active', 'Completed', 'On Hold')),
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role_in_project TEXT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    goal TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'Planned' CHECK(status IN ('Planned', 'Active', 'Completed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    sprint_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Urgent')),
    story_points INTEGER DEFAULT 3,
    status TEXT DEFAULT 'Backlog' CHECK(status IN ('Backlog', 'In Sprint', 'Completed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (sprint_id) REFERENCES sprints (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    sprint_id INTEGER,
    story_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    assigned_to INTEGER,
    priority TEXT DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Urgent')),
    estimated_hours REAL DEFAULT 0.0,
    actual_hours REAL DEFAULT 0.0,
    due_date DATE,
    status TEXT DEFAULT 'To Do' CHECK(status IN ('To Do', 'In Progress', 'Testing', 'Done')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (sprint_id) REFERENCES sprints (id) ON DELETE SET NULL,
    FOREIGN KEY (story_id) REFERENCES user_stories (id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS bugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    sprint_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'Medium' CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
    status TEXT DEFAULT 'Open' CHECK(status IN ('Open', 'In Progress', 'Resolved', 'Closed')),
    reported_by INTEGER NOT NULL,
    assigned_to INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (sprint_id) REFERENCES sprints (id) ON DELETE SET NULL,
    FOREIGN KEY (reported_by) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS standup_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    sprint_id INTEGER,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    yesterday_work TEXT NOT NULL,
    today_plan TEXT NOT NULL,
    blockers TEXT,
    comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (sprint_id) REFERENCES sprints (id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
