from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create FastAPI instance
app = FastAPI(
    title="Fraud Detection System",
    description="Enterprise fraud detection API",
    version="0.1.0"
)

# Configure CORS (for frontend connections later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )