from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Literal
from enum import Enum


class TransactionType(str, Enum):
    PURCHASE = "purchase"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    PAYMENT = "payment"
    REFUND = "refund"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    FLAGGED = "flagged"
    UNDER_REVIEW = "under_review"


class TransactionBase(BaseModel):
    # Transaction details
    amount: float = Field(..., gt=0, description="Transaction amount in USD")
    currency: str = Field(default="USD", max_length=3)
    transaction_type: TransactionType
    
    # Merchant/Recipient info
    merchant_name: str = Field(..., max_length=255)
    merchant_category: str = Field(..., max_length=100)
    merchant_country: str = Field(..., max_length=2, description="ISO country code")
    
    # Customer info
    customer_id: str = Field(..., max_length=50)
    customer_email: Optional[str] = Field(None, max_length=255)
    
    # Card/Payment details
    card_last_four: Optional[str] = Field(None, pattern="^[0-9]{4}$")
    payment_method: str = Field(..., description="credit_card, debit_card, bank_transfer, etc.")
    
    # Location info
    transaction_country: str = Field(..., max_length=2, description="ISO country code")
    transaction_city: Optional[str] = Field(None, max_length=100)
    ip_address: Optional[str] = Field(None, max_length=45)
    
    # Device info
    device_id: Optional[str] = Field(None, max_length=100)
    device_type: Optional[str] = Field(None, max_length=50)
    
    # Additional metadata
    description: Optional[str] = Field(None, max_length=500)
    
    @validator('card_last_four')
    def validate_card_last_four(cls, v):
        if v and not v.isdigit():
            raise ValueError('Card last four must contain only digits')
        return v


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction"""
    pass


class TransactionResponse(TransactionBase):
    """Schema for transaction response"""
    id: int
    status: TransactionStatus
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: Literal["low", "medium", "high"]
    fraud_prediction: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Fraud detection results
    fraud_reasons: Optional[list[str]] = []
    verification_required: bool = False
    
    # ML model information
    ml_score: Optional[float] = Field(None, ge=0, le=1)
    rule_score: Optional[float] = Field(None, ge=0, le=1)
    ml_confidence: Optional[str] = None
    
    class Config:
        from_attributes = True


class TransactionAnalysis(BaseModel):
    """Response for transaction analysis"""
    transaction_id: int
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: Literal["low", "medium", "high"]
    fraud_prediction: bool
    fraud_reasons: list[str]
    recommendations: list[str]
    requires_manual_review: bool
    
    # ML model information
    ml_info: Optional[dict] = None
    
    
class TransactionListResponse(BaseModel):
    """Response for listing transactions"""
    total_count: int
    transactions: list[TransactionResponse]
    
    
class TransactionFilter(BaseModel):
    """Filters for querying transactions"""
    customer_id: Optional[str] = None
    status: Optional[TransactionStatus] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    fraud_only: Optional[bool] = False
    risk_level: Optional[Literal["low", "medium", "high"]] = None