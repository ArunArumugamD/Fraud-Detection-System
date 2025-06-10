import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import os
from typing import Dict, Tuple, Optional
import json
from datetime import datetime
from pathlib import Path

class FraudMLModel:
    """
    Machine Learning model for fraud detection
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        
        # Use absolute paths based on project root
        self.project_root = Path(__file__).parent.parent.parent  # Go up to project root
        self.models_dir = self.project_root / "models"
        self.model_path = self.models_dir / "fraud_detector_rf.pkl"
        self.scaler_path = self.models_dir / "scaler.pkl"
        self.encoders_path = self.models_dir / "encoders.pkl"
        
        # Try to load existing model
        self.load_model()
    
    def extract_features(self, transaction_data: Dict) -> np.ndarray:
        """
        Extract features from transaction data for ML model
        """
        features = []
        
        # Numerical features
        features.append(transaction_data.get('amount', 0))
        
        # Time-based features (if we had timestamp)
        # For now, we'll use hour of day simulation
        current_hour = datetime.now().hour
        features.append(current_hour)
        
        # Is weekend (0 or 1)
        is_weekend = 1 if datetime.now().weekday() >= 5 else 0
        features.append(is_weekend)
        
        # Categorical features - encoded
        # Payment method risk score
        payment_risk = {
            'credit_card': 0.2,
            'debit_card': 0.3,
            'prepaid_card': 0.8,
            'bank_transfer': 0.1,
            'cash': 0.5
        }
        features.append(payment_risk.get(transaction_data.get('payment_method', ''), 0.5))
        
        # Transaction type risk
        transaction_risk = {
            'purchase': 0.2,
            'withdrawal': 0.4,
            'transfer': 0.6,
            'deposit': 0.1,
            'payment': 0.3,
            'refund': 0.5
        }
        features.append(transaction_risk.get(transaction_data.get('transaction_type', ''), 0.5))
        
        # Merchant category risk
        category_risk = {
            'Food & Beverage': 0.1,
            'Retail': 0.2,
            'E-commerce': 0.3,
            'Electronics': 0.4,
            'Jewelry': 0.5,
            'Money Transfer': 0.7,
            'ATM': 0.6,
            'Gambling': 0.9
        }
        features.append(category_risk.get(transaction_data.get('merchant_category', ''), 0.5))
        
        # Cross-border transaction (0 or 1)
        is_cross_border = 1 if transaction_data.get('merchant_country') != transaction_data.get('transaction_country') else 0
        features.append(is_cross_border)
        
        # High-risk country (simplified)
        high_risk_countries = ['XX', 'YY', 'ZZ']
        merchant_risk = 1 if transaction_data.get('merchant_country') in high_risk_countries else 0
        transaction_risk = 1 if transaction_data.get('transaction_country') in high_risk_countries else 0
        features.append(merchant_risk)
        features.append(transaction_risk)
        
        # Device info available (0 or 1)
        has_device_info = 1 if transaction_data.get('device_id') else 0
        features.append(has_device_info)
        
        # IP info available (0 or 1)
        has_ip_info = 1 if transaction_data.get('ip_address') else 0
        features.append(has_ip_info)
        
        # Amount velocity features (would need historical data)
        # For now, we'll use amount brackets
        amount = transaction_data.get('amount', 0)
        amount_bracket = 0
        if amount > 10000:
            amount_bracket = 4
        elif amount > 5000:
            amount_bracket = 3
        elif amount > 1000:
            amount_bracket = 2
        elif amount > 100:
            amount_bracket = 1
        features.append(amount_bracket)
        
        return np.array(features).reshape(1, -1)
    
    def train_model(self, training_data: pd.DataFrame):
        """
        Train the ML model with historical transaction data
        """
        print("Training fraud detection model...")
        
        # Prepare features
        feature_data = []
        labels = []
        
        for _, row in training_data.iterrows():
            transaction_dict = row.to_dict()
            features = self.extract_features(transaction_dict)
            feature_data.append(features[0])
            labels.append(1 if row['fraud_prediction'] else 0)
        
        X = np.array(feature_data)
        y = np.array(labels)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Random Forest model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced'  # Handle imbalanced data
        )
        
        self.model.fit(X_scaled, y)
        
        # Feature importance
        feature_names = [
            'amount', 'hour_of_day', 'is_weekend', 'payment_risk',
            'transaction_type_risk', 'category_risk', 'is_cross_border',
            'merchant_high_risk', 'transaction_high_risk', 'has_device_info',
            'has_ip_info', 'amount_bracket'
        ]
        
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nFeature Importance:")
        print(feature_importance)
        
        # Save model
        self.save_model()
        
        return self.model
    
    def predict_fraud_probability(self, transaction_data: Dict) -> Tuple[float, Dict]:
        """
        Predict fraud probability for a transaction
        Returns: (probability, explanation_dict)
        """
        if self.model is None:
            # No trained model, return neutral prediction
            return 0.5, {"status": "No ML model available, using rules only"}
        
        try:
            # Extract features
            features = self.extract_features(transaction_data)
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Get prediction probability
            fraud_probability = self.model.predict_proba(features_scaled)[0][1]
            
            # Get feature contributions (simplified explanation)
            feature_values = features[0]
            feature_names = [
                'amount', 'hour_of_day', 'is_weekend', 'payment_risk',
                'transaction_type_risk', 'category_risk', 'is_cross_border',
                'merchant_high_risk', 'transaction_high_risk', 'has_device_info',
                'has_ip_info', 'amount_bracket'
            ]
            
            # Identify high-risk features
            explanations = {}
            if feature_values[0] > 5000:  # amount
                explanations['high_amount'] = f"Transaction amount ${feature_values[0]} is high"
            if feature_values[6] == 1:  # cross-border
                explanations['cross_border'] = "Cross-border transaction detected"
            if feature_values[7] == 1 or feature_values[8] == 1:  # high-risk country
                explanations['high_risk_location'] = "High-risk country involved"
            if feature_values[3] > 0.5:  # payment method risk
                explanations['risky_payment'] = "Higher risk payment method"
            
            return fraud_probability, {
                "ml_score": float(fraud_probability),
                "risk_factors": explanations,
                "model_confidence": "high" if abs(fraud_probability - 0.5) > 0.3 else "medium"
            }
            
        except Exception as e:
            print(f"ML prediction error: {e}")
            return 0.5, {"status": "ML prediction failed", "error": str(e)}
    
    def save_model(self):
        """Save trained model and preprocessors"""
        # Create models directory if it doesn't exist
        self.models_dir.mkdir(exist_ok=True)
        
        if self.model:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            print(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load existing model if available"""
        try:
            if self.model_path.exists() and self.scaler_path.exists():
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                print(f"ML model loaded successfully from {self.model_path}")
                return True
            else:
                print(f"Model files not found at {self.model_path}")
        except Exception as e:
            print(f"Could not load model: {e}")
        return False


# Create singleton instance
ml_model = FraudMLModel()