from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.sql import func
from app.db.database import Base


class Transaction(Base):
    """
    Transaction model for fraud detection system
    """
    __tablename__ = "transactions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    transaction_type = Column(String(50), nullable=False)
    
    # Merchant/Recipient info
    merchant_name = Column(String(255), nullable=False)
    merchant_category = Column(String(100), nullable=False)
    merchant_country = Column(String(2), nullable=False)
    
    # Customer info
    customer_id = Column(String(50), nullable=False, index=True)
    customer_email = Column(String(255))
    
    # Card/Payment details
    card_last_four = Column(String(4))
    payment_method = Column(String(50), nullable=False)
    
    # Location info
    transaction_country = Column(String(2), nullable=False)
    transaction_city = Column(String(100))
    ip_address = Column(String(45))
    
    # Device info
    device_id = Column(String(100))
    device_type = Column(String(50))
    
    # Transaction metadata
    description = Column(Text)
    
    # Fraud detection results
    status = Column(String(50), default="pending", nullable=False, index=True)
    risk_score = Column(Float, default=0.0, nullable=False)
    risk_level = Column(String(20), default="low", nullable=False)
    fraud_prediction = Column(Boolean, default=False, nullable=False, index=True)
    fraud_reasons = Column(Text)  # Store as JSON string
    verification_required = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Create composite indexes for better query performance
    __table_args__ = (
        Index('idx_customer_created', 'customer_id', 'created_at'),
        Index('idx_status_risk', 'status', 'risk_score'),
        Index('idx_fraud_created', 'fraud_prediction', 'created_at'),
    )