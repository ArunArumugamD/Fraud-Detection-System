import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",  # Import string instead of app object
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )