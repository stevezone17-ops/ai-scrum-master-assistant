"""
ai/risk_service.py
==================
Step 12A: AI Sprint Risk Assessment Service

Integrates the trained Random Forest model (ai/models/sprint_risk_model.joblib)
with the active sprint data to produce risk predictions, confidence scores,
probabilities, dynamic explanations, and key risk factors for the dashboard.
"""

import logging
import pandas as pd
import numpy as np

from database.db import get_db
from models.sprint import Sprint
from ai.data_preparation import extract_sprint_dataset, FEATURE_COLUMNS
from ai.risk_model import load_model, predict_sprint_risk, get_model_info

logger = logging.getLogger(__name__)

# Cached model instance in memory so joblib.load is not called on every HTTP request
_CACHED_MODEL = None


def get_loaded_model(force_reload: bool = False) -> dict:
    """
    Get the cached model bundle or load it from disk.
    Does NOT retrain the model.
    """
    global _CACHED_MODEL
    if _CACHED_MODEL is None or force_reload:
        _CACHED_MODEL = load_model()
    return _CACHED_MODEL


def get_sprint_features_for_active_sprint(project_id: int) -> tuple:
    """
    Find active sprint for project_id and extract its 17 feature values.
    Returns (active_sprint_dict, features_dict) or (None, None).
    """
    active_sprint = Sprint.get_active_sprint(project_id)
    if not active_sprint:
        return None, None

    sprint_id = active_sprint['id']

    # Try extracting full dataset from SQLite via data_preparation
    try:
        dataset = extract_sprint_dataset()
        if not dataset.empty and 'sprint_id' in dataset.columns:
            sprint_rows = dataset[dataset['sprint_id'] == sprint_id]
            if not sprint_rows.empty:
                row = sprint_rows.iloc[0]
                features_dict = {col: float(row[col]) for col in FEATURE_COLUMNS if col in row}
                return dict(active_sprint), features_dict
    except Exception as e:
        logger.warning(f"Error extracting sprint dataset via data_preparation: {e}")

    # Fallback to direct DB calculation for active sprint if dataset extraction returned no row
    conn = get_db()
    try:
        # Calculate task metrics for this active sprint
        task_query = """
            SELECT
                COUNT(*)                                                     AS total_tasks,
                SUM(CASE WHEN status = 'Done'         THEN 1 ELSE 0 END)  AS completed_tasks,
                SUM(CASE WHEN status != 'Done'        THEN 1 ELSE 0 END)  AS pending_tasks,
                SUM(CASE WHEN priority IN ('Critical','High') THEN 1 ELSE 0 END) AS high_priority_tasks,
                COALESCE(SUM(estimated_hours), 0)                         AS estimated_hours,
                COALESCE(SUM(actual_hours), 0)                            AS actual_hours,
                SUM(
                    CASE
                        WHEN status != 'Done' AND due_date IS NOT NULL AND due_date < DATE('now')
                        THEN 1 ELSE 0
                    END
                ) AS overdue_tasks
            FROM tasks
            WHERE sprint_id = ?
        """
        t_row = conn.execute(task_query, (sprint_id,)).fetchone()
        t_dict = dict(t_row) if t_row else {}

        # Story points
        sp_query = """
            SELECT
                COALESCE(SUM(story_points), 0) AS total_story_points,
                COALESCE(SUM(CASE WHEN status = 'Done' THEN story_points ELSE 0 END), 0) AS completed_story_points
            FROM user_stories
            WHERE sprint_id = ?
        """
        sp_row = conn.execute(sp_query, (sprint_id,)).fetchone()
        sp_dict = dict(sp_row) if sp_row else {}

        # Developer count
        dev_query = "SELECT COUNT(DISTINCT assigned_to) FROM tasks WHERE sprint_id = ? AND assigned_to IS NOT NULL"
        dev_count = conn.execute(dev_query, (sprint_id,)).fetchone()[0] or 0

        # Bug count
        bug_query = "SELECT COUNT(*) FROM bugs WHERE sprint_id = ? AND status != 'Closed'"
        bug_count = conn.execute(bug_query, (sprint_id,)).fetchone()[0] or 0

        # Previous velocity
        vel_query = """
            SELECT COALESCE(AVG(sp_sum), 0.0) FROM (
                SELECT SUM(us.story_points) AS sp_sum
                FROM sprints s
                JOIN user_stories us ON us.sprint_id = s.id AND us.status = 'Done'
                WHERE s.project_id = ? AND s.id != ? AND s.status = 'Completed'
                GROUP BY s.id
            )
        """
        prev_vel = conn.execute(vel_query, (project_id, sprint_id)).fetchone()[0] or 0.0

        # Date calculations
        start_date = active_sprint.get('start_date')
        end_date = active_sprint.get('end_date')
        days_allocated = 14
        days_remaining = 0
        if start_date and end_date:
            try:
                s_dt = pd.to_datetime(start_date)
                e_dt = pd.to_datetime(end_date)
                now_dt = pd.to_datetime('today')
                days_allocated = max(1, (e_dt - s_dt).days)
                days_remaining = max(0, (e_dt - now_dt).days)
            except Exception:
                pass

        total_tasks = float(t_dict.get('total_tasks', 0))
        completed_tasks = float(t_dict.get('completed_tasks', 0))
        pending_tasks = float(t_dict.get('pending_tasks', 0))
        total_sp = float(sp_dict.get('total_story_points', 0))
        completed_sp = float(sp_dict.get('completed_story_points', 0))
        est_h = float(t_dict.get('estimated_hours', 0))
        act_h = float(t_dict.get('actual_hours', 0))

        task_completion_rate = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0
        sp_completion_rate = (completed_sp / total_sp) if total_sp > 0 else 0.0
        hours_variance = act_h - est_h

        features_dict = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'overdue_tasks': float(t_dict.get('overdue_tasks', 0)),
            'total_story_points': total_sp,
            'completed_story_points': completed_sp,
            'developer_count': float(dev_count),
            'estimated_hours': est_h,
            'actual_hours': act_h,
            'days_allocated': float(days_allocated),
            'days_remaining': float(days_remaining),
            'previous_velocity': float(prev_vel),
            'bug_count': float(bug_count),
            'high_priority_tasks': float(t_dict.get('high_priority_tasks', 0)),
            'task_completion_rate': round(task_completion_rate, 4),
            'story_point_completion_rate': round(sp_completion_rate, 4),
            'hours_variance': round(hours_variance, 2),
        }
        return dict(active_sprint), features_dict

    finally:
        conn.close()


def _format_risk_factors(features: dict, feature_importance: list) -> list:
    """
    Format top risk factors based on feature importance and real values.
    Returns a list of dicts with feature label, metric description, and impact level.
    """
    factor_labels = {
        'overdue_tasks': ('Overdue Tasks', lambda f: f"{int(f.get('overdue_tasks',0))} overdue task(s)"),
        'days_remaining': ('Days Remaining', lambda f: f"{int(f.get('days_remaining',0))} day(s) left in sprint"),
        'task_completion_rate': ('Task Completion', lambda f: f"{round(f.get('task_completion_rate',0)*100, 1)}% tasks completed"),
        'story_point_completion_rate': ('Story Point Progress', lambda f: f"{round(f.get('story_point_completion_rate',0)*100, 1)}% points completed"),
        'hours_variance': ('Hours Variance', lambda f: f"{'+' if f.get('hours_variance',0)>0 else ''}{round(f.get('hours_variance',0),1)}h vs estimated"),
        'bug_count': ('Open Bugs', lambda f: f"{int(f.get('bug_count',0))} unresolved bug(s)"),
        'high_priority_tasks': ('High Priority Backlog', lambda f: f"{int(f.get('high_priority_tasks',0))} high/critical task(s)"),
        'pending_tasks': ('Pending Tasks', lambda f: f"{int(f.get('pending_tasks',0))} task(s) pending"),
        'developer_count': ('Team Capacity', lambda f: f"{int(f.get('developer_count',0))} active developer(s)"),
    }

    factors = []
    # Pick top features from importance list that have notable metric signals
    for item in feature_importance:
        feat_name = item['feature']
        if feat_name in factor_labels:
            label, val_func = factor_labels[feat_name]
            val_str = val_func(features)
            
            # Determine impact relevance
            overdue = features.get('overdue_tasks', 0)
            comp_rate = features.get('task_completion_rate', 0)
            days_rem = features.get('days_remaining', 0)
            
            if feat_name == 'overdue_tasks' and overdue > 0:
                factors.append({'name': label, 'value': val_str, 'severity': 'high' if overdue >= 3 else 'medium'})
            elif feat_name == 'days_remaining':
                factors.append({'name': label, 'value': val_str, 'severity': 'high' if days_rem <= 2 else 'info'})
            elif feat_name == 'task_completion_rate':
                factors.append({'name': label, 'value': val_str, 'severity': 'high' if comp_rate < 0.3 else ('medium' if comp_rate < 0.6 else 'low')})
            elif feat_name == 'hours_variance' and abs(features.get('hours_variance', 0)) > 5:
                factors.append({'name': label, 'value': val_str, 'severity': 'medium' if features.get('hours_variance', 0) > 0 else 'info'})
            elif len(factors) < 4:
                factors.append({'name': label, 'value': val_str, 'severity': 'info'})

        if len(factors) >= 4:
            break

    return factors


def _generate_explanation(risk_level: str, features: dict) -> str:
    """
    Generate dynamic human-readable explanation based on real project metrics.
    """
    overdue = int(features.get('overdue_tasks', 0))
    days_rem = int(features.get('days_remaining', 0))
    comp_pct = round(features.get('task_completion_rate', 0.0) * 100, 1)
    sp_pct = round(features.get('story_point_completion_rate', 0.0) * 100, 1)

    if risk_level == 'HIGH':
        if overdue > 0 and days_rem <= 3:
            return f"High risk detected because {overdue} task(s) are overdue and only {days_rem} day(s) remain with {comp_pct}% task completion."
        elif overdue >= 3:
            return f"High risk detected due to {overdue} overdue tasks lagging behind the scheduled sprint end date."
        else:
            return f"High risk detected due to low story point completion ({sp_pct}%) and insufficient time remaining ({days_rem} days)."
    elif risk_level == 'MEDIUM':
        if overdue > 0:
            return f"Medium risk detected because {overdue} task(s) are currently overdue, though sprint completion stands at {comp_pct}%."
        elif comp_pct < 50 and days_rem <= 5:
            return f"Medium risk detected: task completion ({comp_pct}%) is lagging behind schedule with {days_rem} day(s) remaining."
        else:
            return f"Medium risk detected based on workload variance and remaining backlog item count."
    else:  # LOW
        return f"Low risk detected. Sprint development is on schedule ({comp_pct}% completed) with zero overdue tasks."


def get_ai_sprint_risk_assessment(project_id: int) -> dict:
    """
    Main service entry point for dashboard integration.

    Returns dict structured for UI rendering:
    {
        'has_sprint': True/False,
        'error': True/False,
        'message': str,
        'sprint_name': str,
        'risk_level': 'LOW' | 'MEDIUM' | 'HIGH',
        'confidence_pct': float,
        'probabilities': {'LOW': float, 'MEDIUM': float, 'HIGH': float},
        'badge_class': str,
        'explanation': str,
        'risk_factors': list,
        'features': dict
    }
    """
    active_sprint, features = get_sprint_features_for_active_sprint(project_id)

    if not active_sprint or not features:
        return {
            'has_sprint': False,
            'error': False,
            'message': "No active sprint available for AI risk analysis.",
            'risk_level': None,
            'sprint_name': None,
        }

    try:
        model_bundle = get_loaded_model()
    except Exception as e:
        logger.error(f"Failed to load AI sprint risk model: {e}", exc_info=True)
        return {
            'has_sprint': True,
            'error': True,
            'message': "AI risk analysis is currently unavailable.",
            'risk_level': None,
            'sprint_name': active_sprint.get('name'),
        }

    try:
        prediction = predict_sprint_risk(features, model_bundle)
        risk_level = prediction['risk']
        confidence = prediction['confidence']
        probabilities = prediction['probabilities']

        # Format probabilities as percentages (0-100)
        prob_pcts = {
            k: round(v * 100, 1) for k, v in probabilities.items()
        }
        confidence_pct = round(confidence * 100, 1)

        badge_class_map = {
            'LOW': 'badge-active',
            'MEDIUM': 'badge-high',
            'HIGH': 'badge-urgent',
        }
        badge_class = badge_class_map.get(risk_level, 'badge-secondary')

        feature_importance = model_bundle.get('feature_importance', [])
        risk_factors = _format_risk_factors(features, feature_importance)
        explanation = _generate_explanation(risk_level, features)

        return {
            'has_sprint': True,
            'error': False,
            'message': None,
            'sprint_id': active_sprint.get('id'),
            'sprint_name': active_sprint.get('name'),
            'risk_level': risk_level,
            'confidence_pct': confidence_pct,
            'probabilities': prob_pcts,
            'badge_class': badge_class,
            'explanation': explanation,
            'risk_factors': risk_factors,
            'features': features,
        }

    except Exception as e:
        logger.error(f"Error performing AI sprint risk prediction: {e}", exc_info=True)
        return {
            'has_sprint': True,
            'error': True,
            'message': "AI risk analysis is currently unavailable.",
            'risk_level': None,
            'sprint_name': active_sprint.get('name'),
        }
