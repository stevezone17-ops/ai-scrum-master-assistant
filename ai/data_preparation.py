"""
ai/data_preparation.py
=======================
Step 11A: AI Data Preparation for Sprint Risk Prediction

Collects real sprint data from the SQLite database, engineers ML features,
assigns rule-based risk labels, and produces a clean Pandas DataFrame
ready for model training in a later step.

NO model training is performed here.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from database.db import get_db


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

FEATURE_COLUMNS = [
    'total_tasks',
    'completed_tasks',
    'pending_tasks',
    'overdue_tasks',
    'total_story_points',
    'completed_story_points',
    'developer_count',
    'estimated_hours',
    'actual_hours',
    'days_allocated',
    'days_remaining',
    'previous_velocity',
    'bug_count',
    'high_priority_tasks',
    'task_completion_rate',
    'story_point_completion_rate',
    'hours_variance',
]

TARGET_COLUMN = 'risk_label'


# ---------------------------------------------------------------------------
# SECTION 1: RAW DATA EXTRACTION FROM SQLITE
# ---------------------------------------------------------------------------

def _extract_sprints_raw(conn) -> pd.DataFrame:
    """Pull all sprints with their project metadata."""
    query = """
        SELECT
            s.id            AS sprint_id,
            s.project_id,
            s.name          AS sprint_name,
            s.status,
            s.start_date,
            s.end_date
        FROM sprints s
        ORDER BY s.project_id, s.start_date
    """
    return pd.read_sql_query(query, conn)


def _extract_tasks_per_sprint(conn) -> pd.DataFrame:
    """Aggregate task metrics grouped by sprint_id."""
    query = """
        SELECT
            t.sprint_id,
            COUNT(*)                                                     AS total_tasks,
            SUM(CASE WHEN t.status = 'Done'         THEN 1 ELSE 0 END)  AS completed_tasks,
            SUM(CASE WHEN t.status != 'Done'        THEN 1 ELSE 0 END)  AS pending_tasks,
            SUM(CASE WHEN t.priority IN ('Critical','High') THEN 1 ELSE 0 END) AS high_priority_tasks,
            COALESCE(SUM(t.estimated_hours), 0)                         AS estimated_hours,
            COALESCE(SUM(t.actual_hours), 0)                            AS actual_hours,
            -- Overdue: not Done AND due_date < today
            SUM(
                CASE
                    WHEN t.status != 'Done'
                     AND t.due_date IS NOT NULL
                     AND t.due_date < DATE('now')
                    THEN 1 ELSE 0
                END
            ) AS overdue_tasks
        FROM tasks t
        WHERE t.sprint_id IS NOT NULL
        GROUP BY t.sprint_id
    """
    return pd.read_sql_query(query, conn)


def _extract_story_points_per_sprint(conn) -> pd.DataFrame:
    """Aggregate user story points grouped by sprint_id."""
    query = """
        SELECT
            us.sprint_id,
            COALESCE(SUM(us.story_points), 0)                               AS total_story_points,
            COALESCE(SUM(CASE WHEN us.status = 'Done' THEN us.story_points ELSE 0 END), 0) AS completed_story_points
        FROM user_stories us
        WHERE us.sprint_id IS NOT NULL
        GROUP BY us.sprint_id
    """
    return pd.read_sql_query(query, conn)


def _extract_developer_counts(conn) -> pd.DataFrame:
    """Count distinct developers assigned to tasks in each sprint."""
    query = """
        SELECT
            t.sprint_id,
            COUNT(DISTINCT t.assigned_to) AS developer_count
        FROM tasks t
        WHERE t.sprint_id IS NOT NULL
          AND t.assigned_to IS NOT NULL
        GROUP BY t.sprint_id
    """
    return pd.read_sql_query(query, conn)


def _extract_bug_counts(conn) -> pd.DataFrame:
    """Count bugs (open) per sprint."""
    query = """
        SELECT
            b.sprint_id,
            COUNT(*) AS bug_count
        FROM bugs b
        WHERE b.sprint_id IS NOT NULL
          AND b.status != 'Closed'
        GROUP BY b.sprint_id
    """
    return pd.read_sql_query(query, conn)


def _extract_previous_velocity(conn) -> pd.DataFrame:
    """For each sprint, calculate the avg completed story points
    from all *prior completed* sprints in the same project (velocity baseline)."""
    query = """
        SELECT
            s1.id AS sprint_id,
            COALESCE(
                AVG(
                    CASE WHEN s2.status = 'Completed' AND s2.end_date < s1.start_date
                    THEN (
                        SELECT COALESCE(SUM(us.story_points), 0)
                        FROM user_stories us
                        WHERE us.sprint_id = s2.id AND us.status = 'Done'
                    )
                    END
                ),
                0.0
            ) AS previous_velocity
        FROM sprints s1
        JOIN sprints s2 ON s2.project_id = s1.project_id AND s2.id != s1.id
        GROUP BY s1.id
    """
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        # Fallback: return empty DF; will be filled with 0 later
        return pd.DataFrame(columns=['sprint_id', 'previous_velocity'])


# ---------------------------------------------------------------------------
# SECTION 2: FEATURE ENGINEERING
# ---------------------------------------------------------------------------

def _calculate_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add days_allocated and days_remaining columns."""
    today = date.today()

    def _parse_date(d):
        if pd.isna(d) or d == '':
            return None
        try:
            return datetime.strptime(str(d).strip(), '%Y-%m-%d').date()
        except ValueError:
            return None

    df = df.copy()
    df['_start'] = df['start_date'].apply(_parse_date)
    df['_end'] = df['end_date'].apply(_parse_date)

    def _days_allocated(row):
        if row['_start'] and row['_end']:
            delta = (row['_end'] - row['_start']).days
            return max(delta, 1)
        return 14  # sensible default

    def _days_remaining(row):
        if row['_end']:
            delta = (row['_end'] - today).days
            return max(delta, 0)
        return 0

    df['days_allocated'] = df.apply(_days_allocated, axis=1)
    df['days_remaining'] = df.apply(_days_remaining, axis=1)
    df.drop(columns=['_start', '_end'], inplace=True)
    return df


def _calculate_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rate/variance features with safe division."""
    df = df.copy()

    # Task Completion Rate
    df['task_completion_rate'] = np.where(
        df['total_tasks'] > 0,
        df['completed_tasks'] / df['total_tasks'],
        0.0
    ).round(4)

    # Story Point Completion Rate
    df['story_point_completion_rate'] = np.where(
        df['total_story_points'] > 0,
        df['completed_story_points'] / df['total_story_points'],
        0.0
    ).round(4)

    # Hours Variance (actual - estimated; positive = over-ran)
    df['hours_variance'] = (df['actual_hours'] - df['estimated_hours']).round(2)

    return df


# ---------------------------------------------------------------------------
# SECTION 3: RISK LABEL CLASSIFICATION (Rule-Based)
# ---------------------------------------------------------------------------

def classify_risk_label(row: pd.Series) -> str:
    """
    Rule-based risk label assignment for historical sprint data.

    Kept in a standalone function so it can be swapped/extended without
    touching the rest of the pipeline.

    Returns: 'HIGH' | 'MEDIUM' | 'LOW'
    """
    completion_rate = row.get('task_completion_rate', 0.0)
    sp_completion    = row.get('story_point_completion_rate', 0.0)
    overdue          = row.get('overdue_tasks', 0)
    total_tasks      = row.get('total_tasks', 0)
    days_remaining   = row.get('days_remaining', 0)
    days_allocated   = max(row.get('days_allocated', 1), 1)
    hours_variance   = row.get('hours_variance', 0.0)
    estimated_hours  = max(row.get('estimated_hours', 1.0), 1.0)

    overdue_ratio       = overdue / max(total_tasks, 1)
    days_remaining_pct  = days_remaining / days_allocated
    hours_over_pct      = hours_variance / estimated_hours

    # ---- HIGH risk conditions -----------------------------------------------
    high_conditions = [
        completion_rate < 0.25 and days_remaining_pct < 0.20,   # Very behind, almost no time
        overdue_ratio > 0.40,                                    # >40% tasks overdue
        sp_completion < 0.15 and days_remaining_pct < 0.30,     # Barely started, little time
        hours_over_pct > 0.50 and completion_rate < 0.50,       # Way over budget + low done
    ]
    if any(high_conditions):
        return 'HIGH'

    # ---- MEDIUM risk conditions ----------------------------------------------
    medium_conditions = [
        0.25 <= completion_rate < 0.60 and days_remaining_pct < 0.40,
        overdue_ratio > 0.15,
        hours_over_pct > 0.20,
        sp_completion < 0.40 and days_remaining_pct < 0.50,
    ]
    if any(medium_conditions):
        return 'MEDIUM'

    # ---- LOW risk (default) -------------------------------------------------
    return 'LOW'


# ---------------------------------------------------------------------------
# SECTION 4: DATA CLEANING
# ---------------------------------------------------------------------------

def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply data-quality rules:
    - Fill numeric NaNs with 0 (no records are silently dropped).
    - Clamp negative hours to 0.
    - Ensure rates are in [0, 1].
    - Drop rows where sprint_id is null (should never happen, but guard anyway).
    """
    df = df.copy()

    # Drop rows with no sprint_id (data integrity guard)
    df.dropna(subset=['sprint_id'], inplace=True)

    # Numeric fill
    numeric_cols = [
        'total_tasks', 'completed_tasks', 'pending_tasks', 'overdue_tasks',
        'total_story_points', 'completed_story_points',
        'developer_count', 'estimated_hours', 'actual_hours',
        'days_allocated', 'days_remaining', 'previous_velocity',
        'bug_count', 'high_priority_tasks',
        'task_completion_rate', 'story_point_completion_rate', 'hours_variance',
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Clamp negative hours to 0 (guards against bad seed data)
    for col in ['estimated_hours', 'actual_hours']:
        if col in df.columns:
            df[col] = df[col].clip(lower=0.0)

    # Clamp rates to [0, 1]
    for col in ['task_completion_rate', 'story_point_completion_rate']:
        if col in df.columns:
            df[col] = df[col].clip(0.0, 1.0)

    return df


# ---------------------------------------------------------------------------
# SECTION 5: MAIN PIPELINE — REAL DB DATA
# ---------------------------------------------------------------------------

def extract_sprint_dataset() -> pd.DataFrame:
    """
    Full pipeline: extract → merge → engineer features → label → clean.

    Returns a DataFrame with FEATURE_COLUMNS + TARGET_COLUMN,
    indexed by sprint_id.
    """
    conn = get_db()
    try:
        sprints_df      = _extract_sprints_raw(conn)
        tasks_df        = _extract_tasks_per_sprint(conn)
        stories_df      = _extract_story_points_per_sprint(conn)
        devs_df         = _extract_developer_counts(conn)
        bugs_df         = _extract_bug_counts(conn)
        prev_vel_df     = _extract_previous_velocity(conn)
    finally:
        conn.close()

    if sprints_df.empty:
        return pd.DataFrame(columns=['sprint_id'] + FEATURE_COLUMNS + [TARGET_COLUMN])

    # Merge all frames on sprint_id
    df = sprints_df.copy()
    df = df.merge(tasks_df,    on='sprint_id', how='left')
    df = df.merge(stories_df,  on='sprint_id', how='left')
    df = df.merge(devs_df,     on='sprint_id', how='left')
    df = df.merge(bugs_df,     on='sprint_id', how='left')
    df = df.merge(prev_vel_df, on='sprint_id', how='left')

    # Date features
    df = _calculate_date_features(df)

    # Clean / fill numeric types
    df = _clean_dataframe(df)

    # Derived numeric features
    df = _calculate_derived_features(df)

    # Assign risk label
    df[TARGET_COLUMN] = df.apply(classify_risk_label, axis=1)

    # Keep only the columns we need for ML
    keep_cols = ['sprint_id', 'sprint_name', 'status'] + FEATURE_COLUMNS + [TARGET_COLUMN]
    existing  = [c for c in keep_cols if c in df.columns]
    df = df[existing].copy()

    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# SECTION 6: SYNTHETIC DATASET GENERATOR (ML Experimentation Only)
# ---------------------------------------------------------------------------

def generate_synthetic_dataset(n_samples: int = 200, random_seed: int = 42) -> pd.DataFrame:
    """
    Generate a realistic synthetic sprint dataset for ML experimentation.

    WARNING: Do NOT insert these records into the production database.
    This is purely for offline model training / experimentation.
    """
    rng = np.random.default_rng(random_seed)

    total_tasks            = rng.integers(4, 25, n_samples).astype(float)
    days_allocated         = rng.integers(7, 21, n_samples).astype(float)
    completed_frac         = rng.uniform(0.0, 1.0, n_samples)
    completed_tasks        = np.floor(total_tasks * completed_frac)
    pending_tasks          = total_tasks - completed_tasks
    overdue_tasks          = np.floor(rng.uniform(0.0, 0.5, n_samples) * pending_tasks)
    total_story_points     = rng.integers(8, 60, n_samples).astype(float)
    sp_done_frac           = rng.uniform(0.0, 1.0, n_samples)
    completed_story_points = np.floor(total_story_points * sp_done_frac)
    developer_count        = rng.integers(1, 6, n_samples).astype(float)
    estimated_hours        = rng.uniform(20, 200, n_samples).round(1)
    hours_over_frac        = rng.uniform(-0.2, 0.6, n_samples)
    actual_hours           = np.clip(estimated_hours * (1 + hours_over_frac), 0, None).round(1)
    days_remaining         = np.clip(
        rng.integers(0, days_allocated.astype(int) + 1, n_samples).astype(float),
        0, days_allocated
    )
    previous_velocity      = rng.uniform(5, 50, n_samples).round(1)
    bug_count              = rng.integers(0, 8, n_samples).astype(float)
    high_priority_tasks    = np.minimum(
        rng.integers(0, 6, n_samples).astype(float), total_tasks
    )

    task_completion_rate         = np.where(total_tasks > 0, completed_tasks / total_tasks, 0.0)
    story_point_completion_rate  = np.where(total_story_points > 0, completed_story_points / total_story_points, 0.0)
    hours_variance               = (actual_hours - estimated_hours).round(2)

    df = pd.DataFrame({
        'sprint_id':                  [f'SYN-{i+1:04d}' for i in range(n_samples)],
        'sprint_name':                [f'Synthetic Sprint {i+1}' for i in range(n_samples)],
        'status':                     'Synthetic',
        'total_tasks':                total_tasks,
        'completed_tasks':            completed_tasks,
        'pending_tasks':              pending_tasks,
        'overdue_tasks':              overdue_tasks,
        'total_story_points':         total_story_points,
        'completed_story_points':     completed_story_points,
        'developer_count':            developer_count,
        'estimated_hours':            estimated_hours,
        'actual_hours':               actual_hours,
        'days_allocated':             days_allocated,
        'days_remaining':             days_remaining,
        'previous_velocity':          previous_velocity,
        'bug_count':                  bug_count,
        'high_priority_tasks':        high_priority_tasks,
        'task_completion_rate':       task_completion_rate.round(4),
        'story_point_completion_rate': story_point_completion_rate.round(4),
        'hours_variance':             hours_variance,
    })

    df[TARGET_COLUMN] = df.apply(classify_risk_label, axis=1)
    return df


# ---------------------------------------------------------------------------
# SECTION 7: COMBINED DATASET (REAL + SYNTHETIC AUGMENTATION)
# ---------------------------------------------------------------------------

def get_combined_dataset(min_real_records: int = 10) -> pd.DataFrame:
    """
    Return the real dataset. If it has fewer than `min_real_records` rows,
    augment with synthetic data so ML training has sufficient samples.

    Synthetic rows are clearly flagged via status == 'Synthetic'.
    """
    real_df = extract_sprint_dataset()
    n_real  = len(real_df)

    if n_real >= min_real_records:
        return real_df

    n_synthetic = max(min_real_records * 5, 150)
    syn_df      = generate_synthetic_dataset(n_samples=n_synthetic)
    combined    = pd.concat([real_df, syn_df], ignore_index=True)
    return combined


# ---------------------------------------------------------------------------
# SECTION 8: X / y SPLIT FOR ML
# ---------------------------------------------------------------------------

def prepare_for_ml(df: pd.DataFrame = None):
    """
    Return (X, y) where:
      X — DataFrame of FEATURE_COLUMNS (all numeric)
      y — Series of risk_label strings

    If `df` is None, fetches the combined dataset automatically.
    Does NOT train any model.
    """
    if df is None:
        df = get_combined_dataset()

    available_features = [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[available_features].copy()
    y = df[TARGET_COLUMN].copy() if TARGET_COLUMN in df.columns else pd.Series(dtype=str)
    return X, y


# ---------------------------------------------------------------------------
# SECTION 9: DATA VALIDATION REPORT
# ---------------------------------------------------------------------------

def validate_dataset(df: pd.DataFrame = None) -> dict:
    """
    Print and return a validation summary:
      - Shape
      - Missing values per column
      - Risk label distribution
      - Basic statistics for numeric columns
    """
    if df is None:
        df = get_combined_dataset()

    n_records  = len(df)
    n_features = len([c for c in FEATURE_COLUMNS if c in df.columns])
    missing    = df[FEATURE_COLUMNS].isnull().sum().to_dict()
    missing    = {k: int(v) for k, v in missing.items() if v > 0}

    label_dist = {}
    if TARGET_COLUMN in df.columns:
        label_dist = df[TARGET_COLUMN].value_counts().to_dict()

    numeric_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    stats = df[numeric_cols].describe().round(3).to_dict()

    report = {
        'n_records':        n_records,
        'n_features':       n_features,
        'missing_values':   missing,
        'risk_distribution': label_dist,
        'statistics':       stats,
    }

    # Pretty-print
    print(f"\n{'='*50}")
    print(f"  AI Data Preparation — Dataset Validation")
    print(f"{'='*50}")
    print(f"  Dataset shape  : ({n_records}, {n_features})")
    print(f"  Missing values : {missing if missing else 'None'}")
    print(f"\n  Risk distribution:")
    for label, count in sorted(label_dist.items()):
        bar = '#' * (count // max(1, n_records // 20))
        print(f"    {label:<8}: {count:>4}  {bar}")
    print(f"{'='*50}\n")

    return report
