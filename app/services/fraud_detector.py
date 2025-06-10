from typing import List, Tuple, Dict
from app.models.schemas import TransactionCreate
from app.services.ml_model import ml_model
import json


class FraudDetector:
    """
    Combined rule-based and ML fraud detection service
    """
    
    # Risk thresholds
    HIGH_RISK_AMOUNT = 10000
    MEDIUM_RISK_AMOUNT = 5000
    
    # High-risk countries (example list)
    HIGH_RISK_COUNTRIES = ["XX", "YY"]  # Use actual country codes
    
    # Suspicious patterns
    SUSPICIOUS_MERCHANTS = ["test", "suspicious", "fraud"]
    
    def analyze_transaction(self, transaction: TransactionCreate) -> Tuple[float, List[str], Dict]:
        """
        Analyze transaction using both rules and ML
        Returns: (combined_risk_score, reasons, ml_info)
        """
        # Get rule-based score
        rule_score, rule_reasons = self._apply_rules(transaction)
        
        # Get ML prediction
        ml_probability, ml_explanation = ml_model.predict_fraud_probability(transaction.dict())
        
        # Combine scores (weighted average)
        # You can adjust these weights based on model performance
        rule_weight = 0.4
        ml_weight = 0.6
        
        combined_score = (rule_score * rule_weight) + (ml_probability * ml_weight)
        
        # Combine reasons
        all_reasons = rule_reasons.copy()
        
        # Add ML insights if significant
        if ml_probability > 0.7:
            all_reasons.append(f"ML model detected high fraud probability ({ml_probability:.2f})")
        elif ml_probability > 0.5:
            all_reasons.append(f"ML model detected medium fraud probability ({ml_probability:.2f})")
        
        # Add specific ML risk factors
        if 'risk_factors' in ml_explanation:
            for factor, description in ml_explanation['risk_factors'].items():
                all_reasons.append(f"ML: {description}")
        
        # Ensure score is between 0 and 1
        combined_score = min(max(combined_score, 0.0), 1.0)
        
        # ML info for response
        ml_info = {
            "ml_score": ml_probability,
            "rule_score": rule_score,
            "combined_score": combined_score,
            "ml_confidence": ml_explanation.get('model_confidence', 'unknown'),
            "weights": {"rules": rule_weight, "ml": ml_weight}
        }
        
        return combined_score, all_reasons, ml_info
    
    def _apply_rules(self, transaction: TransactionCreate) -> Tuple[float, List[str]]:
        """
        Apply rule-based fraud detection (original logic)
        Returns: (risk_score, list_of_reasons)
        """
        risk_score = 0.0
        reasons = []
        
        # Rule 1: High transaction amount
        if transaction.amount > self.HIGH_RISK_AMOUNT:
            risk_score += 0.4
            reasons.append(f"High transaction amount: ${transaction.amount}")
        elif transaction.amount > self.MEDIUM_RISK_AMOUNT:
            risk_score += 0.2
            reasons.append(f"Medium-high transaction amount: ${transaction.amount}")
        
        # Rule 2: High-risk country
        if transaction.merchant_country in self.HIGH_RISK_COUNTRIES:
            risk_score += 0.3
            reasons.append(f"High-risk merchant country: {transaction.merchant_country}")
        
        if transaction.transaction_country in self.HIGH_RISK_COUNTRIES:
            risk_score += 0.2
            reasons.append(f"High-risk transaction country: {transaction.transaction_country}")
        
        # Rule 3: Cross-border transaction
        if transaction.merchant_country != transaction.transaction_country:
            risk_score += 0.1
            reasons.append("Cross-border transaction")
        
        # Rule 4: Suspicious merchant name
        merchant_lower = transaction.merchant_name.lower()
        for suspicious in self.SUSPICIOUS_MERCHANTS:
            if suspicious in merchant_lower:
                risk_score += 0.3
                reasons.append(f"Suspicious merchant name: {transaction.merchant_name}")
                break
        
        # Rule 5: Unusual payment method for amount
        if transaction.amount > 5000 and transaction.payment_method == "prepaid_card":
            risk_score += 0.2
            reasons.append("Large amount on prepaid card")
        
        # Rule 6: Missing information increases risk
        if not transaction.device_id:
            risk_score += 0.05
            reasons.append("Missing device information")
        
        if not transaction.ip_address:
            risk_score += 0.05
            reasons.append("Missing IP address")
        
        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)
        
        return risk_score, reasons
    
    def get_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score"""
        if risk_score >= 0.7:
            return "high"
        elif risk_score >= 0.3:
            return "medium"
        else:
            return "low"
    
    def is_fraud(self, risk_score: float) -> bool:
        """Determine if transaction should be flagged as fraud"""
        return risk_score >= 0.7
    
    def get_recommendations(self, risk_score: float, risk_level: str, ml_info: Dict) -> List[str]:
        """Get recommendations based on risk analysis"""
        recommendations = []
        
        # Check if ML and rules disagree significantly
        if ml_info and abs(ml_info.get('ml_score', 0) - ml_info.get('rule_score', 0)) > 0.4:
            recommendations.append("ML and rule scores differ significantly - manual review recommended")
        
        if risk_level == "high":
            recommendations.extend([
                "Block transaction immediately",
                "Contact customer for verification",
                "Flag for manual review"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Request additional verification",
                "Monitor customer activity",
                "Consider transaction limits"
            ])
        else:
            recommendations.append("Approve transaction")
            if risk_score > 0.1:
                recommendations.append("Continue monitoring for patterns")
        
        return recommendations


# Create singleton instance
fraud_detector = FraudDetector()