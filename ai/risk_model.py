"""
ai/risk_model.py
=================
Step 11B: Machine Learning Model Training for Sprint Risk Prediction

Trains a RandomForestClassifier on prepared sprint data, evaluates it,
and provides save/load/predict utilities.

Architecture Decisions (for project presentation):
---------------------------------------------------
- **Why Random Forest?**
  Random Forest is an ensemble of decision trees.  It handles mixed numeric
  features well, is resistant to overfitting on small datasets, provides
  built-in feature importance, and produces interpretable results — all
  critical for an Agile risk tool that a Scrum Master needs to trust.

- **What features are used?**
  17 numeric features extracted from sprint task data, story points, hours,
  dates, bugs, and team composition.  See data_preparation.FEATURE_COLUMNS.

- **What are the target labels?**
  LOW   — Sprint is on track; few/no overdue tasks, steady velocity.
  MEDIUM — Moderate risk; some overdue tasks or lagging completion.
  HIGH  — Critical risk; heavy overdue ratio, very little time remaining.

- **How does the model predict risk?**
  Each tree in the forest votes on a risk class.  The class receiving
  the majority of votes becomes the final prediction.  Probability is
  the fraction of trees voting for each class.

- **How is feature importance calculated?**
  Mean Decrease in Impurity (MDI) — averaged over all trees.  Features
  that appear higher in trees and split more samples get higher scores.

Synthetic-Data Notice:
  This is a college project.  If the production database contains fewer
  than ~10 historical sprints, training uses a synthetic dataset generated
  by ai.data_preparation.generate_synthetic_dataset().  Synthetic records
  are NEVER inserted into the production SQLite database.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
import joblib

from ai.data_preparation import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    get_combined_dataset,
    prepare_for_ml,
)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

_MODEL_DIR  = os.path.join(os.path.dirname(__file__), 'models')
_MODEL_PATH = os.path.join(_MODEL_DIR, 'sprint_risk_model.joblib')
_META_PATH  = os.path.join(_MODEL_DIR, 'sprint_risk_meta.json')

LABEL_ORDER = ['LOW', 'MEDIUM', 'HIGH']   # consistent ordering


# ---------------------------------------------------------------------------
# 1. TRAINING
# ---------------------------------------------------------------------------

def train_model(
    test_size: float = 0.20,
    random_state: int = 42,
    n_estimators: int = 100,
    max_depth: int = 10,
    min_real_records: int = 10,
    verbose: bool = True,
) -> dict:
    """
    End-to-end training pipeline.

    Returns a dict with keys:
        model, scaler, label_encoder, evaluation, feature_importance,
        model_info, X_train, X_test, y_train, y_test
    """

    # --- 1. Fetch & prepare data -------------------------------------------
    dataset = get_combined_dataset(min_real_records=min_real_records)
    X, y = prepare_for_ml(dataset)

    n_samples  = len(X)
    n_features = X.shape[1]
    label_dist = y.value_counts().to_dict()

    if verbose:
        print(f"\n--- Sprint Risk Model Training ---")
        print(f"  Samples  : {n_samples}")
        print(f"  Features : {n_features}")
        print(f"  Labels   : {label_dist}")

    # --- 2. Encode labels --------------------------------------------------
    le = LabelEncoder()
    le.fit(LABEL_ORDER)          # force consistent LOW=0, MEDIUM=1, HIGH=2
    y_encoded = le.transform(y)

    # --- 3. Scale features -------------------------------------------------
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # --- 4. Train/test split -----------------------------------------------
    # Check that every class has >= 2 samples so stratify is possible
    min_class_count = min(label_dist.get(l, 0) for l in LABEL_ORDER if l in label_dist)
    can_stratify = min_class_count >= 2

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_encoded,
        test_size=test_size,
        random_state=random_state,
        stratify=y_encoded if can_stratify else None,
    )

    if verbose:
        print(f"  Train    : {len(X_train)} samples")
        print(f"  Test     : {len(X_test)} samples")
        print(f"  Stratify : {'Yes' if can_stratify else 'No (class too small)'}")

    # --- 5. Train RandomForest ---------------------------------------------
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        class_weight='balanced',      # handles class imbalance
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # --- 6. Evaluation -----------------------------------------------------
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    accuracy  = round(accuracy_score(y_test, y_pred), 4)
    precision = round(precision_score(y_test, y_pred, average='weighted', zero_division=0), 4)
    recall_   = round(recall_score(y_test, y_pred, average='weighted', zero_division=0), 4)
    f1        = round(f1_score(y_test, y_pred, average='weighted', zero_division=0), 4)
    conf_mtx  = confusion_matrix(y_test, y_pred, labels=le.transform(LABEL_ORDER)).tolist()
    cls_report = classification_report(
        y_test, y_pred,
        target_names=LABEL_ORDER,
        zero_division=0,
        output_dict=True,
    )

    evaluation = {
        'accuracy':             accuracy,
        'precision':            precision,
        'recall':               recall_,
        'f1_score':             f1,
        'confusion_matrix':     conf_mtx,
        'classification_report': cls_report,
    }

    if verbose:
        print(f"\n  Accuracy  : {accuracy}")
        print(f"  Precision : {precision}")
        print(f"  Recall    : {recall_}")
        print(f"  F1 Score  : {f1}")
        print(f"  Confusion Matrix:")
        for row in conf_mtx:
            print(f"    {row}")

    # --- 7. Cross-validation (if enough data) ------------------------------
    cv_scores = None
    if n_samples >= 30 and min_class_count >= 3:
        n_splits = min(5, min_class_count)
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        cv_raw = cross_val_score(model, X_scaled, y_encoded, cv=skf, scoring='accuracy')
        cv_scores = {
            'mean': round(float(cv_raw.mean()), 4),
            'std':  round(float(cv_raw.std()), 4),
            'folds': [round(float(s), 4) for s in cv_raw],
        }
        if verbose:
            print(f"  CV Accuracy : {cv_scores['mean']} (+/- {cv_scores['std']})")
    elif verbose:
        print(f"  CV skipped  : not enough data ({n_samples} samples)")

    evaluation['cross_validation'] = cv_scores

    # --- 8. Feature importance ---------------------------------------------
    importances = model.feature_importances_
    feature_names = list(X.columns)
    importance_pairs = sorted(
        zip(feature_names, importances),
        key=lambda x: x[1],
        reverse=True,
    )
    feature_importance = [
        {'feature': name, 'importance': round(float(imp), 4)}
        for name, imp in importance_pairs
    ]

    if verbose:
        print(f"\n  Top 5 Important Features:")
        for fi in feature_importance[:5]:
            bar = '#' * int(fi['importance'] * 40)
            print(f"    {fi['feature']:<30} {fi['importance']:.4f}  {bar}")

    # --- 9. Model metadata -------------------------------------------------
    model_info = {
        'model_name':      'RandomForestClassifier',
        'n_estimators':     n_estimators,
        'max_depth':        max_depth,
        'training_samples': n_samples,
        'test_samples':     len(X_test),
        'feature_count':    n_features,
        'features':         feature_names,
        'labels':           LABEL_ORDER,
        'accuracy':         accuracy,
        'f1_score':         f1,
        'training_date':    datetime.now().isoformat(timespec='seconds'),
        'data_source':      'real+synthetic' if n_samples > len(get_combined_dataset(min_real_records=999999)) else 'combined',
    }

    return {
        'model':              model,
        'scaler':             scaler,
        'label_encoder':      le,
        'evaluation':         evaluation,
        'feature_importance': feature_importance,
        'model_info':         model_info,
        'X_train': X_train, 'X_test': X_test,
        'y_train': y_train, 'y_test': y_test,
    }


# ---------------------------------------------------------------------------
# 2. SAVING
# ---------------------------------------------------------------------------

def save_model(training_result: dict, model_path: str = None, meta_path: str = None):
    """
    Persist model + scaler + label_encoder + metadata to disk.

    Saves to ai/models/ by default.  Creates the directory if missing.
    """
    model_path = model_path or _MODEL_PATH
    meta_path  = meta_path  or _META_PATH

    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    bundle = {
        'model':         training_result['model'],
        'scaler':        training_result['scaler'],
        'label_encoder': training_result['label_encoder'],
    }
    joblib.dump(bundle, model_path)

    meta = {
        'model_info':         training_result['model_info'],
        'evaluation':         training_result['evaluation'],
        'feature_importance': training_result['feature_importance'],
    }
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    print(f"  Model saved to : {model_path}")
    print(f"  Meta  saved to : {meta_path}")


# ---------------------------------------------------------------------------
# 3. LOADING
# ---------------------------------------------------------------------------

def load_model(model_path: str = None, meta_path: str = None) -> dict:
    """
    Load a previously saved model from disk.

    Returns dict with keys: model, scaler, label_encoder, model_info,
    evaluation, feature_importance.

    Raises FileNotFoundError if the model file doesn't exist.
    """
    model_path = model_path or _MODEL_PATH
    meta_path  = meta_path  or _META_PATH

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"No trained model found at {model_path}. "
            f"Call train_model() and save_model() first."
        )

    bundle = joblib.load(model_path)

    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)

    return {
        'model':              bundle['model'],
        'scaler':             bundle['scaler'],
        'label_encoder':      bundle['label_encoder'],
        'model_info':         meta.get('model_info', {}),
        'evaluation':         meta.get('evaluation', {}),
        'feature_importance': meta.get('feature_importance', []),
    }


# ---------------------------------------------------------------------------
# 4. PREDICTION
# ---------------------------------------------------------------------------

def predict_sprint_risk(features: dict, loaded_model: dict = None) -> dict:
    """
    Predict risk for a single sprint given its feature dictionary.

    Parameters
    ----------
    features : dict
        Keys should match FEATURE_COLUMNS.  Missing keys default to 0.
    loaded_model : dict, optional
        Output of load_model().  If None, loads from default path.

    Returns
    -------
    dict:
        {
            "risk": "HIGH",
            "probabilities": {"LOW": 0.05, "MEDIUM": 0.20, "HIGH": 0.75},
            "confidence": 0.75
        }
    """
    if loaded_model is None:
        loaded_model = load_model()

    model  = loaded_model['model']
    scaler = loaded_model['scaler']
    le     = loaded_model['label_encoder']

    # Build feature vector in correct column order
    feature_values = [float(features.get(col, 0.0)) for col in FEATURE_COLUMNS]
    X_input = np.array([feature_values])
    X_scaled = scaler.transform(X_input)

    prediction = model.predict(X_scaled)[0]
    probas     = model.predict_proba(X_scaled)[0]

    risk_label = le.inverse_transform([prediction])[0]

    # Map probabilities to label names (order matches le.classes_)
    prob_dict = {}
    for idx, cls_encoded in enumerate(model.classes_):
        cls_name = le.inverse_transform([cls_encoded])[0]
        prob_dict[cls_name] = round(float(probas[idx]), 4)

    confidence = round(float(max(probas)), 4)

    return {
        'risk':          risk_label,
        'probabilities': prob_dict,
        'confidence':    confidence,
    }


# ---------------------------------------------------------------------------
# 5. MODEL INFORMATION
# ---------------------------------------------------------------------------

def get_model_info(loaded_model: dict = None) -> dict:
    """
    Return human-readable model information for dashboards/reports.

    Keys: model_name, training_samples, feature_count, accuracy,
    important_features (top-5), training_date.
    """
    if loaded_model is None:
        loaded_model = load_model()

    info = loaded_model.get('model_info', {})
    fi   = loaded_model.get('feature_importance', [])

    return {
        'model_name':         info.get('model_name', 'Unknown'),
        'training_samples':   info.get('training_samples', 0),
        'feature_count':      info.get('feature_count', 0),
        'accuracy':           info.get('accuracy', 0.0),
        'f1_score':           info.get('f1_score', 0.0),
        'labels':             info.get('labels', LABEL_ORDER),
        'important_features': fi[:5],
        'training_date':      info.get('training_date', ''),
    }


# ---------------------------------------------------------------------------
# 6. CONVENIENCE: TRAIN + SAVE IN ONE CALL
# ---------------------------------------------------------------------------

def train_and_save(**kwargs) -> dict:
    """Train the model and immediately persist it.  Returns training_result."""
    result = train_model(**kwargs)
    save_model(result)
    return result
