"""
ai/recommendations.py
====================
Step 12B: AI Scrum Master Recommendation Engine

Analyzes real-time sprint metrics and ML risk assessment results to provide 
prioritized, actionable recommendations to the Scrum Master.
"""

import logging
from models.task import Task
from ai.risk_service import (
    get_sprint_features_for_active_sprint,
    get_ai_sprint_risk_assessment
)

logger = logging.getLogger(__name__)


def generate_recommendations_from_features(features: dict, predicted_risk: str, workloads: list = None) -> list:
    """
    Core rule engine that evaluates sprint metrics, predicted risk level,
    and developer workloads to generate prioritized recommendations.

    Each recommendation dict contains:
    - title: str
    - description: str
    - priority: 'HIGH' | 'MEDIUM' | 'LOW'
    """
    raw_recommendations = []

    if not features:
        return []

    overdue_tasks = int(features.get('overdue_tasks', 0))
    days_remaining = int(features.get('days_remaining', 0))
    pending_tasks = int(features.get('pending_tasks', 0))
    total_tasks = int(features.get('total_tasks', 0))
    actual_hours = float(features.get('actual_hours', 0.0))
    estimated_hours = float(features.get('estimated_hours', 0.0))
    task_completion_rate = float(features.get('task_completion_rate', 0.0))
    bug_count = int(features.get('bug_count', 0))

    # Rule 1: Overdue tasks
    if overdue_tasks > 0:
        raw_recommendations.append({
            'title': f"Review overdue tasks and prioritize them ({overdue_tasks} task(s) overdue).",
            'description': "Review overdue tasks and prioritize them.",
            'priority': "HIGH"
        })

    # Rule 2: Low days remaining and many incomplete tasks
    if days_remaining <= 3 and pending_tasks > 0:
        raw_recommendations.append({
            'title': f"Sprint deadline is approaching with {pending_tasks} incomplete tasks.",
            'description': "Sprint is approaching its deadline. Consider moving low-priority work to the next sprint.",
            'priority': "HIGH"
        })

    # Rule 3: High developer workload
    if workloads:
        for dev in workloads:
            workload_pct = dev.get('workload_pct', 0)
            assigned_hrs = dev.get('assigned_hours', 0)
            if workload_pct > 100 or assigned_hrs > 40:
                username = dev.get('username', 'Developer')
                raw_recommendations.append({
                    'title': f"{username} has a high workload.",
                    'description': "Consider redistributing tasks among available developers.",
                    'priority': "MEDIUM"
                })

    # Rule 4: Actual hours > Estimated hours
    if actual_hours > estimated_hours:
        raw_recommendations.append({
            'title': "Tasks taking longer than estimated.",
            'description': "Tasks are taking longer than estimated. Review task estimates and blockers.",
            'priority': "MEDIUM"
        })

    # Rule 5: Low completion rate
    if total_tasks > 0 and task_completion_rate < 0.5:
        raw_recommendations.append({
            'title': "Low task completion rate.",
            'description': "Consider reducing sprint scope or discussing blockers with the team.",
            'priority': "MEDIUM"
        })

    # Rule 6: High bug count
    if bug_count >= 3:
        raw_recommendations.append({
            'title': f"High bug count ({bug_count} unresolved bugs).",
            'description': "Prioritize critical bugs before taking additional work.",
            'priority': "MEDIUM"
        })

    # Rule 7-9: Risk level recommendations
    if predicted_risk == 'HIGH':
        raw_recommendations.append({
            'title': "High Sprint Risk Detected.",
            'description': "Schedule an immediate sprint review with the team and address blockers.",
            'priority': "HIGH"
        })
    elif predicted_risk == 'MEDIUM':
        raw_recommendations.append({
            'title': "Medium Sprint Risk Detected.",
            'description': "Monitor sprint progress closely and review incomplete work.",
            'priority': "MEDIUM"
        })
    elif predicted_risk == 'LOW':
        raw_recommendations.append({
            'title': "Low Sprint Risk Detected.",
            'description': "Sprint is progressing well. Continue monitoring remaining work.",
            'priority': "LOW"
        })

    # Priority sorting: HIGH -> MEDIUM -> LOW
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    raw_recommendations.sort(key=lambda x: priority_order.get(x['priority'], 9))

    # Deduplication
    seen = set()
    deduped = []
    for rec in raw_recommendations:
        key = (rec['title'], rec['description'])
        if key not in seen:
            seen.add(key)
            deduped.append(rec)

    # Return maximum of 5 recommendations
    return deduped[:5]


def get_recommendations(project_id: int) -> dict:
    """
    Main service entry point to retrieve recommendations for a project's active sprint.

    Returns:
    {
        'has_sprint': bool,
        'error': bool,
        'message': str or None,
        'sprint_name': str or None,
        'recommendations': list
    }
    """
    try:
        active_sprint, features = get_sprint_features_for_active_sprint(project_id)
        if not active_sprint or not features:
            return {
                'has_sprint': False,
                'error': False,
                'message': "No active sprint available for AI recommendations.",
                'sprint_name': None,
                'recommendations': []
            }

        risk_assessment = get_ai_sprint_risk_assessment(project_id)
        predicted_risk = risk_assessment.get('risk_level') or 'LOW'

        # Fetch workload stats for active sprint
        workloads = []
        try:
            workload_raw = Task.get_workload(project_id, active_sprint['id'])
            workloads = [dict(w) for w in workload_raw]
        except Exception as e:
            logger.warning(f"Failed to fetch workload stats: {e}")

        recs = generate_recommendations_from_features(features, predicted_risk, workloads)

        return {
            'has_sprint': True,
            'error': False,
            'message': None,
            'sprint_name': active_sprint.get('name'),
            'recommendations': recs
        }

    except Exception as e:
        logger.error(f"Error fetching recommendations: {e}", exc_info=True)
        return {
            'has_sprint': True,
            'error': True,
            'message': "AI recommendation engine is currently unavailable.",
            'sprint_name': None,
            'recommendations': []
        }
