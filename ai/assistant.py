"""
ai/assistant.py
===============
Step 12D: AI Scrum Master Assistant Engine

Provides intent classification, database-driven conversational responses,
modular context extraction for future LLM integration, and seamless 
reuse of existing ML risk prediction, recommendation engine, daily stand-up analysis, 
and project metrics.
"""

import re
import logging
from datetime import date
from database.db import get_db
from models.project import Project
from models.sprint import Sprint
from models.task import Task
from models.story import UserStory
from models.bug import Bug
from ai.risk_service import get_ai_sprint_risk_assessment
from ai.recommendations import get_recommendations
from ai.standup_analysis import generate_team_standup_summary

logger = logging.getLogger(__name__)

# Intent Categories
INTENT_SPRINT_STATUS = "SPRINT_STATUS"
INTENT_RISK = "RISK"
INTENT_OVERDUE_TASKS = "OVERDUE_TASKS"
INTENT_TEAM_WORKLOAD = "TEAM_WORKLOAD"
INTENT_BLOCKERS = "BLOCKERS"
INTENT_RECOMMENDATIONS = "RECOMMENDATIONS"
INTENT_TASK_STATUS = "TASK_STATUS"
INTENT_BACKLOG_STATUS = "BACKLOG_STATUS"
INTENT_UNKNOWN = "UNKNOWN"

# Pattern rules for Intent Detection (order matters)
INTENT_PATTERNS = [
    (INTENT_RISK, [
        r'\brisk\b', r'\bat risk\b', r'\brisk level\b', r'\brisk assessment\b',
        r'\bis the sprint (at risk|safe|failing)\b', r'\bhow risky\b', r'\brisk\?'
    ]),
    (INTENT_OVERDUE_TASKS, [
        r'\boverdue\b', r'\blate tasks?\b', r'\bpast due\b', r'\bbehind schedule\b',
        r'\bwhich tasks are (overdue|late)\b', r'\bany overdue\b', r'\bwhat tasks are late\b',
        r'\bshow me overdue\b'
    ]),
    (INTENT_TEAM_WORKLOAD, [
        r'\bworkload\b', r'\boverloaded\b', r'\bhighest workload\b', r'\bwho is working\b',
        r'\bdeveloper workload\b', r'\bteam workload\b', r'\bwho has the (most|highest)\b',
        r'\bwho is overloaded\b', r'\bwhich developer has the most work\b'
    ]),
    (INTENT_BLOCKERS, [
        r'\bblockers?\b', r'\bimpediments?\b', r'\bstuck\b', r'\bwaiting for\b',
        r'\bstandup blockers\b', r'\bwhat blockers\b', r'\bany blockers\b',
        r'\bwhat is blocking\b', r'\bblocking the team\b'
    ]),
    (INTENT_RECOMMENDATIONS, [
        r'\brecommendations?\b', r'\bwhat should (i|we|the scrum master) (focus|do)\b',
        r'\bsuggestions?\b', r'\bwhat to do\b', r'\baction items?\b', r'\badvice\b',
        r'\bhow to fix\b', r'\bwhat should i focus on\b', r'\bwhat should we do next\b'
    ]),
    (INTENT_TASK_STATUS, [
        r'\btasks? status\b', r'\btask breakdown\b', r'\bhow many tasks\b',
        r'\btask summary\b', r'\btasks completed\b', r'\btask counts?\b',
        r'\bhow many tasks are (completed|in progress|to do)\b', r'\bwhat is the task status\b'
    ]),
    (INTENT_BACKLOG_STATUS, [
        r'\bbacklog\b', r'\buser stories\b', r'\bstory points\b', r'\bbacklog items\b',
        r'\bhow many backlog items\b', r'\bhow many story points remain\b', r'\bwhat is the backlog status\b'
    ]),
    (INTENT_SPRINT_STATUS, [
        r'\bhow is (the )?(current )?sprint\b', r'\bsprint status\b', r'\bsprint progress\b',
        r'\bsprint health\b', r'\bhow are we doing\b', r'\bsprint overview\b', r'\bcurrent sprint\b',
        r'\bsprint details?\b', r'\bhow is the sprint doing\b', r'\bwhat is the current sprint progress\b'
    ])
]


def detect_intent(user_query: str) -> str:
    """
    Detect question intent using regex matching.
    Case-insensitive, robust to phrasing variations, whitespace normalized.
    """
    if not user_query or not isinstance(user_query, str) or not user_query.strip():
        return INTENT_UNKNOWN

    # Normalize query whitespace and lowercase
    query_clean = " ".join(user_query.strip().lower().split())

    for intent, patterns in INTENT_PATTERNS:
        for p in patterns:
            if re.search(p, query_clean):
                return intent

    return INTENT_UNKNOWN


def get_project_context(project_id: int, intent: str) -> dict:
    """
    Retrieve modular, structured project data for the given intent.
    Keeps project data retrieval separate from response generation.
    """
    context = {}
    active_sprint = Sprint.get_active_sprint(project_id)
    context['active_sprint'] = dict(active_sprint) if active_sprint else None

    if intent == INTENT_SPRINT_STATUS:
        if active_sprint:
            context['sprint_stats'] = Sprint.get_sprint_stats(active_sprint['id'])
            context['risk_info'] = get_ai_sprint_risk_assessment(project_id)

    elif intent == INTENT_RISK:
        context['risk_info'] = get_ai_sprint_risk_assessment(project_id)

    elif intent == INTENT_OVERDUE_TASKS:
        all_tasks = [dict(t) for t in Task.get_by_project(project_id)]
        context['overdue_tasks'] = [t for t in all_tasks if t.get('is_overdue') == 1]

    elif intent == INTENT_TEAM_WORKLOAD:
        context['workload_list'] = [dict(w) for w in Task.get_workload(project_id)]

    elif intent == INTENT_BLOCKERS:
        context['standup_summary'] = generate_team_standup_summary(project_id)

    elif intent == INTENT_RECOMMENDATIONS:
        context['recommendations_info'] = get_recommendations(project_id)

    elif intent == INTENT_TASK_STATUS:
        all_tasks = [dict(t) for t in Task.get_by_project(project_id)]
        status_counts = {}
        for t in all_tasks:
            st = t.get('status', 'To Do')
            status_counts[st] = status_counts.get(st, 0) + 1
        context['task_counts'] = status_counts
        context['total_tasks'] = len(all_tasks)

    elif intent == INTENT_BACKLOG_STATUS:
        stories = [dict(s) for s in UserStory.get_by_project(project_id)]
        context['total_stories'] = len(stories)
        context['backlog_cnt'] = sum(1 for s in stories if s.get('status') == 'Backlog')
        context['in_sprint_cnt'] = sum(1 for s in stories if s.get('status') == 'In Sprint')
        context['completed_cnt'] = sum(1 for s in stories if s.get('status') == 'Completed')
        context['total_sp'] = sum(s.get('story_points', 0) or 0 for s in stories)

    return context


def generate_response_from_context(intent: str, project: dict, context: dict, user_role: str = "Scrum Master") -> str:
    """
    Format concise, readable responses from retrieved project context, respecting user roles.
    Never hallucinates unmentioned data.
    """
    if intent == INTENT_SPRINT_STATUS:
        return _format_sprint_status(project, context)
    elif intent == INTENT_RISK:
        return _format_sprint_risk(project, context)
    elif intent == INTENT_OVERDUE_TASKS:
        return _format_overdue_tasks(project, context)
    elif intent == INTENT_TEAM_WORKLOAD:
        return _format_team_workload(project, context, user_role)
    elif intent == INTENT_BLOCKERS:
        return _format_blockers(project, context)
    elif intent == INTENT_RECOMMENDATIONS:
        return _format_recommendations(project, context, user_role)
    elif intent == INTENT_TASK_STATUS:
        return _format_task_status(project, context)
    elif intent == INTENT_BACKLOG_STATUS:
        return _format_backlog_status(project, context)
    else:
        return "I can help with sprint progress, risk, overdue tasks, team workload, blockers, backlog, task status, and Scrum recommendations."


def answer_question(question: str, project_id: int, user: dict = None, user_id: int = None, user_role: str = None) -> dict:
    """
    Main entry point function for the AI Scrum Master Assistant.
    Supports flexible user parameters (dict or explicit user_id/user_role).
    Enforces project-level isolation and role-based permissions.
    """
    if user and isinstance(user, dict):
        user_id = user_id or user.get('id')
        user_role = user_role or user.get('role')

    user_role = user_role or "Developer"

    if not question or not isinstance(question, str) or not question.strip():
        return {
            'intent': INTENT_UNKNOWN,
            'question': question or "",
            'response': "Please provide a valid question.",
            'error': True
        }

    # 1. Authorization & Project Isolation Check
    if user_id:
        user_projects = Project.get_user_projects(user_id, user_role)
        if not any(p['id'] == project_id for p in user_projects):
            return {
                'intent': INTENT_UNKNOWN,
                'question': question,
                'response': "Access Denied: You do not have permission to view information for this project.",
                'error': True
            }

    project = Project.get_by_id(project_id)
    if not project:
        return {
            'intent': INTENT_UNKNOWN,
            'question': question,
            'response': "Project not found.",
            'error': True
        }

    intent = detect_intent(question)

    try:
        context = get_project_context(project_id, intent)
        resp_text = generate_response_from_context(intent, project, context, user_role)

        return {
            'intent': intent,
            'question': question,
            'response': resp_text,
            'error': False
        }

    except Exception as e:
        logger.error(f"Error executing assistant query for project {project_id}: {e}", exc_info=True)
        return {
            'intent': intent,
            'question': question,
            'response': f"I encountered an issue analyzing data for {project['name']}: {str(e)}",
            'error': True
        }


# Alias for backward compatibility
def ask_assistant(project_id: int, user_id: int, user_role: str, user_query: str) -> dict:
    return answer_question(question=user_query, project_id=project_id, user_id=user_id, user_role=user_role)


# =============================================================================
# FORMATTER HELPERS
# =============================================================================

def _format_sprint_status(project: dict, context: dict) -> str:
    active_sprint = context.get('active_sprint')
    if not active_sprint:
        return (
            f"Project: {project['name']}\n\n"
            "No Active Sprint Found.\n"
            "Currently, there is no active sprint running for this project."
        )

    sprint_stats = context.get('sprint_stats', {})
    risk_info = context.get('risk_info', {})
    risk_level = risk_info.get('risk_level') or risk_info.get('predicted_risk') or 'N/A'

    try:
        sprint_end = date.fromisoformat(str(active_sprint['end_date']))
        days_rem = (sprint_end - date.today()).days
        days_str = f"{days_rem} days remaining" if days_rem >= 0 else f"{abs(days_rem)} days past end date"
    except Exception:
        days_str = "Dates unspecified"

    total_t = sprint_stats.get('total_tasks', 0)
    done_t = sprint_stats.get('completed_tasks', 0)
    task_pct = round((done_t / total_t * 100), 1) if total_t > 0 else 0.0

    total_sp = sprint_stats.get('total_story_points', 0)
    done_sp = sprint_stats.get('completed_story_points', 0)
    sp_pct = round((done_sp / total_sp * 100), 1) if total_sp > 0 else 0.0

    return (
        f"Current sprint: **{active_sprint['name']}**\n"
        f"Days remaining: **{days_str}**\n"
        f"Task completion: **{done_t}/{total_t}** ({task_pct}%)\n"
        f"Story point completion: **{done_sp}/{total_sp}** ({sp_pct}%)\n"
        f"Risk: **{risk_level}**"
    )


def _format_sprint_risk(project: dict, context: dict) -> str:
    active_sprint = context.get('active_sprint')
    sprint_name = active_sprint['name'] if active_sprint else "Active Sprint"
    risk_data = context.get('risk_info', {})

    if not risk_data or risk_data.get('error'):
        return (
            f"Sprint Risk Assessment:\n\n"
            f"Unable to calculate risk assessment: {risk_data.get('message', 'Model error') if risk_data else 'No data'}"
        )

    risk = risk_data.get('risk_level') or risk_data.get('predicted_risk') or 'UNKNOWN'
    conf = risk_data.get('confidence_pct', 0)
    risk_factors = risk_data.get('risk_factors', [])

    factors_lines = []
    if isinstance(risk_factors, list):
        for f in risk_factors:
            if isinstance(f, dict):
                factors_lines.append(f"- {f.get('name')}: {f.get('value')}")
            else:
                factors_lines.append(f"- {f}")

    factors_str = "\n".join(factors_lines) if factors_lines else "- No critical risk factors identified."

    recs = get_recommendations(project['id']).get('recommendations', [])
    rec_text = recs[0]['description'] if recs else "Keep monitoring daily progress and blockers."

    return (
        f"Sprint: **{sprint_name}**\n\n"
        f"Risk: **{risk}**\n"
        f"Confidence: **{conf}%**\n\n"
        f"Main factors:\n"
        f"{factors_str}\n\n"
        f"Recommendation:\n"
        f"{rec_text}"
    )


def _format_overdue_tasks(project: dict, context: dict) -> str:
    overdue_tasks = context.get('overdue_tasks', [])

    if not overdue_tasks:
        return (
            "Overdue Tasks:\n\n"
            "Great news! There are currently 0 overdue tasks in this project."
        )

    lines = []
    for t in overdue_tasks:
        dev = t.get('assignee_name') or 'Unassigned'
        due = t.get('due_date') or 'No date'
        status = t.get('status', 'To Do')
        lines.append(f"• **{t['title']}** - Assigned to: *{dev}* | Status: `{status}` | Due: **{due}**")

    tasks_list_str = "\n".join(lines)

    return (
        f"Overdue Tasks ({len(overdue_tasks)}):\n\n"
        f"The following overdue tasks require attention:\n\n"
        f"{tasks_list_str}"
    )


def _format_team_workload(project: dict, context: dict, user_role: str) -> str:
    workload_list = context.get('workload_list', [])

    if not workload_list:
        return (
            "Team Workload Analysis:\n\n"
            "No workload data available for this project."
        )

    sorted_wl = sorted(
        workload_list,
        key=lambda x: (x.get('workload_pct', 0), x.get('assigned_hours', 0)),
        reverse=True
    )

    highest_dev = sorted_wl[0]
    uname = highest_dev.get('username', 'Developer')
    pct = round(highest_dev.get('workload_pct', 0), 1)
    hrs = highest_dev.get('assigned_hours', 0)

    dev_lines = []
    for w in sorted_wl:
        dev_name = w.get('username', 'Developer')
        dev_pct = round(w.get('workload_pct', 0), 1)
        dev_hrs = w.get('assigned_hours', 0)
        tot = w.get('total_tasks', 0)
        dev_lines.append(f"• **{dev_name}**: {dev_hrs} hrs ({dev_pct}% capacity) - {tot} task(s)")

    devs_str = "\n".join(dev_lines)

    return (
        f"Highest Workload: **{uname}** ({pct}% capacity with {hrs} hrs assigned).\n\n"
        f"Team Workload Overview:\n"
        f"{devs_str}"
    )


def _format_blockers(project: dict, context: dict) -> str:
    summary = context.get('standup_summary', {})

    if not summary or summary.get('error') or not summary.get('has_updates'):
        return (
            "Daily Stand-up Blockers:\n\n"
            "No stand-up updates have been submitted by the team for today yet."
        )

    blockers = summary.get('high_priority_blockers', [])
    potentials = summary.get('potential_issues', [])
    repeated = summary.get('repeated_blockers', [])

    if not blockers and not potentials:
        return (
            "Daily Stand-up Blockers:\n\n"
            "No active blockers or potential issues reported today!"
        )

    lines = []
    if repeated:
        for r in repeated:
            lines.append(f"[REPEATED BLOCKER] {r.get('message')}")

    if blockers:
        lines.append("\nHigh Priority Blockers:")
        for b in blockers:
            lines.append(f"• **{b['developer']}**: {b['blocker']}")

    if potentials:
        lines.append("\nPotential Delays / Risks:")
        for p in potentials:
            lines.append(f"• **{p['developer']}**: {p['issue']}")

    return "Daily Stand-up Blockers:\n\n" + "\n".join(lines)


def _format_recommendations(project: dict, context: dict, user_role: str) -> str:
    recs_info = context.get('recommendations_info', {})
    recs = recs_info.get('recommendations', [])

    if not recs:
        return (
            "AI Recommendations:\n\n"
            "No major issues detected. The sprint is progressing normally."
        )

    rec_lines = []
    for r in recs:
        prio = r.get('priority', 'LOW')
        rec_lines.append(f"[{prio}] **{r['title']}**\n  Recommendation: {r['description']}")

    return (
        f"AI Recommendations ({len(recs)}):\n\n" +
        "\n\n".join(rec_lines)
    )


def _format_task_status(project: dict, context: dict) -> str:
    status_counts = context.get('task_counts', {})
    total = context.get('total_tasks', 0)

    todo = status_counts.get('To Do', 0)
    in_prog = status_counts.get('In Progress', 0)
    testing = status_counts.get('Testing', 0)
    done = status_counts.get('Done', 0)

    done_pct = round(done / total * 100, 1) if total > 0 else 0.0

    return (
        f"Task Status Breakdown:\n\n"
        f"• **Total Tasks:** **{total}**\n"
        f"• **To Do:** {todo}\n"
        f"• **In Progress:** {in_prog}\n"
        f"• **Testing:** {testing}\n"
        f"• **Done:** **{done}** ({done_pct}% completed)"
    )


def _format_backlog_status(project: dict, context: dict) -> str:
    total = context.get('total_stories', 0)
    backlog_cnt = context.get('backlog_cnt', 0)
    in_sprint_cnt = context.get('in_sprint_cnt', 0)
    completed_cnt = context.get('completed_cnt', 0)
    total_sp = context.get('total_sp', 0)

    return (
        f"Product Backlog Status:\n\n"
        f"• **Total User Stories:** **{total}** ({total_sp} total story points)\n"
        f"• **Backlog (Unassigned):** {backlog_cnt}\n"
        f"• **In Sprint:** {in_sprint_cnt}\n"
        f"• **Completed:** {completed_cnt}"
    )
