"""
ai/standup_analysis.py
======================
Step 12C: AI Daily Stand-up Analysis Module

Provides explainable NLP text analysis, blocker extraction, progress summarization,
team aggregation, and repeated blocker tracking for Agile daily stand-ups.
"""

import logging
import re
from datetime import date
from difflib import SequenceMatcher
from models.standup import StandupUpdate
from models.project import Project

logger = logging.getLogger(__name__)

# Keywords indicating definite blockers
BLOCKER_KEYWORDS = [
    "blocked", "blocker", "waiting", "dependency", "failing",
    "error", "unavailable", "stuck", "cannot", "unable",
    "impediment", "broken", "help needed"
]

# Keywords indicating potential delays or risks
POTENTIAL_ISSUE_KEYWORDS = [
    "delayed", "delay", "issue", "behind", "uncertain", "slow",
    "risk", "difficult", "complex", "pending", "investigating",
    "troubleshooting", "struggling", "bottleneck"
]

# Benign phrases that indicate no blocker
BENIGN_BLOCKER_PHRASES = [
    "none", "n/a", "na", "no blockers", "no blocker", "nil", "nothing",
    "all good", "no impediment", "no issues", "no issue", "clear", "nope"
]


def _is_benign_text(text: str) -> bool:
    """Check if the given blocker text essentially means 'no blocker'."""
    if not text:
        return True
    cleaned = re.sub(r'[^\w\s]', '', text.strip().lower())
    return cleaned in BENIGN_BLOCKER_PHRASES or len(cleaned) == 0


def _extract_keywords(text: str, keyword_list: list) -> list:
    """Find all matching keywords/phrases in the given text."""
    if not text:
        return []
    lower_text = text.lower()
    found = []
    for kw in keyword_list:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, lower_text):
            found.append(kw)
    return found


def classify_standup_text(yesterday_work: str, today_plan: str, blockers: str = "", comments: str = "") -> dict:
    """
    Classify a stand-up submission into BLOCKED, POTENTIAL_ISSUE, or NO_ISSUE.

    Returns:
    {
        'status': 'BLOCKED' | 'POTENTIAL_ISSUE' | 'NO_ISSUE',
        'badge_class': str,
        'reason': str,
        'keywords': list,
        'has_blocker': bool
    }
    """
    yesterday = yesterday_work or ""
    today = today_plan or ""
    blocker_text = blockers or ""
    comment_text = comments or ""

    full_text = f"{yesterday} {today} {blocker_text} {comment_text}"
    
    # Check blockers field explicitly
    blocker_is_active = not _is_benign_text(blocker_text)

    # Extract keywords
    blocker_kw_in_blockers = _extract_keywords(blocker_text, BLOCKER_KEYWORDS)
    blocker_kw_in_all = _extract_keywords(full_text, BLOCKER_KEYWORDS)
    potential_kw_in_all = _extract_keywords(full_text, POTENTIAL_ISSUE_KEYWORDS)

    # 1. Definite Blocked condition
    if blocker_is_active:
        keywords = list(set(blocker_kw_in_all + blocker_kw_in_blockers))
        if "waiting" in keywords or "dependency" in keywords:
            reason = "Waiting for an external dependency or approval."
        elif "failing" in keywords or "error" in keywords or "broken" in keywords:
            reason = "Encountering technical errors or failing tests."
        elif "stuck" in keywords or "unable" in keywords or "cannot" in keywords:
            reason = "Developer is stuck or unable to proceed on current task."
        else:
            reason = f"Blocker reported: {blocker_text[:80]}"

        return {
            'status': 'BLOCKED',
            'badge_class': 'badge-urgent',
            'reason': reason,
            'keywords': keywords if keywords else ['blocker'],
            'has_blocker': True
        }

    if blocker_kw_in_all:
        return {
            'status': 'BLOCKED',
            'badge_class': 'badge-urgent',
            'reason': f"Blocker detected in update text ('{blocker_kw_in_all[0]}').",
            'keywords': blocker_kw_in_all,
            'has_blocker': True
        }

    # 2. Potential Issue condition
    if potential_kw_in_all:
        return {
            'status': 'POTENTIAL_ISSUE',
            'badge_class': 'badge-high',
            'reason': f"Potential risk or delay detected ('{potential_kw_in_all[0]}').",
            'keywords': potential_kw_in_all,
            'has_blocker': False
        }

    # 3. No Issue condition
    return {
        'status': 'NO_ISSUE',
        'badge_class': 'badge-active',
        'reason': "Progressing normally with no blockers reported.",
        'keywords': [],
        'has_blocker': False
    }


def generate_standup_summary(yesterday_work: str, today_plan: str, blockers: str = "", comments: str = "", status: str = None) -> str:
    """
    Generate a concise, factual 1-2 sentence AI summary of the stand-up update.
    Never hallucinates unmentioned items.
    """
    y_clean = (yesterday_work or "").strip().rstrip('.')
    t_clean = (today_plan or "").strip().rstrip('.')
    b_clean = (blockers or "").strip().rstrip('.')

    if not status:
        classification = classify_standup_text(yesterday_work, today_plan, blockers, comments)
        status = classification['status']

    # Normalize phrases
    if y_clean and t_clean:
        base = f"Completed {y_clean} and working on {t_clean}."
    elif y_clean:
        base = f"Completed {y_clean}."
    elif t_clean:
        base = f"Working on {t_clean}."
    else:
        base = "Submitted stand-up update."

    if status == 'BLOCKED' and not _is_benign_text(b_clean):
        return f"{base} Currently blocked: {b_clean}."
    elif status == 'POTENTIAL_ISSUE' and not _is_benign_text(b_clean):
        return f"{base} Potential issue noted: {b_clean}."
    elif status == 'BLOCKED':
        return f"{base} Currently blocked on current task."
    
    return base


def analyze_single_standup(standup: dict) -> dict:
    """Analyze a single stand-up record dict and return enriched analysis fields."""
    yesterday = standup.get('yesterday_work', '')
    today = standup.get('today_plan', '')
    blockers = standup.get('blockers', '')
    comments = standup.get('comments', '')

    classification = classify_standup_text(yesterday, today, blockers, comments)
    summary = generate_standup_summary(yesterday, today, blockers, comments, classification['status'])

    return {
        'id': standup.get('id'),
        'user_id': standup.get('user_id'),
        'username': standup.get('username', 'Developer'),
        'user_role': standup.get('user_role', 'Developer'),
        'date': standup.get('date'),
        'yesterday_work': yesterday,
        'today_plan': today,
        'blockers': blockers,
        'comments': comments,
        'status': classification['status'],
        'badge_class': classification['badge_class'],
        'reason': classification['reason'],
        'keywords': classification['keywords'],
        'summary': summary
    }


def detect_repeated_blockers(project_id: int, days: int = 7) -> list:
    """
    Analyze historical stand-ups for a project across recent days to flag repeated blockers.

    Returns list of dicts:
    [
        {
            'developer': str,
            'blocker': str,
            'consecutive_days': int,
            'message': str
        }
    ]
    """
    try:
        recent_updates = StandupUpdate.get_recent_standups(project_id, days=days)
    except Exception as e:
        logger.error(f"Failed to fetch recent standups for repeated blocker analysis: {e}")
        return []

    if not recent_updates:
        return []

    # Group by user_id
    user_updates = {}
    for u in recent_updates:
        uid = u['user_id']
        if uid not in user_updates:
            user_updates[uid] = []
        user_updates[uid].append(dict(u))

    repeated_alerts = []

    for uid, u_list in user_updates.items():
        # Sort chronologically by date
        sorted_list = sorted(u_list, key=lambda x: x.get('date', ''))
        
        # Filter for updates with active blockers
        blocked_entries = []
        for entry in sorted_list:
            b_text = entry.get('blockers', '')
            if not _is_benign_text(b_text):
                blocked_entries.append((entry.get('date'), b_text, entry.get('username', 'Developer')))

        if len(blocked_entries) < 2:
            continue

        # Check similarity between consecutive blocker entries
        match_streak = 1
        last_blocker = blocked_entries[0][1]
        last_user = blocked_entries[0][2]
        
        for i in range(1, len(blocked_entries)):
            curr_date, curr_blocker, curr_user = blocked_entries[i]
            
            # String similarity calculation
            norm_last = re.sub(r'[^\w\s]', '', last_blocker.lower()).strip()
            norm_curr = re.sub(r'[^\w\s]', '', curr_blocker.lower()).strip()
            
            similarity = SequenceMatcher(None, norm_last, norm_curr).ratio()
            
            # Check for keyword overlap as fallback
            words_last = set(norm_last.split())
            words_curr = set(norm_curr.split())
            overlap = len(words_last & words_curr)

            if similarity >= 0.55 or (overlap >= 2 and len(words_curr) > 0):
                match_streak += 1
            else:
                if match_streak >= 2:
                    repeated_alerts.append({
                        'developer': last_user,
                        'blocker': last_blocker,
                        'consecutive_days': match_streak,
                        'message': f"⚠ Repeated blocker detected: '{last_blocker}' has been mentioned as a blocker for {match_streak} consecutive updates."
                    })
                match_streak = 1
                last_blocker = curr_blocker
                last_user = curr_user

        if match_streak >= 2:
            repeated_alerts.append({
                'developer': last_user,
                'blocker': last_blocker,
                'consecutive_days': match_streak,
                'message': f"⚠ Repeated blocker detected: '{last_blocker}' has been mentioned as a blocker for {match_streak} consecutive updates."
            })

    return repeated_alerts


def generate_team_standup_summary(project_id: int, target_date: str = None) -> dict:
    """
    Generate comprehensive team-level daily stand-up analysis for the Scrum Master & Dashboard.

    Returns:
    {
        'has_updates': bool,
        'error': bool,
        'date': str,
        'total_updates_today': int,
        'developers_reported': int,
        'total_team_devs': int,
        'reporting_ratio_str': str,
        'blocker_count': int,
        'potential_issue_count': int,
        'no_issue_count': int,
        'high_priority_blockers': list,
        'potential_issues': list,
        'no_issue_devs': list,
        'repeated_blockers': list,
        'analyzed_standups': list
    }
    """
    if not target_date:
        target_date = date.today().isoformat()

    try:
        updates_raw = StandupUpdate.get_by_project(project_id, date=target_date)
        updates = [dict(u) for u in updates_raw]

        # Get total developers in project
        members = Project.get_members(project_id)
        dev_members = [m for m in members if m.get('role_in_project') == 'Developer']
        total_dev_count = len(dev_members) if dev_members else max(len(updates), 1)

        analyzed_standups = [analyze_single_standup(u) for u in updates]

        reported_users = set(u['username'] for u in analyzed_standups)
        developers_reported = len(reported_users)

        high_priority_blockers = []
        potential_issues = []
        no_issue_devs = []

        for item in analyzed_standups:
            if item['status'] == 'BLOCKED':
                high_priority_blockers.append({
                    'developer': item['username'],
                    'blocker': item['blockers'] if not _is_benign_text(item['blockers']) else item['reason'],
                    'reason': item['reason'],
                    'summary': item['summary']
                })
            elif item['status'] == 'POTENTIAL_ISSUE':
                potential_issues.append({
                    'developer': item['username'],
                    'issue': item['blockers'] if not _is_benign_text(item['blockers']) else item['reason'],
                    'reason': item['reason'],
                    'summary': item['summary']
                })
            else:
                no_issue_devs.append(item['username'])

        repeated_blockers = detect_repeated_blockers(project_id, days=7)

        return {
            'has_updates': len(analyzed_standups) > 0,
            'error': False,
            'date': target_date,
            'total_updates_today': len(analyzed_standups),
            'developers_reported': developers_reported,
            'total_team_devs': total_dev_count,
            'reporting_ratio_str': f"{developers_reported}/{total_dev_count} developers reported",
            'blocker_count': len(high_priority_blockers),
            'potential_issue_count': len(potential_issues),
            'no_issue_count': len(no_issue_devs),
            'high_priority_blockers': high_priority_blockers,
            'potential_issues': potential_issues,
            'no_issue_devs': no_issue_devs,
            'repeated_blockers': repeated_blockers,
            'analyzed_standups': analyzed_standups
        }

    except Exception as e:
        logger.error(f"Error generating team stand-up summary for project {project_id}: {e}", exc_info=True)
        return {
            'has_updates': False,
            'error': True,
            'message': "AI stand-up analysis is currently unavailable.",
            'date': target_date,
            'total_updates_today': 0,
            'developers_reported': 0,
            'total_team_devs': 0,
            'reporting_ratio_str': "0/0 developers reported",
            'blocker_count': 0,
            'potential_issue_count': 0,
            'no_issue_count': 0,
            'high_priority_blockers': [],
            'potential_issues': [],
            'no_issue_devs': [],
            'repeated_blockers': [],
            'analyzed_standups': []
        }
