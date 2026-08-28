import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

class AgileRiskPredictor:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=50, random_state=42)
        self.scaler = StandardScaler()
        self._train_initial_model()

    def _train_initial_model(self):
        """Train a Scikit-Learn RandomForestClassifier on synthetic Agile sprint datasets."""
        np.random.seed(42)
        n_samples = 300
        
        # Features:
        # 1. completion_rate (0.0 to 1.0)
        # 2. days_remaining_ratio (0.0 to 1.0)
        # 3. overdue_ratio (0.0 to 1.0)
        # 4. max_workload_share (0.2 to 0.8)
        # 5. bug_ratio (0.0 to 0.5)
        # 6. velocity_ratio (0.5 to 1.5)
        
        completion_rate = np.random.uniform(0.1, 1.0, n_samples)
        days_remaining_ratio = np.random.uniform(0.05, 1.0, n_samples)
        overdue_ratio = np.random.uniform(0.0, 0.5, n_samples)
        max_workload_share = np.random.uniform(0.2, 0.7, n_samples)
        bug_ratio = np.random.uniform(0.0, 0.4, n_samples)
        velocity_ratio = np.random.uniform(0.6, 1.4, n_samples)

        X = np.column_stack([
            completion_rate,
            days_remaining_ratio,
            overdue_ratio,
            max_workload_share,
            bug_ratio,
            velocity_ratio
        ])

        # Target: Risk level 0: Low, 1: Medium, 2: High
        y = []
        for i in range(n_samples):
            comp = completion_rate[i]
            time_left = days_remaining_ratio[i]
            overdue = overdue_ratio[i]
            bugs = bug_ratio[i]
            workload = max_workload_share[i]

            # Heuristic ground truth for ML classifier
            risk_score = (1 - comp) * 0.4 + (1 - time_left) * 0.2 + overdue * 0.25 + bugs * 0.15 + (workload - 0.3) * 0.2
            
            if risk_score < 0.35:
                y.append(0) # LOW
            elif risk_score < 0.58:
                y.append(1) # MEDIUM
            else:
                y.append(2) # HIGH

        y = np.array(y)

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict_sprint_risk(self, metrics):
        """
        Input metrics dictionary:
        {
          'total_tasks': int,
          'completed_tasks': int,
          'pending_tasks': int,
          'overdue_tasks': int,
          'days_total': int,
          'days_remaining': int,
          'max_dev_tasks': int,
          'avg_dev_tasks': float,
          'open_bugs': int,
          'previous_velocity': float,
          'current_velocity': float
        }
        """
        total_tasks = metrics.get('total_tasks', 0)
        if total_tasks == 0:
            return {
                'risk_level': 'LOW',
                'risk_score': 0.1,
                'predicted_completion': 100.0,
                'confidence': 'High',
                'recommendations': ["No tasks in sprint. Sprint scope is clear."]
            }

        completed_tasks = metrics.get('completed_tasks', 0)
        overdue_tasks = metrics.get('overdue_tasks', 0)
        days_total = max(metrics.get('days_total', 14), 1)
        days_remaining = max(metrics.get('days_remaining', 0), 0)
        max_dev_tasks = metrics.get('max_dev_tasks', 0)
        open_bugs = metrics.get('open_bugs', 0)
        prev_vel = max(metrics.get('previous_velocity', 10.0), 1.0)
        curr_vel = metrics.get('current_velocity', completed_tasks)

        # Feature Extraction
        completion_rate = completed_tasks / float(total_tasks)
        days_remaining_ratio = days_remaining / float(days_total)
        overdue_ratio = overdue_tasks / float(total_tasks)
        max_workload_share = (max_dev_tasks / float(total_tasks)) if total_tasks > 0 else 0.3
        bug_ratio = open_bugs / float(total_tasks)
        velocity_ratio = min(max(curr_vel / float(prev_vel), 0.5), 1.5)

        features = np.array([[
            completion_rate,
            days_remaining_ratio,
            overdue_ratio,
            max_workload_share,
            bug_ratio,
            velocity_ratio
        ]])

        features_scaled = self.scaler.transform(features)
        prediction = self.model.predict(features_scaled)[0]
        probs = self.model.predict_proba(features_scaled)[0]

        risk_mapping = {0: 'LOW', 1: 'MEDIUM', 2: 'HIGH'}
        risk_level = risk_mapping.get(prediction, 'MEDIUM')

        # Estimated completion % based on velocity & time remaining
        expected_remaining_pace = (completion_rate + (days_remaining_ratio * velocity_ratio)) * 100.0
        predicted_completion = round(min(max(expected_remaining_pace, completion_rate * 100), 100.0), 1)

        # Generate rule-informed smart recommendations
        recommendations = []
        
        if overdue_tasks > 0:
            recommendations.append(f"⚠️ {overdue_tasks} task(s) are past their due date. Immediate review needed.")
        
        if max_workload_share > 0.45 and total_tasks > 3:
            recommendations.append("👥 High team workload imbalance detected. Consider reassigning items from overloaded developer.")

        if completion_rate < 0.5 and days_remaining_ratio < 0.3:
            recommendations.append("🚨 Sprint is at high risk of delay. Less than half completed with <30% time remaining.")
            recommendations.append("📌 Action: Move low-priority user stories back to Product Backlog.")

        if open_bugs >= 3:
            recommendations.append(f"🐛 {open_bugs} open bugs logged. Allocate developer capacity to bug fixing before adding new tasks.")

        if velocity_ratio < 0.7 and completed_tasks > 0:
            recommendations.append("📉 Current sprint velocity is below team baseline. Unblock technical impediments in daily standups.")

        if not recommendations:
            recommendations.append("✅ Sprint is progressing according to schedule. Velocity and task balance are optimal.")

        return {
            'risk_level': risk_level,
            'risk_score': round(probs[prediction] * 100, 1),
            'predicted_completion': predicted_completion,
            'completion_rate': round(completion_rate * 100, 1),
            'confidence': 'High' if probs[prediction] > 0.6 else 'Medium',
            'recommendations': recommendations
        }

# Global predictor instance
predictor = AgileRiskPredictor()
