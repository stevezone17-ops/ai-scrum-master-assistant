# AI-Based Scrum Master Assistant for Agile Software Project Management

> A comprehensive, web-based Agile software project management application featuring Machine Learning Sprint Risk Evaluation (Scikit-Learn), Rule-Based Recommendations, NLP Daily Stand-up Analysis, an interactive AI Scrum Master Assistant, and ReportLab Server-Side PDF Export.

---

## 📋 Table of Contents
1. [Project Overview](#-project-overview)
2. [Problem Statement & Objectives](#-problem-statement--objectives)
3. [Agile & Scrum Concepts Used](#-agile--scrum-concepts-used)
4. [System Architecture](#-system-architecture)
5. [Technology Stack](#-technology-stack)
6. [Database Design & Schema](#-database-design--schema)
7. [AI & Machine Learning Layer](#-ai--machine-learning-layer)
   - [ML Sprint Risk Prediction](#1-ml-sprint-risk-prediction)
   - [AI Recommendations Engine](#2-ai-recommendations-engine)
   - [NLP Daily Stand-up Analysis](#3-nlp-daily-stand-up-analysis)
   - [AI Scrum Master Assistant](#4-ai-scrum-master-assistant)
8. [Reporting & PDF Export](#-reporting--pdf-export)
9. [User Roles & Permission Matrix](#-user-roles--permission-matrix)
10. [Security & Data Isolation](#-security--data-isolation)
11. [Directory Structure](#-directory-structure)
12. [Installation & Setup Instructions](#-installation--setup-instructions)
13. [Default Demo Credentials](#-default-demo-credentials)
14. [Testing & Verification Results](#-testing--verification-results)
15. [Limitations & Future Enhancements](#-limitations--future-enhancements)

---

## 📌 Project Overview

The **AI-Based Scrum Master Assistant** is an intelligent, full-stack web application designed to help software development teams adopt Agile methodologies effectively. By integrating traditional Scrum artifacts (Product Backlog, Sprints, Tasks, Kanban Board, Daily Stand-ups) with an automated AI analytical layer, the platform identifies sprint delay risks, detects development blockers, recommends actionable resolution steps, and answers natural-language project queries.

---

## 🎯 Problem Statement & Objectives

### Problem Statement
Agile software development teams frequently face sprint scope creep, unaddressed technical impediments, unrealistic developer workload distribution, and sudden sprint deadline failures. Traditional project management software simply records tasks without providing proactive insights or early warnings to the Scrum Master.

### Project Objectives
- **Automate Sprint Risk Prediction**: Leverage Machine Learning (`RandomForestClassifier`) to predict sprint failure risk (`LOW`, `MEDIUM`, `HIGH`) based on live sprint progress metrics.
- **Provide Actionable Recommendations**: Implement a rule-based engine that converts metric variances into prioritized Scrum Master recommendations.
- **Automate Daily Stand-up Analysis**: Process daily Scrum updates using NLP text matching to highlight impediments and detect repeated blockers across consecutive days.
- **Interactive AI Assistant**: Allow project members to ask natural language questions about sprint status, team workload, blockers, and overdue tasks.
- **Server-Side PDF Reporting**: Generate downloadable, professional PDF project and sprint status reports directly from real-time database records.

---

## 🔄 Agile & Scrum Concepts Used

- **Product Backlog & User Stories**: Structured requirements framed as user stories with Fibonacci Story Point estimation (1, 2, 3, 5, 8, 13) and priority levels (`Low`, `Medium`, `High`, `Urgent`).
- **Sprint Management**: Time-boxed development cycles with defined sprint goals, target start/end dates, status tracking (`Planned`, `Active`, `Completed`), and velocity calculation.
- **Task Breakdown & Kanban Board**: Task division under user stories with 4-column drag-and-drop workflow (`To Do`, `In Progress`, `Testing`, `Done`).
- **Daily Stand-up Meetings**: Developer updates recording work completed yesterday, planned work for today, and technical blockers.
- **Sprint Velocity & Burndown Tracking**: Historical tracking of story points completed per sprint to establish team velocity baselines.

---

## 🏗️ System Architecture

```
                                  +-------------------+
                                  |    User Browser   |
                                  +---------+---------+
                                            |
                                            v (HTTP / REST AJAX)
                                  +-------------------+
                                  |   Flask Backend   |
                                  |  (routes/ & app)  |
                                  +----+----+----+----+
                                       |    |    |
           +---------------------------+    |    +--------------------------+
           |                                |                               |
           v                                v                               v
+-------------------+             +-------------------+           +-------------------+
|  SQLite3 Database |             |    AI/ML Layer    |           | ReportLab PDF Engine|
| (database/db.py)  |             |      (ai/)        |           |(utils/pdf_generator)|
+-------------------+             +---------+---------+           +-------------------+
                                            |
                       +--------------------+--------------------+
                       |                    |                    |
                       v                    v                    v
              +-----------------+  +------------------+  +------------------+
              | ML Risk Model   |  | Recommendations  |  | Stand-up NLP     |
              | (RandomForest)  |  | Engine           |  | Analyzer         |
              +-----------------+  +------------------+  +------------------+
                                            |
                                            v
                                   +------------------+
                                   | AI Assistant     |
                                   | Query Engine     |
                                   +------------------+
```

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, Vanilla CSS3 (Custom Dark Theme Design System), JavaScript (ES6+ AJAX), Chart.js, FontAwesome 6
- **Backend Framework**: Python 3.12, Flask 3.x, Werkzeug (Password Hashing & Routing)
- **Database**: SQLite3
- **Data Processing**: Pandas 2.x, NumPy 1.24+
- **Machine Learning**: Scikit-Learn 1.3+ (`RandomForestClassifier`, `StandardScaler`), Joblib
- **Document Export**: ReportLab 4.x (Server-Side PDF Generator)
- **Testing Framework**: Python `unittest`

---

## 🗄️ Database Design & Schema

The database consists of 8 interconnected tables with enforced SQLite foreign keys:

1. **`users`**: User accounts storing `username`, `email`, `password_hash`, `role` (`Scrum Master`, `Product Owner`, `Developer`), and `created_at`.
2. **`projects`**: Project details storing `name`, `description`, `start_date`, `end_date`, `status` (`Active`, `Planning`, `Completed`, `On Hold`), and `created_by`.
3. **`team_members`**: Junction table assigning users to projects with `project_id`, `user_id`, `role_in_project`, and `joined_at`.
4. **`user_stories`**: Backlog user stories storing `project_id`, `sprint_id`, `title`, `description`, `priority`, `story_points`, `status`, and `assigned_to`.
5. **`sprints`**: Sprint iterations storing `project_id`, `name`, `goal`, `start_date`, `end_date`, `status`, and `velocity`.
6. **`tasks`**: Technical tasks storing `project_id`, `sprint_id`, `story_id`, `title`, `description`, `assigned_to`, `priority`, `estimated_hours`, `actual_hours`, `due_date`, and `status`.
7. **`standup_updates`**: Daily Scrum submissions storing `project_id`, `sprint_id`, `user_id`, `update_date`, `yesterday_text`, `today_text`, `blocker_text`, `status_category`, `is_blocked`, and `comments`.
8. **`bugs`**: Defect tracking storing `project_id`, `sprint_id`, `task_id`, `title`, `severity`, `status`, and `reported_by`.

---

## 🤖 AI & Machine Learning Layer

### 1. ML Sprint Risk Prediction (`ai/risk_model.py`, `ai/risk_service.py`)
- **Model**: `RandomForestClassifier` trained on historical and synthetic sprint metrics.
- **Preprocessing**: `StandardScaler` feature normalization.
- **Features Extracted**:
  - `task_completion_rate`: % of sprint tasks in `Done` status.
  - `time_elapsed_ratio`: Ratio of days elapsed vs. total sprint duration.
  - `overdue_task_ratio`: Ratio of overdue tasks vs. total tasks.
  - `workload_share`: Maximum developer workload ratio.
  - `bug_density_ratio`: Ratio of active bugs to user stories.
  - `velocity_ratio`: Current sprint points vs. average historical velocity.
- **Outputs**: Sprint delay risk level (`LOW`, `MEDIUM`, `HIGH`), model confidence score (e.g., `83.0%`), class probabilities, and top risk factors.

### 2. AI Recommendations Engine (`ai/recommendations.py`)
Rule-based recommendation engine evaluating live project metrics to issue prioritized action items:
- **`HIGH` Priority**: Overdue tasks detected, sprint deadline approaching with incomplete work, high ML risk assessment.
- **`MEDIUM` Priority**: Low overall task completion rate, unassigned developer workload imbalances.
- **`LOW` Priority**: Normal progress monitoring recommendations.

### 3. NLP Daily Stand-up Analysis (`ai/standup_analysis.py`)
Text-processing engine that analyzes developers' daily Scrum text submissions:
- **Blocker Detection**: Categorizes submissions as `BLOCKED`, `POTENTIAL_ISSUE`, or `ON_SCHEDULE` using keyword and pattern matching.
- **Repeated Blocker Alerting**: Tracks consecutive days a developer reports the same impediment (e.g., *API credentials missing for 3+ updates*).
- **Team Aggregation**: Computes reporting completion rates and compiles high-priority blockers for the Scrum Master feed.

### 4. AI Scrum Master Assistant (`ai/assistant.py`)
Natural-language assistant pipeline that operates entirely offline without external LLM API costs:
- **Intent Detection**: Intent classifier supporting 8 intents (`SPRINT_STATUS`, `RISK`, `OVERDUE_TASKS`, `TEAM_WORKLOAD`, `BLOCKERS`, `RECOMMENDATIONS`, `BACKLOG_STATUS`, `TASK_STATUS`).
- **Database Context Retrieval**: Queries real-time database models for the requested project.
- **Chat History**: Manages session chat history limited to the last 20 messages.

---

## 📄 Reporting & PDF Export

- **Sprint Report View**: Live UI summary displaying sprint goals, story points completed, velocity, task distribution, AI risk assessment, recommendations, and stand-up blockers.
- **Project Overview Report**: Comprehensive project health indicator (`Healthy`, `Needs Attention`, `At Risk`), total backlog progress, and sprint completion metrics.
- **Server-Side PDF Export (`utils/pdf_generator.py`)**: Uses ReportLab `SimpleDocTemplate` to format document streams into downloadable binary PDF files (`application/pdf`) via `/projects/<id>/reports/export/pdf`.

---

## 👥 User Roles & Permission Matrix

| Feature / Action | Scrum Master | Product Owner | Developer |
| :--- | :---: | :---: | :---: |
| **View Dashboard & Projects** | ✅ | ✅ | ✅ (Assigned) |
| **Create / Edit / Delete Projects** | ✅ | ❌ | ❌ |
| **Manage Team Members** | ✅ | ❌ | ❌ |
| **Create / Edit User Stories** | ✅ | ✅ | ❌ |
| **Create / Manage Sprints** | ✅ | ❌ | ❌ |
| **Create / Edit Tasks** | ✅ | ✅ | ❌ (Own progress only) |
| **Kanban Drag & Drop** | ✅ | ✅ | ✅ |
| **Log Actual Hours & Task Progress**| ✅ | ✅ | ✅ (Assigned tasks) |
| **Submit Daily Stand-up Update** | ✅ | ✅ | ✅ |
| **View AI Risk & Recommendations** | ✅ | ✅ | ✅ |
| **Query AI Assistant** | ✅ | ✅ | ✅ |
| **View & Export PDF Reports** | ✅ | ✅ | ✅ |

---

## 🔒 Security & Data Isolation

- **Password Security**: Passwords stored using Werkzeug secure password hashing (`pbkdf2:sha256`).
- **Session Management**: Server-side Flask session cookies with environment variable `SECRET_KEY` fallback.
- **Project Isolation**: All routes enforce backend membership validation (`Project.get_user_projects`, `_check_project_access`). Users cannot view, modify, or download reports for projects they are not assigned to.
- **Input Validation**: Form values are validated for non-empty text, non-negative hours, valid Fibonacci story points, valid date ranges, and sanitized query parameters.

---

## 📁 Directory Structure

```
cia_software/
├── app.py                      # Flask entry point & error handlers (404, 403, 500)
├── schema.sql                  # Database schema definitions
├── requirements.txt            # Python dependencies (Flask, scikit-learn, reportlab, joblib)
├── README.md                   # Comprehensive project documentation
├── walkthrough.md              # Feature implementation verification log
├── implementation_plan.md      # Technical design plan
│
├── database/
│   ├── db.py                   # SQLite connection provider & seed data initializer
│   └── database.db             # SQLite database storage file
│
├── models/
│   ├── user.py                 # User model & authentication helpers
│   ├── project.py              # Project CRUD & team member management
│   ├── story.py                # Product Backlog & User Story model
│   ├── sprint.py               # Sprint model & velocity calculator
│   ├── task.py                 # Task management & workload statistics
│   ├── standup.py              # Daily stand-up submissions & comment history
│   └── bug.py                  # Defect tracking model
│
├── ai/
│   ├── data_preparation.py     # Dataset generator & feature scaling
│   ├── risk_model.py           # RandomForest training & persistence pipeline
│   ├── risk_service.py         # AI Sprint Risk prediction inference engine
│   ├── recommendations.py      # Rule-based Scrum Master recommendation engine
│   ├── standup_analysis.py     # NLP stand-up blocker analyzer
│   └── assistant.py            # AI Scrum Master Assistant intent classifier & answer engine
│
├── routes/
│   ├── auth_routes.py          # /login, /register, /logout endpoints
│   ├── project_routes.py       # /dashboard, /projects CRUD, /team endpoints
│   ├── backlog_routes.py       # /projects/<id>/backlog endpoints
│   ├── sprint_routes.py        # /projects/<id>/sprints endpoints
│   ├── task_routes.py          # /tasks, /kanban endpoints
│   ├── standup_routes.py       # /projects/<id>/standup endpoints
│   ├── ai_routes.py            # /assistant chat & AI API endpoints
│   └── report_routes.py        # /projects/<id>/reports & PDF export endpoints
│
├── utils/
│   └── pdf_generator.py        # ReportLab PDF document builder
│
├── templates/
│   ├── base.html               # Main layout template with sidebar navigation
│   ├── login.html              # Login template
│   ├── register.html           # User registration template
│   ├── dashboard.html          # Main workspace dashboard & AI cards
│   ├── projects.html           # Project management view
│   ├── project_details.html    # Single project details view
│   ├── backlog.html            # Product backlog user story view
│   ├── sprints.html            # Sprint planning view
│   ├── kanban.html             # Drag-and-drop Kanban board view
│   ├── team.html               # Team management view
│   ├── standup.html            # Daily stand-up update feed view
│   ├── assistant.html          # AI Scrum Master Assistant chat interface
│   ├── reports.html            # Sprint & Project reports view with PDF trigger
│   └── error.html              # Custom 404, 403, 500 error page template
│
├── static/
│   ├── css/
│   │   └── style.css           # Vanilla CSS SaaS dark design system
│   └── js/
│       ├── main.js             # Modal controls & layout helpers
│       ├── kanban.js           # AJAX drag-and-drop Kanban controller
│       └── charts.js           # Chart.js dashboard charts
│
└── tests/                      # Automated Test Suite (72 tests, 100% pass)
    ├── test_auth_and_roles.py
    ├── test_projects_and_teams.py
    ├── test_backlog_sprints_tasks.py
    ├── test_error_handlers.py
    ├── test_assistant.py
    ├── test_reports.py
    ├── test_standup_analysis.py
    ├── test_recommendations.py
    ├── test_risk_service.py
    ├── test_risk_model.py
    └── test_data_preparation.py
```

---

## ⚙️ Installation & Setup Instructions

### 1. Prerequisites
- Python **3.10** or higher installed on Windows.

### 2. Open Terminal / PowerShell
Open PowerShell or Command Prompt and navigate to the project folder:
```powershell
cd c:\Users\steve\OneDrive\Desktop\cia_software
```

### 3. Virtual Environment Setup
Create and activate a virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 4. Install Dependencies
Install all required packages from `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### 5. Initialize Database & Run Server
Execute `app.py` to initialize database tables, seed default demo data, and launch the web server:
```powershell
.\venv\Scripts\python.exe app.py
```

### 6. Access the Application
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Demo Credentials

The database comes pre-seeded with sample user accounts for instant demonstration:

| User Role | Username / Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Scrum Master** | `scrummaster` (or `sm@agilescrum.io`) | `password123` | Full project & administrative control |
| **Developer** | `developer1` (or `dev1@agilescrum.io`) | `password123` | Assigned task updates & stand-up updates |
| **Product Owner** | `productowner` (or `po@agilescrum.io`) | `password123` | Product backlog & report management |

---

## 🧪 Testing & Verification Results

All 11 test modules were executed using the Python `unittest` framework:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests
```

### Final Test Summary:
- **Total Test Suites**: 11
- **Total Tests Executed**: 178
- **Passed**: 178 (100% Pass Rate)
- **Failed**: 0
- **Errors**: 0

---

## 🔮 Limitations & Future Enhancements

### Current Limitations
- **Offline Intent Classifier**: The AI assistant uses lightweight pattern matching for intent recognition to operate offline without API costs.
- **Synthetic Training Baseline**: The initial ML model is trained on a synthetic sprint dataset generated by `ai/data_preparation.py` due to a lack of historical real-world sprint databases.

### Future Enhancements
- **LLM Integration**: Option to connect external APIs (e.g., Gemini or OpenAI) for complex free-form conversational queries.
- **Third-Party Integrations**: Sync tasks and commits directly with GitHub, GitLab, or Jira.
- **WebSocket Push**: Live WebSocket events for real-time Kanban card movements across multiple active browser windows.
- **Burndown / Burnup Charts**: Visual SVG burndown progress charts embedded into Sprint Reports.
