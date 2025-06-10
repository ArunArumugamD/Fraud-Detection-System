import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from app.services.ml_model import ml_model
from app.db.database import SessionLocal
from app.models.transaction_model import Transaction

def generate_synthetic_training_data(n_samples=1000):
    """
    Generate synthetic training data for ML model
    In production, you'd use real historical data
    """
    print(f"Generating {n_samples} synthetic transactions...")
    
    data = []
    
    # Normal transactions (70%)
    for _ in range(int(n_samples * 0.7)):
        transaction = {
            'amount': random.uniform(10, 1000),
            'transaction_type': random.choice(['purchase', 'payment', 'deposit']),
            'merchant_name': random.choice(['Amazon', 'Starbucks', 'Target', 'Walmart', 'Apple Store']),
            'merchant_category': random.choice(['E-commerce', 'Food & Beverage', 'Retail', 'Electronics']),
            'merchant_country': 'US',
            'customer_id': f'CUST{random.randint(1000, 9999)}',
            'payment_method': random.choice(['credit_card', 'debit_card', 'bank_transfer']),
            'transaction_country': 'US',
            'device_id': f'device-{random.randint(100, 999)}',
            'ip_address': f'192.168.1.{random.randint(1, 255)}',
            'fraud_prediction': False,
            'risk_score': random.uniform(0, 0.3)
        }
        data.append(transaction)
    
    # Suspicious transactions (20%)
    for _ in range(int(n_samples * 0.2)):
        transaction = {
            'amount': random.uniform(1000, 8000),
            'transaction_type': random.choice(['purchase', 'withdrawal', 'transfer']),
            'merchant_name': random.choice(['Electronics Shop', 'Jewelry Store', 'Online Store XYZ']),
            'merchant_category': random.choice(['Electronics', 'Jewelry', 'E-commerce']),
            'merchant_country': random.choice(['US', 'MX', 'CA']),
            'customer_id': f'CUST{random.randint(1000, 9999)}',
            'payment_method': random.choice(['credit_card', 'prepaid_card']),
            'transaction_country': random.choice(['US', 'MX', 'CA']),
            'device_id': random.choice([f'device-{random.randint(100, 999)}', None]),
            'ip_address': random.choice([f'192.168.1.{random.randint(1, 255)}', None]),
            'fraud_prediction': False,
            'risk_score': random.uniform(0.3, 0.6)
        }
        data.append(transaction)
    
    # Fraudulent transactions (10%)
    for _ in range(int(n_samples * 0.1)):
        transaction = {
            'amount': random.uniform(5000, 20000),
            'transaction_type': random.choice(['withdrawal', 'transfer', 'purchase']),
            'merchant_name': random.choice(['Suspicious Store', 'Unknown Merchant', 'Test Shop 123']),
            'merchant_category': random.choice(['Money Transfer', 'Electronics', 'ATM']),
            'merchant_country': random.choice(['XX', 'YY', 'ZZ']),
            'customer_id': f'CUST{random.randint(1000, 9999)}',
            'payment_method': random.choice(['prepaid_card', 'credit_card']),
            'transaction_country': random.choice(['US', 'XX', 'YY']),
            'device_id': None,
            'ip_address': None,
            'fraud_prediction': True,
            'risk_score': random.uniform(0.7, 1.0)
        }
        data.append(transaction)
    
    return pd.DataFrame(data)

def load_existing_transactions():
    """
    Load existing transactions from database
    """
    print("Loading existing transactions from database...")
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).all()
        if transactions:
            data = []
            for t in transactions:
                data.append({
                    'amount': t.amount,
                    'transaction_type': t.transaction_type,
                    'merchant_name': t.merchant_name,
                    'merchant_category': t.merchant_category,
                    'merchant_country': t.merchant_country,
                    'customer_id': t.customer_id,
                    'payment_method': t.payment_method,
                    'transaction_country': t.transaction_country,
                    'device_id': t.device_id,
                    'ip_address': t.ip_address,
                    'fraud_prediction': t.fraud_prediction,
                    'risk_score': t.risk_score
                })
            return pd.DataFrame(data)
        else:
            print("No existing transactions found.")
            return None
    finally:
        db.close()

def main():
    """
    Train the ML model
    """
    # Try to load existing data first
    existing_data = load_existing_transactions()
    
    # Generate synthetic data
    synthetic_data = generate_synthetic_training_data(1000)
    
    # Combine data if we have existing transactions
    if existing_data is not None and len(existing_data) > 0:
        print(f"Found {len(existing_data)} existing transactions")
        training_data = pd.concat([existing_data, synthetic_data], ignore_index=True)
    else:
        training_data = synthetic_data
    
    print(f"\nTotal training samples: {len(training_data)}")
    print(f"Fraud cases: {training_data['fraud_prediction'].sum()} ({training_data['fraud_prediction'].mean()*100:.1f}%)")
    
    # Train the model
    ml_model.train_model(training_data)
    
    print("\nModel training completed!")
    
    # Test the model with a sample transaction
    test_transaction = {
        'amount': 5500,
        'transaction_type': 'purchase',
        'merchant_name': 'Electronics Store',
        'merchant_category': 'Electronics',
        'merchant_country': 'XX',
        'customer_id': 'TEST123',
        'payment_method': 'prepaid_card',
        'transaction_country': 'US',
        'device_id': None,
        'ip_address': None
    }
    
    probability, explanation = ml_model.predict_fraud_probability(test_transaction)
    print(f"\nTest prediction for high-risk transaction:")
    print(f"Fraud probability: {probability:.3f}")
    print(f"Explanation: {explanation}")

if __name__ == "__main__":
    main()