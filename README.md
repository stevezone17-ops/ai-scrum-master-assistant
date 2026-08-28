# 🤖 AI-Based Scrum Master Assistant for Agile Software Project Management

[![Deployment Status](https://img.shields.io/badge/Render-Deployed-brightgreen.svg)](https://ai-scrum-master-assistant.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey.svg)](https://flask.palletsprojects.org/)
[![Database](https://img.shields.io/badge/Database-Supabase%20PostgreSQL%20%7C%20SQLite-blueviolet.svg)](https://supabase.com)
[![Machine Learning](https://img.shields.io/badge/ML-Scikit--Learn%20RandomForest-orange.svg)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> An enterprise-grade, full-stack Agile project management platform featuring **Machine Learning Sprint Delay Risk Evaluation (Scikit-Learn)**, **Rule-Based Recommendations**, **NLP Daily Stand-up Blocker Analysis**, an **Offline AI Scrum Master Assistant**, and **Server-Side PDF Exporting**. Supports dual database backends (**Supabase PostgreSQL** for production cloud hosting & **SQLite** for local zero-config offline execution).

---

## 🌐 Live Production Deployment

- **Live Web Application**: [https://ai-scrum-master-assistant.onrender.com](https://ai-scrum-master-assistant.onrender.com)
- **Primary Database Backend**: Supabase PostgreSQL Cloud
- **Production Server Engine**: Gunicorn WSGI Server

---

## 📋 Table of Contents

1. [Executive Summary & Core Objectives](#-executive-summary--core-objectives)
2. [Key Product Features](#-key-product-features)
3. [Agile & Scrum Methodologies Implemented](#-agile--scrum-methodologies-implemented)
4. [System Architecture & Flow](#-system-architecture--flow)
5. [Technology Stack](#-technology-stack)
6. [Database Design & Dual-Backend Architecture](#-database-design--dual-backend-architecture)
7. [AI & Machine Learning Engine](#-ai--machine-learning-engine)
   - [1. ML Sprint Delay Risk Model](#1-ml-sprint-delay-risk-model)
   - [2. AI Scrum Master Recommendations Engine](#2-ai-scrum-master-recommendations-engine)
   - [3. NLP Daily Stand-Up Impediment Analyzer](#3-nlp-daily-stand-up-impediment-analyzer)
   - [4. Intent-Based AI Assistant Chat](#4-intent-based-ai-assistant-chat)
8. [Reporting & Server-Side PDF Export](#-reporting--server-side-pdf-export)
9. [Role-Based Access Control (RBAC) Matrix](#-role-based-access-control-rbac-matrix)
10. [Repository Directory Layout](#-repository-directory-layout)
11. [Local Development & Installation Guide](#-local-development--installation-guide)
12. [Environment Configuration (.env)](#-environment-configuration-env)
13. [Render Production Deployment Guide](#-render-production-deployment-guide)
14. [Default Demo Credentials](#-default-demo-credentials)
15. [Automated Testing & Verification](#-automated-testing--verification)
16. [License & Acknowledgments](#-license--acknowledgments)

---

## 🎯 Executive Summary & Core Objectives

### The Problem
Modern software development teams using traditional project management tools (like Jira or Trello) often experience silent sprint failures. Issues like unmonitored scope creep, undetected technical blockers, unbalanced developer workloads, and over-estimated tasks are typically discovered too late during sprint retrospectives.

### The Solution
The **AI-Based Scrum Master Assistant** connects standard Agile workflow management (Product Backlogs, Sprint Cycles, Kanban Boards, Stand-up Updates) directly with an intelligent analytical engine. It continuously evaluates sprint progress metrics, predicts sprint delivery risks, highlights impediments reported across consecutive stand-up updates, and offers actionable recommendations to keep projects on track.

---

## ✨ Key Product Features

- **📊 Dynamic Executive Dashboard**: Real-time project overview featuring active sprint progress, task completion metrics, team workload distributions, project health indicators, and AI insight cards.
- **📁 Multi-Project Workspace**: Create and manage multiple software projects with team role assignments (`Scrum Master`, `Product Owner`, `Developer`).
- **🔖 Product Backlog Management**: Prioritized backlog framing user stories with Fibonacci Story Point estimations (`1`, `2`, `3`, `5`, `8`, `13`) and priority indicators (`Low`, `Medium`, `High`, `Critical`).
- **⚡ Sprint Iteration Management**: Time-boxed sprint planning with start/end dates, sprint goals, velocity tracking, and automatic rollover of incomplete user stories.
- **📋 Interactive Drag & Drop Kanban Board**: Visual 4-column workflow (`To Do`, `In Progress`, `Testing`, `Done`) with real-time AJAX state updates.
- **💬 Daily Stand-up Feed**: Log daily Scrum updates (work completed yesterday, planned work today, technical blockers) with automatic blocker severity flags.
- **🤖 Offline AI Scrum Master Assistant**: Conversational chat interface answering questions regarding sprint risk, overdue tasks, team workload, and reported blockers.
- **📄 Professional PDF Reports**: Generate server-side PDF status reports for projects and sprints using ReportLab.
- **🔄 Dual Database Support**: Zero-config local execution with SQLite, alongside live production cloud database support via Supabase PostgreSQL.

---

## 🔄 Agile & Scrum Methodologies Implemented

| Agile Artifact / Event | Implementation Details |
| :--- | :--- |
| **Product Backlog** | Central requirement repository structured as user stories with Fibonacci estimations and status states (`Backlog`, `Ready`, `In Sprint`, `Completed`). |
| **Sprint Planning** | Time-boxed iterations (`Planned`, `Active`, `Completed`) with defined sprint goals and points tracking. |
| **Task Breakdown** | Fine-grained technical tasks assigned to developers under specific user stories with estimated vs. actual logged hours. |
| **Kanban Board** | Visual task progress columns enabling developers to move work items cleanly across stages. |
| **Daily Stand-up** | Structured 3-question daily Scrum updates capturing work finished, planned work, and active technical impediments. |
| **Sprint Velocity** | Historical tracking of completed story points across iterations to establish team velocity baselines. |

---

## 🏗️ System Architecture & Flow

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
            +--------------------------+    |    +--------------------------+
            |                               |                               |
            v                               v                               v
+-----------------------+         +-------------------+           +-------------------+
|  Database Switcher    |         |    AI/ML Layer    |           | ReportLab PDF Engine|
| (database/db.py)      |         |      (ai/)        |           |(utils/pdf_generator)|
+-----------+-----------+         +---------+---------+           +-------------------+
            |                               |
     +------+------+                        +--------------------+--------------------+
     |             |                        |                    |                    |
     v             v                        v                    v                    v
+---------+  +-----------+         +-----------------+  +------------------+  +------------------+
| SQLite3 |  | Supabase  |         | ML Risk Model   |  | Recommendations  |  | Stand-up NLP     |
| Local   |  | PostgreSQL|         | (RandomForest)  |  | Engine           |  | Analyzer         |
+---------+  +-----------+         +-----------------+  +------------------+  +------------------+
                                            |
                                            v
                                   +------------------+
                                   | AI Assistant     |
                                   | Query Engine     |
                                   +------------------+
```

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, Vanilla CSS3 (Custom Dark Theme Design System), JavaScript (ES6+ AJAX), FontAwesome 6, Chart.js
- **Backend Framework**: Python 3.12, Flask 3.x, Werkzeug, Gunicorn (Production WSGI)
- **Database Engine**: Supabase PostgreSQL (Cloud) / SQLite3 (Local)
- **Data Engineering**: Pandas 2.x, NumPy 1.24+
- **Machine Learning**: Scikit-Learn 1.3+ (`RandomForestClassifier`, `StandardScaler`), Joblib
- **Document Generator**: ReportLab 4.x (Server-Side PDF)
- **Testing Suites**: Python `unittest` & `pytest`

---

## 🗄️ Database Design & Dual-Backend Architecture

The platform supports 8 relational tables with foreign-key constraints across both database backends:

```
                          +---------------+
                          |     users     |
                          +-------+-------+
                                  |
            +---------------------+---------------------+
            |                     |                     |
            v                     v                     v
    +---------------+     +---------------+     +---------------+
    |   projects    | <-> |  team_members |     |standup_updates|
    +-------+-------+     +---------------+     +---------------+
            |
            +---------------------+
            |                     |
            v                     v
    +---------------+     +---------------+
    |    sprints    |     | user_stories  |
    +-------+-------+     +-------+-------+
            |                     |
            +----------+----------+
                       |
                       v
                +---------------+     +---------------+
                |     tasks     | <-> |     bugs      |
                +---------------+     +---------------+
```

### Database Abstraction Switcher (`database/db.py`)
- **`DATABASE_BACKEND=sqlite`**: Uses local SQLite file database (`database/database.db`).
- **`DATABASE_BACKEND=supabase`**: Uses Supabase PostgreSQL cloud database via PostgREST API with a dynamic Python type adapter (`database/supabase_adapter.py`).

---

## 🤖 AI & Machine Learning Engine

### 1. ML Sprint Delay Risk Model (`ai/risk_model.py`, `ai/risk_service.py`)
- **Algorithm**: `RandomForestClassifier`
- **Feature Pipeline**: Normalized via `StandardScaler`
- **Key Metrics Evaluated**:
  - `task_completion_rate`: % of tasks in `Done` state.
  - `story_point_completion_rate`: % of sprint story points finished.
  - `overdue_tasks`: Count of tasks past due date.
  - `days_remaining_pct`: Time left vs. total sprint duration.
  - `hours_variance`: Actual hours logged vs. estimated.
- **Output**: Risk Classification (`LOW`, `MEDIUM`, `HIGH`), Confidence Score (e.g. `85%`), and key risk drivers.

### 2. AI Scrum Master Recommendations Engine (`ai/recommendations.py`)
Generates actionable, prioritized Scrum Master advice based on metric variances:
- **`HIGH` Priority**: Overdue tasks, approaching deadline with low completion, ML high risk flags.
- **`MEDIUM` Priority**: Developer workload imbalances, unassigned high-priority tasks.
- **`LOW` Priority**: Normal velocity & progress tracking guidance.

### 3. NLP Daily Stand-Up Impediment Analyzer (`ai/standup_analysis.py`)
- **Blocker Categorization**: Analyzes daily updates to flag status (`BLOCKED`, `POTENTIAL_ISSUE`, `ON_SCHEDULE`).
- **Consecutive Blocker Alert**: Flags recurring developer impediments reported across multiple consecutive days.

### 4. Intent-Based AI Assistant Chat (`ai/assistant.py`)
- **Offline Query Processing**: Categorizes questions into 8 intents (`SPRINT_STATUS`, `RISK`, `OVERDUE_TASKS`, `TEAM_WORKLOAD`, `BLOCKERS`, `RECOMMENDATIONS`, `BACKLOG_STATUS`, `TASK_STATUS`).
- **Context Injection**: Queries live database models to inject real project metrics directly into assistant answers.

---

## 📄 Reporting & Server-Side PDF Export

- **Interactive Web Reports**: Dynamic project health summaries, sprint point breakdown, developer capacity progress, and AI recommendations.
- **Server-Side PDF Generator (`utils/pdf_generator.py`)**: Generates downloadable PDF reports via ReportLab at `/projects/<id>/reports/export/pdf`.

---

## 👥 Role-Based Access Control (RBAC) Matrix

| Action / Capability | Scrum Master | Product Owner | Developer |
| :--- | :---: | :---: | :---: |
| **View Dashboard & Workspace** | ✅ | ✅ | ✅ |
| **Create / Edit / Delete Projects** | ✅ | ❌ | ❌ |
| **Manage Team Members** | ✅ | ❌ | ❌ |
| **Create / Edit User Stories** | ✅ | ✅ | ❌ |
| **Manage Sprints (Create/Start/Complete)** | ✅ | ❌ | ❌ |
| **Create / Edit Tasks** | ✅ | ✅ | ❌ (Log hours only) |
| **Kanban Drag-and-Drop** | ✅ | ✅ | ✅ |
| **Submit Daily Stand-up Update** | ✅ | ✅ | ✅ |
| **Query AI Assistant & View AI Risk** | ✅ | ✅ | ✅ |
| **Export PDF Reports** | ✅ | ✅ | ✅ |

---

## 📁 Repository Directory Layout

```
cia_software/
├── app.py                      # Flask Application Entry Point & Port Binding
├── render.yaml                 # Render Production Deployment Blueprint
├── requirements.txt            # Production Dependencies
├── schema.sql                  # SQLite Database Schema
├── supabase_schema.sql         # Supabase PostgreSQL Database Schema
├── README.md                   # Production Documentation
│
├── database/
│   ├── db.py                   # Unified Database Connection Provider
│   ├── supabase_adapter.py     # Supabase PostgREST & Type Conversion Adapter
│   └── database.db             # Local SQLite Database File
│
├── models/
│   ├── user.py                 # User Account & Authentication Model
│   ├── project.py              # Project CRUD & Workspace Model
│   ├── story.py                # Product Backlog & User Story Model
│   ├── sprint.py               # Sprint Iteration & Velocity Model
│   ├── task.py                 # Task & Workload Model
│   ├── standup.py              # Daily Stand-Up Update Model
│   └── bug.py                  # Defect & Bug Tracking Model
│
├── ai/
│   ├── data_preparation.py     # ML Feature Pipeline & Data Cleaner
│   ├── risk_model.py           # RandomForest Training & Storage Pipeline
│   ├── risk_service.py         # Real-time Sprint Risk Prediction Engine
│   ├── recommendations.py      # Rule-based Recommendations Engine
│   ├── standup_analysis.py     # NLP Stand-up Blocker Analyzer
│   └── assistant.py            # Offline AI Assistant Query Engine
│
├── routes/
│   ├── auth_routes.py          # /login, /register, /logout
│   ├── project_routes.py       # /dashboard, /projects, /team
│   ├── backlog_routes.py       # /projects/<id>/backlog
│   ├── sprint_routes.py        # /projects/<id>/sprints
│   ├── task_routes.py          # /tasks, /kanban
│   ├── standup_routes.py       # /projects/<id>/standup
│   ├── ai_routes.py            # /assistant chat endpoints
│   └── report_routes.py        # /projects/<id>/reports & PDF export
│
├── utils/
│   ├── supabase_client.py      # Official Supabase Python Client Provider
│   └── pdf_generator.py        # ReportLab PDF Document Engine
│
├── scripts/
│   └── migrate_sqlite_to_supabase.py # SQLite-to-Supabase One-Time Data Migration Tool
│
├── templates/                  # Jinja2 HTML Templates (Dark SaaS Theme)
├── static/                     # Custom Vanilla CSS & Client JavaScript
└── tests/                      # Pytest & Unittest Test Suite (100% Pass)
```

---

## ⚙️ Local Development & Installation Guide

### 1. Prerequisites
- Python **3.10** or higher installed.

### 2. Clone & Navigate to Project
```bash
git clone https://github.com/stevezone17-ops/ai-scrum-master-assistant.git
cd ai-scrum-master-assistant
```

### 3. Virtual Environment Setup
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Launch Local Server (SQLite Mode)
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## 🔐 Environment Configuration (.env)

Create a `.env` file in the project root:

```env
# Database Backend Switcher (supabase OR sqlite)
DATABASE_BACKEND=sqlite

# Flask Configuration
SECRET_KEY=your_production_secret_key_here
FLASK_ENV=development

# Supabase PostgreSQL Configuration (Required if DATABASE_BACKEND=supabase)
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
```

---

## 🚀 Render Production Deployment Guide

1. **Push Repository to GitHub**: Ensure all files are committed to `main`.
2. **Create New Web Service on Render**: Connect your GitHub repository.
3. **Build & Start Commands**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. **Environment Variables on Render**:
   - `DATABASE_BACKEND` = `supabase`
   - `SUPABASE_URL` = `https://<your-project>.supabase.co`
   - `SUPABASE_KEY` = `<your-supabase-key>`
   - `SECRET_KEY` = `<your-secret-key>`
   - `PYTHON_VERSION` = `3.12.3`

---

## 🔑 Default Demo Credentials

Pre-seeded demo accounts available for immediate testing:

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Scrum Master** | `scrummaster` | `password123` | Full project & sprint management access |
| **Product Owner** | `productowner` | `password123` | Backlog creation & story points estimation |
| **Developer** | `dev1` | `password123` | Task logging, Kanban updates & stand-up updates |

---

## 🧪 Automated Testing & Verification

Run the test suite using `pytest`:

```bash
python -m pytest tests/ -v
```

### Test Suite Execution Output
```
======================= 21 passed in 41.88s =======================
```

---

## 📜 License & Acknowledgments

This project is open-source software licensed under the **MIT License**.
