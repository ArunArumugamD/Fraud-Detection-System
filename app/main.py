from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
import uvicorn
import json
from typing import Optional, List, Dict
from datetime import datetime
import asyncio
import logging

# Import database components
from app.db.database import engine, get_db, Base
from app.models.transaction_model import Transaction
from app.core.config import settings

# Import schemas and services
from app.models.schemas import (
    TransactionCreate, 
    TransactionResponse, 
    TransactionAnalysis,
    TransactionListResponse,
    TransactionStatus
)
from app.services.fraud_detector import fraud_detector
from app.services.kafka_producer import kafka_producer
from app.services.kafka_consumer import kafka_consumer
from app.services.websocket_manager import websocket_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI instance
app = FastAPI(
    title="Fraud Detection System",
    description="Enterprise fraud detection API with ML and real-time streaming",
    version="2.0.0"
)

# Configure CORS (for frontend connections later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Fraud Detection System...")
    
    # Start Kafka producer
    try:
        await kafka_producer.start()
        logger.info("Kafka producer started")
    except Exception as e:
        logger.warning(f"Kafka producer failed to start: {e}. Continuing without streaming.")
    
    # Start Kafka consumer in background
    try:
        await kafka_consumer.start()
        # Run consumer in background
        asyncio.create_task(kafka_consumer.process_messages())
        logger.info("Kafka consumer started")
    except Exception as e:
        logger.warning(f"Kafka consumer failed to start: {e}. Continuing without consumer.")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Fraud Detection System...")
    
    # Stop Kafka services
    await kafka_producer.stop()
    await kafka_consumer.stop()


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Fraud Detection System API",
        "version": "0.1.0",
        "status": "online"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "fraud-detection-api"
    }


# Example fraud check endpoint (placeholder)
@app.post("/api/v1/check-transaction")
async def check_transaction(amount: float, merchant: str):
    """
    Placeholder endpoint for transaction fraud checking
    """
    # Simple mock logic for now
    risk_score = 0.1  # Low risk by default
    
    if amount > 10000:
        risk_score = 0.8  # High risk for large amounts
    elif amount > 5000:
        risk_score = 0.5  # Medium risk
    
    return {
        "transaction": {
            "amount": amount,
            "merchant": merchant
        },
        "risk_score": risk_score,
        "risk_level": "high" if risk_score > 0.7 else "medium" if risk_score > 0.3 else "low",
        "recommendation": "block" if risk_score > 0.7 else "review" if risk_score > 0.3 else "approve"
    }


# Database test endpoint - Check connection
@app.get("/api/v1/db-test")
async def test_database_connection(db: Session = Depends(get_db)):
    """
    Test database connection
    """
    try:
        # Try to execute a simple query - SQLAlchemy 2.0 requires text()
        result = db.execute(text("SELECT 1"))
        return {
            "status": "success",
            "message": "Database connection successful",
            "database": settings.DB_NAME
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


# Create a test transaction
@app.post("/api/v1/test-transaction")
async def create_test_transaction(
    amount: float,
    merchant: str,
    db: Session = Depends(get_db)
):
    """
    Create a test transaction in the database
    """
    try:
        # Create new transaction
        transaction = Transaction(
            amount=amount,
            merchant_name=merchant,
            merchant_category="test",
            merchant_country="US",
            customer_id="test-customer",
            payment_method="credit_card",
            transaction_country="US",
            transaction_type="purchase",
            risk_score=0.1 if amount < 1000 else 0.5 if amount < 5000 else 0.8,
            fraud_prediction=amount > 10000  # Simple rule for testing
        )
        
        # Add to database
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return {
            "status": "success",
            "transaction_id": transaction.id,
            "amount": transaction.amount,
            "merchant": transaction.merchant_name,
            "risk_score": transaction.risk_score,
            "is_fraud": transaction.fraud_prediction,
            "created_at": transaction.created_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {str(e)}")


# Helper function to convert DB model to response
def transaction_to_response(db_transaction: Transaction, ml_info: Optional[Dict] = None) -> TransactionResponse:
    """Convert database transaction to response model"""
    # Parse fraud reasons from JSON string
    fraud_reasons = []
    if db_transaction.fraud_reasons:
        try:
            fraud_reasons = json.loads(db_transaction.fraud_reasons)
        except:
            fraud_reasons = []
    
    response_dict = {
        "id": db_transaction.id,
        "amount": db_transaction.amount,
        "currency": db_transaction.currency,
        "transaction_type": db_transaction.transaction_type,
        "merchant_name": db_transaction.merchant_name,
        "merchant_category": db_transaction.merchant_category,
        "merchant_country": db_transaction.merchant_country,
        "customer_id": db_transaction.customer_id,
        "customer_email": db_transaction.customer_email,
        "card_last_four": db_transaction.card_last_four,
        "payment_method": db_transaction.payment_method,
        "transaction_country": db_transaction.transaction_country,
        "transaction_city": db_transaction.transaction_city,
        "ip_address": db_transaction.ip_address,
        "device_id": db_transaction.device_id,
        "device_type": db_transaction.device_type,
        "description": db_transaction.description,
        "status": db_transaction.status,
        "risk_score": db_transaction.risk_score,
        "risk_level": db_transaction.risk_level,
        "fraud_prediction": db_transaction.fraud_prediction,
        "fraud_reasons": fraud_reasons,
        "verification_required": db_transaction.verification_required,
        "created_at": db_transaction.created_at,
        "updated_at": db_transaction.updated_at
    }
    
    # Add ML info if provided
    if ml_info:
        response_dict["ml_score"] = ml_info.get("ml_score")
        response_dict["rule_score"] = ml_info.get("rule_score")
        response_dict["ml_confidence"] = ml_info.get("ml_confidence")
    
    return TransactionResponse(**response_dict)


# Create a new transaction with fraud detection
@app.post("/api/v1/transactions", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    stream_mode: bool = Query(False, description="Process via Kafka streaming")
):
    """
    Create a new transaction and run fraud detection (ML + Rules)
    
    - **stream_mode=False**: Direct processing (synchronous)
    - **stream_mode=True**: Kafka streaming (asynchronous)
    """
    try:
        if stream_mode:
            # Streaming mode: publish to Kafka
            import uuid
            temp_id = str(uuid.uuid4())
            
            # Publish to Kafka for async processing
            success = await kafka_producer.publish_transaction(
                transaction_data=transaction.dict(),
                transaction_id=temp_id
            )
            
            if not success:
                raise HTTPException(status_code=503, detail="Failed to publish to Kafka stream")
            
            # Return immediate response
            return TransactionResponse(
                id=0,  # Will be assigned by consumer
                **transaction.dict(),
                status=TransactionStatus.PENDING,
                risk_score=0.0,
                risk_level="low",  # Default to low for pending
                fraud_prediction=False,
                fraud_reasons=[],
                verification_required=False,
                created_at=datetime.utcnow(),
                updated_at=None,
                ml_score=None,
                rule_score=None,
                ml_confidence=None
            )
        
        else:
            # Direct mode: process immediately
            # Run fraud detection with ML
            risk_score, fraud_reasons, ml_info = fraud_detector.analyze_transaction(transaction)
            risk_level = fraud_detector.get_risk_level(risk_score)
            is_fraud = fraud_detector.is_fraud(risk_score)
            
            # Determine status based on risk
            if is_fraud:
                status = TransactionStatus.DECLINED
            elif risk_level == "medium":
                status = TransactionStatus.FLAGGED
            else:
                status = TransactionStatus.APPROVED
            
            # Create database transaction
            db_transaction = Transaction(
                **transaction.dict(),
                status=status,
                risk_score=risk_score,
                risk_level=risk_level,
                fraud_prediction=is_fraud,
                fraud_reasons=json.dumps(fraud_reasons) if fraud_reasons else None,
                verification_required=risk_level in ["medium", "high"]
            )
            
            db.add(db_transaction)
            db.commit()
            db.refresh(db_transaction)
            
            # Send alert if high risk
            if is_fraud or risk_level == "high":
                alert_data = {
                    "transaction_id": str(db_transaction.id),
                    "alert_type": "FRAUD_DETECTED" if is_fraud else "HIGH_RISK",
                    "risk_score": risk_score,
                    "amount": transaction.amount,
                    "merchant": transaction.merchant_name,
                    "customer_id": transaction.customer_id,
                    "reasons": fraud_reasons,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Send WebSocket alert in background
                background_tasks.add_task(websocket_manager.send_alert, alert_data)
            
            # Convert to response with ML info
            return transaction_to_response(db_transaction, ml_info)
        
    except Exception as e:
        if not stream_mode:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {str(e)}")


# Get transaction by ID
@app.get("/api/v1/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific transaction by ID
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transaction_to_response(transaction)


# Analyze a transaction without saving
@app.post("/api/v1/transactions/analyze", response_model=TransactionAnalysis)
async def analyze_transaction(transaction: TransactionCreate):
    """
    Analyze a transaction for fraud without saving it (ML + Rules)
    """
    # Run fraud detection with ML
    risk_score, fraud_reasons, ml_info = fraud_detector.analyze_transaction(transaction)
    risk_level = fraud_detector.get_risk_level(risk_score)
    is_fraud = fraud_detector.is_fraud(risk_score)
    recommendations = fraud_detector.get_recommendations(risk_score, risk_level, ml_info)
    
    return TransactionAnalysis(
        transaction_id=0,  # No ID since not saved
        risk_score=risk_score,
        risk_level=risk_level,
        fraud_prediction=is_fraud,
        fraud_reasons=fraud_reasons,
        recommendations=recommendations,
        requires_manual_review=risk_level == "medium" or abs(ml_info.get('ml_score', 0) - ml_info.get('rule_score', 0)) > 0.4,
        ml_info=ml_info
    )


# Get all transactions
@app.get("/api/v1/transactions", response_model=TransactionListResponse)
async def get_transactions(
    db: Session = Depends(get_db),
    customer_id: Optional[str] = Query(None),
    status: Optional[TransactionStatus] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    fraud_only: bool = Query(False),
    limit: int = Query(100, le=1000),
    offset: int = Query(0)
):
    """
    Get transactions with optional filters
    """
    query = db.query(Transaction)
    
    # Apply filters
    if customer_id:
        query = query.filter(Transaction.customer_id == customer_id)
    if status:
        query = query.filter(Transaction.status == status)
    if min_amount:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount:
        query = query.filter(Transaction.amount <= max_amount)
    if fraud_only:
        query = query.filter(Transaction.fraud_prediction == True)
    
    # Get total count
    total_count = query.count()
    
    # Get paginated results
    transactions = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    transaction_responses = [transaction_to_response(t) for t in transactions]
    
    return TransactionListResponse(
        total_count=total_count,
        transactions=transaction_responses
    )


# ML Model status endpoint
@app.get("/api/v1/ml-model/status")
async def get_ml_model_status():
    """
    Get ML model status and information
    """
    from app.services.ml_model import ml_model
    
    return {
        "model_loaded": ml_model.model is not None,
        "model_type": "RandomForestClassifier" if ml_model.model else None,
        "features_used": [
            'amount', 'hour_of_day', 'is_weekend', 'payment_risk',
            'transaction_type_risk', 'category_risk', 'is_cross_border',
            'merchant_high_risk', 'transaction_high_risk', 'has_device_info',
            'has_ip_info', 'amount_bracket'
        ] if ml_model.model else [],
        "status": "ready" if ml_model.model else "not_trained",
        "message": "ML model is ready for predictions" if ml_model.model else "No ML model found. Run training script first."
    }


# WebSocket endpoint for real-time alerts
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time fraud alerts
    """
    await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
            
            # Could handle other client commands here
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# Streaming system status
@app.get("/api/v1/streaming/status")
async def get_streaming_status():
    """
    Get Kafka streaming system status
    """
    consumer_stats = await kafka_consumer.get_stats()
    websocket_stats = websocket_manager.get_connection_stats()
    
    return {
        "kafka_producer": {
            "status": "connected" if kafka_producer.producer else "disconnected"
        },
        "kafka_consumer": consumer_stats,
        "websocket_connections": websocket_stats,
        "system_status": "operational" if consumer_stats.get("running", False) else "degraded"
    }


# Batch transaction processing endpoint
@app.post("/api/v1/transactions/batch")
async def create_batch_transactions(
    transactions: List[TransactionCreate],
    background_tasks: BackgroundTasks
):
    """
    Submit multiple transactions for processing via Kafka
    """
    import uuid
    
    submitted = []
    failed = []
    
    for transaction in transactions:
        try:
            temp_id = str(uuid.uuid4())
            success = await kafka_producer.publish_transaction(
                transaction_data=transaction.dict(),
                transaction_id=temp_id
            )
            
            if success:
                submitted.append(temp_id)
            else:
                failed.append(transaction.dict())
                
        except Exception as e:
            logger.error(f"Failed to submit transaction: {e}")
            failed.append(transaction.dict())
    
    return {
        "submitted_count": len(submitted),
        "failed_count": len(failed),
        "submitted_ids": submitted,
        "failed_transactions": failed,
        "message": f"Submitted {len(submitted)} transactions to processing queue"
    }


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )